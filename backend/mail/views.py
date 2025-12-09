from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.http import HttpResponse
from email_accounts.models import EmailAccount
from .models import EmailMetadata, Attachment
from .serializers import EmailSerializer, SendEmailSerializer
from .imap_client import IMAPClient
from .smtp_client import SMTPClient
from .cache_service import EmailCacheService


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sync_emails(request, account_id):
    """
    Smart email sync with intelligent caching
    GET /api/mail/sync/{account_id}
    
    Logic:
    - If last_synced > 1 hour ago → Fetch last 20 emails
    - If last_synced < 1 hour → Fetch last 5 emails  
    - If never synced → Fetch last 20 emails
    - Emails cached in Redis (2hr TTL), only metadata in DB
    """
    try:
        account = EmailAccount.objects.get(id=account_id, user=request.user)
    except EmailAccount.DoesNotExist:
        return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        # Use smart cache service
        print(f"[SYNC] Smart sync for account: {account.email} (ID: {account.id})")
        sync_result = EmailCacheService.sync_emails_smart(request.user, account)
        
        return Response({
            'message': f'Synced successfully. Fetched {sync_result["fetched"]} emails, cached {sync_result["cached"]}.',
            'fetched': sync_result['fetched'],
            'cached': sync_result['cached'],
            'new_metadata': sync_result.get('new_metadata', 0),
            'fetch_limit': sync_result['limit'],
            'last_synced': sync_result['last_synced'],
            'strategy': f'Fetched last {sync_result["limit"]} emails (smart caching)'
        })
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Sync error for account {account_id}: {str(e)}")
        print(error_trace)
        return Response(
            {'error': f'Sync failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_emails(request):
    """
    List emails metadata (fast, DB-only query)
    GET /api/mail/
    Query params:
        - account_id (optional): Filter by account
        - limit (optional): Number of emails (default 50)
    
    Returns only metadata - full content fetched on-demand when opening email
    """
    account_id = request.query_params.get('account_id')
    limit = int(request.query_params.get('limit', 50))
    
    # Query only metadata (fast!)
    emails = EmailMetadata.objects.filter(user=request.user)
    
    if account_id:
        emails = emails.filter(account_id=account_id)
    
    emails = emails[:limit]
    
    # Return lightweight metadata with envelope info from cache
    email_list = []
    for email in emails:
        email_data = {
            'id': email.id,
            'message_id': email.message_id,
            'subject': email.subject,
            'from_email': email.from_email,
            'from_name': email.from_name,
            'is_read': email.is_read,
            'is_starred': email.is_starred,
            'is_encrypted': email.is_encrypted,
            'has_attachments': email.has_attachments,
            'sent_at': email.sent_at,
            'cached_at': email.cached_at,
        }
        
        # Try to get envelope data from cache (lightweight)
        email_content = EmailCacheService.get_email_content(email.message_id)
        if email_content:
            email_data['envelope'] = email_content.get('envelope', {})
            email_data['headers'] = email_content.get('headers', {})
        
        email_list.append(email_data)
    
    return Response(email_list)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_email(request, email_id):
    """
    Get full email content (on-demand fetch from cache/IMAP)
    GET /api/mail/{email_id}
    
    Logic:
    1. Get metadata from DB
    2. Check Redis cache for full content
    3. If not cached, fetch from IMAP directly
    4. Cache result and return
    """
    try:
        # Get metadata first (fast DB query)
        metadata = EmailMetadata.objects.get(id=email_id, user=request.user)
        
        # Try to get full content from cache
        email_content = EmailCacheService.get_email_content(metadata.message_id)
        
        if not email_content:
            # Not in cache - fetch on-demand from IMAP
            print(f"[GET_EMAIL] Cache miss for {metadata.message_id}, fetching from IMAP...")
            email_content = EmailCacheService.get_email_on_demand(
                request.user,
                metadata.account,
                metadata.message_id
            )
            
            if not email_content:
                print(f"[GET_EMAIL] ❌ Failed to fetch email content for {metadata.message_id}")
                return Response(
                    {'error': 'Failed to fetch email content'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            print(f"[GET_EMAIL] ✅ Cache hit for {metadata.message_id}")
        
        # Debug: Print what we got
        print(f"[GET_EMAIL] Email content keys: {list(email_content.keys())}")
        print(f"[GET_EMAIL] body_text length: {len(email_content.get('body_text', ''))}")
        print(f"[GET_EMAIL] to_emails: {email_content.get('to_emails')}")
        print(f"[GET_EMAIL] attachments count: {len(email_content.get('attachments', []))}")
        
        # Mark as read
        if not metadata.is_read:
            metadata.is_read = True
            metadata.save()
        
        # Email is already decrypted during sync - just get the content
        body_text = email_content.get('body_text', '')
        body_html = email_content.get('body_html', '')
        security_level = email_content.get('security_level', 'regular')
        
        # Process attachments for API response
        import base64
        attachments = email_content.get('attachments', [])
        processed_attachments = []
        
        for att in attachments:
            # Get attachment data - could be in 'data', 'file_data', or bytes
            att_data = att.get('data') or att.get('file_data')
            
            # Ensure data is base64 string
            if isinstance(att_data, bytes):
                att_data = base64.b64encode(att_data).decode('utf-8')
            elif not isinstance(att_data, str):
                att_data = ''
            
            processed_attachments.append({
                'filename': att.get('filename', 'unknown'),
                'content_type': att.get('content_type', 'application/octet-stream'),
                'size': att.get('size', 0),
                'data': att_data,
                'is_encrypted': att.get('is_encrypted', False),
                'security_level': att.get('security_level', 'regular')
            })
        
        # Parse to_emails and cc_emails (might be JSON strings from IMAP)
        import json
        to_emails = email_content.get('to_emails', [])
        cc_emails = email_content.get('cc_emails', [])
        
        # Convert JSON strings to arrays if needed
        if isinstance(to_emails, str):
            try:
                to_emails = json.loads(to_emails)
            except:
                to_emails = [to_emails] if to_emails else []
        
        if isinstance(cc_emails, str):
            try:
                cc_emails = json.loads(cc_emails)
            except:
                cc_emails = [cc_emails] if cc_emails else []
        
        # Combine metadata + content
        response_data = {
            'id': metadata.id,
            'message_id': metadata.message_id,
            'subject': email_content.get('subject', metadata.subject),
            'from_email': metadata.from_email,
            'from_name': metadata.from_name,
            'to_emails': to_emails,  # Parsed array
            'cc_emails': cc_emails,  # Parsed array
            'body_text': body_text,  # Already decrypted during sync
            'body_html': body_html,
            'attachments': processed_attachments,  # Already decrypted during sync
            'is_read': metadata.is_read,
            'is_starred': metadata.is_starred,
            'is_encrypted': metadata.is_encrypted,
            'sent_at': metadata.sent_at,
            'security_level': security_level,
            'encryption_metadata': email_content.get('encryption_metadata'),
            'headers': email_content.get('headers', {}),  # All email headers
            'envelope': email_content.get('envelope', {}),  # Envelope details
        }
        
        return Response(response_data)
        
    except EmailMetadata.DoesNotExist:
        return Response({'error': 'Email not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_email(request):
    """
    Send an email via SMTP with optional attachments
    POST /api/mail/send
    Body (multipart/form-data or JSON):
        account_id, to_emails[], subject, body_text, body_html (optional),
        security_level, attachments[] (files)
    """
    print(f"[SEND] ========== send_email called ==========")
    print(f"[SEND] Method: {request.method}")
    print(f"[SEND] User: {request.user}")
    
    # Handle multipart/form-data (for file uploads)
    import json
    from django.http import QueryDict
    
    # Convert QueryDict to regular dict to avoid list wrapping issues
    if isinstance(request.data, QueryDict):
        # QueryDict stores values as lists, so we need to unwrap them
        request_data = {}
        for key, value in request.data.items():
            # For to_emails, we'll handle it specially
            if key == 'to_emails':
                # Get the raw value (which is a JSON string in a list)
                if isinstance(value, list) and len(value) > 0:
                    request_data[key] = value[0]  # Get the JSON string
                else:
                    request_data[key] = value
            else:
                # For other fields, get first element if it's a list
                if isinstance(value, list) and len(value) > 0:
                    request_data[key] = value[0]
                else:
                    request_data[key] = value
    else:
        request_data = dict(request.data)
    
    # Debug logging
    print(f"[SEND] Content-Type: {request.content_type}")
    print(f"[SEND] Request data keys: {list(request_data.keys())}")
    
    if request.content_type and 'multipart/form-data' in request.content_type:
        # Convert account_id to int if it's a string
        if 'account_id' in request_data:
            if isinstance(request_data['account_id'], str):
                try:
                    request_data['account_id'] = int(request_data['account_id'])
                except (ValueError, TypeError):
                    pass
        
        # Parse to_emails JSON string
        if 'to_emails' in request_data:
            to_emails_value = request_data['to_emails']
            print(f"[SEND] to_emails type: {type(to_emails_value)}, value: {to_emails_value}")
            
            if isinstance(to_emails_value, str):
                try:
                    parsed = json.loads(to_emails_value)
                    # Ensure it's a flat list of strings
                    if isinstance(parsed, list):
                        request_data['to_emails'] = parsed
                    else:
                        request_data['to_emails'] = [parsed]
                    print(f"[SEND] Parsed to_emails: {request_data['to_emails']}")
                except (json.JSONDecodeError, ValueError) as e:
                    # If parsing fails, try to split by comma
                    print(f"[SEND] JSON parse failed: {e}, trying comma split")
                    request_data['to_emails'] = [email.strip() for email in to_emails_value.split(',') if email.strip()]
            elif isinstance(to_emails_value, list):
                # If it's already a list, use it directly
                request_data['to_emails'] = to_emails_value
            else:
                # Make it a list
                request_data['to_emails'] = [to_emails_value] if to_emails_value else []
    
    print(f"[SEND] Final request_data (to_emails): {request_data.get('to_emails')}")
    serializer = SendEmailSerializer(data=request_data)
    if not serializer.is_valid():
        print(f"[SEND] Serializer errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    try:
        account = EmailAccount.objects.get(id=data['account_id'], user=request.user)
    except EmailAccount.DoesNotExist:
        return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        security_level = data.get('security_level', 'regular')
        import base64
        from crypto import router as crypto_router
        
        # Prepare email content
        email_content = data['body_text']
        encrypted_metadata = None
        
        # Encrypt if security level is not 'regular'
        if security_level != 'regular':
            # Encrypt email body
            try:
                encryption_result = crypto_router.encrypt(
                    security_level=security_level,
                    plaintext=email_content.encode('utf-8'),  # Convert string to bytes
                    requester_sae=account.email,
                    recipient_sae=data['to_emails'][0] if data['to_emails'] else None
                )
                ciphertext = encryption_result['ciphertext']
                encrypted_metadata = encryption_result['metadata']
                
                # Serialize ciphertext based on type
                if isinstance(ciphertext, list):
                    # OTP returns list of bits - convert to string for transmission
                    email_content = ''.join(str(bit) for bit in ciphertext)
                elif isinstance(ciphertext, bytes):
                    # AES/QKD return bytes - base64 encode for transmission
                    email_content = base64.b64encode(ciphertext).decode('utf-8')
                else:
                    # Already a string (base64 encoded)
                    email_content = ciphertext
            except NotImplementedError:
                return Response(
                    {'error': f'Security level "{security_level}" is not yet implemented'},
                    status=status.HTTP_501_NOT_IMPLEMENTED
                )
            except Exception as e:
                return Response(
                    {'error': f'Encryption failed: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # Process attachments
        print(f"[SEND] Processing attachments...")
        print(f"[SEND] request.FILES keys: {list(request.FILES.keys())}")
        encrypted_attachments = []
        if 'attachments' in request.FILES:
            print(f"[SEND] Found attachments in request.FILES")
            for uploaded_file in request.FILES.getlist('attachments'):
                print(f"[SEND] Processing file: {uploaded_file.name}, size: {uploaded_file.size}, type: {uploaded_file.content_type}")
                # Read file as bytes
                file_bytes = uploaded_file.read()
                original_size = len(file_bytes)
                
                if security_level != 'regular':
                    # Encrypt attachment using same security level
                    try:
                        attachment_encryption = crypto_router.encrypt(
                            security_level=security_level,
                            plaintext=file_bytes,  # Direct bytes - no encoding needed!
                            requester_sae=account.email,
                            recipient_sae=data['to_emails'][0] if data['to_emails'] else None
                        )
                        
                        # Serialize attachment ciphertext based on type
                        att_ciphertext = attachment_encryption['ciphertext']
                        if isinstance(att_ciphertext, list):
                            # OTP returns list of bits - convert to string
                            serialized_ciphertext = ''.join(str(bit) for bit in att_ciphertext)
                            encrypted_size = len(serialized_ciphertext)
                        elif isinstance(att_ciphertext, bytes):
                            # AES/QKD return bytes - base64 encode
                            serialized_ciphertext = base64.b64encode(att_ciphertext).decode('utf-8')
                            encrypted_size = len(att_ciphertext)
                        else:
                            # Already a string (base64 encoded)
                            serialized_ciphertext = att_ciphertext
                            encrypted_size = len(base64.b64decode(att_ciphertext))
                        
                        encrypted_attachments.append({
                            'filename': uploaded_file.name,
                            'content_type': uploaded_file.content_type or 'application/octet-stream',
                            'size': original_size,  # Original size
                            'encrypted_data': serialized_ciphertext,
                            'encrypted_size': encrypted_size,
                            'metadata': attachment_encryption['metadata']
                        })
                        print(f"[SEND] Encrypted attachment: {uploaded_file.name} ({original_size} bytes)")
                    except Exception as e:
                        print(f"[SEND] Attachment encryption failed for {uploaded_file.name}: {str(e)}")
                        return Response(
                            {'error': f'Failed to encrypt attachment {uploaded_file.name}: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
                else:
                    # REGULAR: Store plain attachment (base64 encode for storage consistency only)
                    print(f"[SEND] Processing REGULAR attachment: {uploaded_file.name} ({original_size} bytes)")
                    encrypted_attachments.append({
                        'filename': uploaded_file.name,
                        'content_type': uploaded_file.content_type or 'application/octet-stream',
                        'size': original_size,
                        'encrypted_data': base64.b64encode(file_bytes).decode('utf-8'),  # Base64 for storage, will decode in SMTP
                        'encrypted_size': original_size,
                        'metadata': {}  # No encryption metadata for regular
                    })
                    print(f"[SEND] Added regular attachment to list: {uploaded_file.name}")
        
        print(f"[SEND] About to send email via SMTP")
        print(f"[SEND]   - To: {data['to_emails']}")
        print(f"[SEND]   - Subject: {data['subject']}")
        print(f"[SEND]   - Security Level: {security_level}")
        print(f"[SEND]   - Attachments count: {len(encrypted_attachments)}")
        
        smtp_client = SMTPClient(account)
        smtp_client.connect()
        print(f"[SEND] SMTP connected")
        
        smtp_client.send_email(
            to_emails=data['to_emails'],
            subject=data['subject'],
            body_text=email_content,
            body_html=data.get('body_html') or None,
            from_name=request.user.name or None,
            security_level=security_level,
            encryption_metadata=encrypted_metadata,
            attachments=encrypted_attachments if encrypted_attachments else None  # Pass encrypted attachments
        )
        print(f"[SEND] Email sent via SMTP")
        
        smtp_client.disconnect()
        print(f"[SEND] SMTP disconnected")
        
        print(f"[SEND] ========== send_email completed successfully ==========")
        return Response({
            'message': 'Email sent successfully',
            'security_level': security_level,
            'encrypted': security_level != 'regular',
            'metadata': encrypted_metadata,
            'attachments_count': len(encrypted_attachments)
        })
    
    except Exception as e:
        import traceback
        print(f"[SEND] ========== ERROR in send_email ==========")
        print(f"[SEND] Error: {str(e)}")
        print(f"[SEND] Traceback: {traceback.format_exc()}")
        return Response(
            {'error': f'Failed to send email: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_attachment(request, attachment_id):
    """
    Download attachment (automatically decrypted if encrypted)
    GET /api/mail/attachments/{attachment_id}
    """
    try:
        attachment = Attachment.objects.get(id=attachment_id, email__user=request.user)
        import base64
        from crypto import router as crypto_router
        
        # Get file data
        file_data = bytes(attachment.file_data)
        
        # DEBUG: Log attachment details
        print(f"[DOWNLOAD] Attachment details:")
        print(f"[DOWNLOAD]   - filename: {attachment.filename}")
        print(f"[DOWNLOAD]   - is_encrypted: {attachment.is_encrypted}")
        print(f"[DOWNLOAD]   - security_level: {attachment.security_level}")
        print(f"[DOWNLOAD]   - content_type: {attachment.content_type}")
        print(f"[DOWNLOAD]   - size: {attachment.size}")
        print(f"[DOWNLOAD]   - file_data length: {len(file_data)}")
        print(f"[DOWNLOAD]   - encryption_metadata: {attachment.encryption_metadata}")
        
        # Check if attachment is already decrypted (is_encrypted=False means it was decrypted during sync)
        # If is_encrypted=True, it means decryption failed during sync and we need to decrypt now
        if not attachment.is_encrypted:
            # Already decrypted during IMAP sync, return as-is
            print(f"[DOWNLOAD] Attachment {attachment.filename} was already decrypted during sync (regular or successfully decrypted)")
        elif attachment.is_encrypted and attachment.security_level != 'regular':
            try:
                # Use the email account's email address, not the user's QuteMail email
                # This is the email that received the message and should have access to decrypt
                account_email = attachment.email.account.email
                
                # file_data from DB could be:
                # 1. Base64 string stored as UTF-8 bytes (if decryption failed during sync)
                # 2. Raw encrypted bytes (if never attempted to decrypt)
                # Try to decode as UTF-8 first to get base64 string
                try:
                    # Try to decode as UTF-8 (base64 string stored as bytes)
                    encrypted_base64 = file_data.decode('utf-8')
                    print(f"[DOWNLOAD] Attachment {attachment.filename}: found base64 string in DB (decryption failed during sync)")
                except UnicodeDecodeError:
                    # Not a UTF-8 string, must be raw encrypted bytes
                    # Base64 encode the bytes for decryption
                    encrypted_base64 = base64.b64encode(file_data).decode('utf-8')
                    print(f"[DOWNLOAD] Attachment {attachment.filename}: encrypted bytes in DB, base64 encoded for decryption")
                
                print(f"[DOWNLOAD] Attachment {attachment.filename}: base64 length={len(encrypted_base64)}")
                
                decrypt_kwargs = {
                    'ciphertext': encrypted_base64,  # Base64 string (same format as email body)
                    'requester_sae': account_email  # Use account email, not user.email
                }
                
                if attachment.security_level == 'qkd':
                    if attachment.encryption_metadata and 'key_id' in attachment.encryption_metadata:
                        decrypt_kwargs['key_id'] = attachment.encryption_metadata['key_id']
                        print(f"[DOWNLOAD] Decrypting attachment {attachment.filename} with key_id: {decrypt_kwargs['key_id']} for {account_email}")
                    else:
                        print(f"[DOWNLOAD] Warning: Attachment {attachment.filename} is encrypted but no key_id in metadata: {attachment.encryption_metadata}")
                elif attachment.security_level == 'aes':
                    if attachment.encryption_metadata and 'key' in attachment.encryption_metadata:
                        decrypt_kwargs['key_material'] = base64.b64decode(attachment.encryption_metadata['key'])
                
                file_data = crypto_router.decrypt(
                    security_level=attachment.security_level,
                    **decrypt_kwargs
                )
                print(f"[DOWNLOAD] Successfully decrypted attachment: {attachment.filename}")
            except Exception as e:
                import traceback
                print(f"[DOWNLOAD] Decryption failed for {attachment.filename}: {str(e)}")
                print(f"[DOWNLOAD] Traceback: {traceback.format_exc()}")
                return Response(
                    {'error': f'Decryption failed: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # Return file with proper filename and content type
        # Use the stored filename directly (it's already stored correctly)
        filename = attachment.filename or 'attachment'
        
        # Set proper content type (use original, not text/plain)
        content_type = attachment.content_type or 'application/octet-stream'
        # If content_type was set to text/plain during encryption, try to infer from filename
        if content_type == 'text/plain' and filename:
            if filename.endswith('.pdf'):
                content_type = 'application/pdf'
            elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif filename.endswith('.png'):
                content_type = 'image/png'
            elif filename.endswith('.docx'):
                content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            elif filename.endswith('.doc'):
                content_type = 'application/msword'
            elif filename.endswith('.xlsx'):
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            elif filename.endswith('.xls'):
                content_type = 'application/vnd.ms-excel'
        
        response = HttpResponse(file_data, content_type=content_type)
        # Use filename* for proper UTF-8 encoding support
        import urllib.parse
        encoded_filename = urllib.parse.quote(filename, safe='')
        # Set Content-Disposition with both formats for maximum compatibility
        response['Content-Disposition'] = f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}'
        response['Content-Length'] = len(file_data)
        print(f"[DOWNLOAD] Setting Content-Disposition for filename: {filename}")
        return response
        
    except Attachment.DoesNotExist:
        return Response({'error': 'Attachment not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response(
            {'error': f'Failed to download attachment: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
