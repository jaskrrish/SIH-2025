from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.http import HttpResponse
from email_accounts.models import EmailAccount
from .models import Email, Attachment
from .serializers import EmailSerializer, SendEmailSerializer
from .imap_client import IMAPClient
from .smtp_client import SMTPClient


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sync_emails(request, account_id):
    """
    Sync/fetch emails from external provider via IMAP
    GET /api/mail/sync/{account_id}
    """
    try:
        account = EmailAccount.objects.get(id=account_id, user=request.user)
    except EmailAccount.DoesNotExist:
        return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        # Connect to IMAP and fetch emails
        print(f"Syncing emails for account: {account.email} (ID: {account.id})")
        imap_client = IMAPClient(account)
        imap_client.connect()
        
        fetched_emails = imap_client.fetch_emails(limit=20)
        print(f"Fetched {len(fetched_emails)} emails from IMAP")
        imap_client.disconnect()
        
        # Save to database
        new_count = 0
        from .models import Attachment
        
        for email_data in fetched_emails:
            # Check if email already exists
            if not Email.objects.filter(message_id=email_data['message_id']).exists():
                # Extract attachments before creating email
                attachments_data = email_data.pop('attachments', [])
                security_level = email_data.pop('security_level', 'regular')
                encryption_metadata = email_data.pop('encryption_metadata', None)
                
                print(f"[SYNC] Processing new email: subject={email_data.get('subject', 'N/A')}, attachments_count={len(attachments_data)}")
                
                # Create email
                email_obj = Email.objects.create(
                    user=request.user,
                    account=account,
                    **email_data
                )
                
                # Save attachments
                for att_data in attachments_data:
                    # Use attachment's own encryption_metadata (with its own key_id)
                    # Don't fall back to email body's metadata as they have different keys
                    att_encryption_metadata = att_data.get('encryption_metadata')
                    if att_encryption_metadata is None and att_data.get('is_encrypted', False):
                        # If attachment is encrypted but no metadata, create minimal metadata
                        att_encryption_metadata = {}
                    
                    # DEBUG: Log attachment data before saving
                    print(f"[SYNC] Saving attachment: {att_data['filename']}")
                    print(f"[SYNC]   - is_encrypted: {att_data.get('is_encrypted', False)}")
                    print(f"[SYNC]   - security_level: {att_data.get('security_level', security_level)}")
                    print(f"[SYNC]   - size: {att_data.get('size', 0)}")
                    print(f"[SYNC]   - file_data type: {type(att_data.get('file_data'))}, len: {len(att_data.get('file_data', b''))}")
                    print(f"[SYNC]   - encryption_metadata: {att_encryption_metadata}")
                    
                    Attachment.objects.create(
                        email=email_obj,
                        filename=att_data['filename'],
                        content_type=att_data['content_type'],
                        size=att_data['size'],
                        file_data=att_data['file_data'],
                        is_encrypted=att_data.get('is_encrypted', False),
                        security_level=att_data.get('security_level', security_level),
                        encryption_metadata=att_encryption_metadata  # Use attachment's own metadata
                    )
                    print(f"[SYNC] Saved attachment: {att_data['filename']} - is_encrypted={att_data.get('is_encrypted', False)}, security_level={att_data.get('security_level', security_level)}, key_id={att_encryption_metadata.get('key_id') if att_encryption_metadata else 'None'}")
                
                new_count += 1
        
        # Update last_synced
        account.last_synced = timezone.now()
        account.save()
        
        return Response({
            'message': f'Synced successfully. {new_count} new emails fetched.',
            'new_emails': new_count,
            'last_synced': account.last_synced
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
    List emails for current user
    GET /api/mail/
    Query params:
        - account_id (optional): Filter by account
        - limit (optional): Number of emails (default 50)
    """
    account_id = request.query_params.get('account_id')
    limit = int(request.query_params.get('limit', 50))
    
    emails = Email.objects.filter(user=request.user)
    
    if account_id:
        emails = emails.filter(account_id=account_id)
    
    emails = emails[:limit]
    
    serializer = EmailSerializer(emails, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_email(request, email_id):
    """
    Get single email details
    GET /api/mail/{email_id}
    """
    try:
        email = Email.objects.get(id=email_id, user=request.user)
        
        # Mark as read
        if not email.is_read:
            email.is_read = True
            email.save()
        
        serializer = EmailSerializer(email)
        return Response(serializer.data)
    except Email.DoesNotExist:
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
                email_content = encryption_result['ciphertext']
                encrypted_metadata = encryption_result['metadata']
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
                        
                        encrypted_attachments.append({
                            'filename': uploaded_file.name,
                            'content_type': uploaded_file.content_type or 'application/octet-stream',
                            'size': original_size,  # Original size
                            'encrypted_data': attachment_encryption['ciphertext'],
                            'encrypted_size': len(base64.b64decode(attachment_encryption['ciphertext'])),
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
