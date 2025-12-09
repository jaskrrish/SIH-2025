from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from email_accounts.models import EmailAccount
from .models import Email
from .serializers import EmailSerializer, SendEmailSerializer
from .imap_client import IMAPClient
from .smtp_client import SMTPClient


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sync_emails(request, account_id):
    """
    Sync emails for an account.
    Auto-detects which folders exist on the IMAP server (inbox, sent, draft, trash).
    Optional query: ?folder=inbox|sent|draft|trash to sync only that folder
    """
    try:
        account = EmailAccount.objects.get(id=account_id, user=request.user)
    except EmailAccount.DoesNotExist:
        return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)

    # Optional single folder
    folder_param = request.query_params.get("folder")
    FOLDERS = ["inbox", "sent", "draft", "trash"]
    requested_folders = [folder_param] if folder_param in FOLDERS else FOLDERS

    folder_results = {}

    try:
        imap_client = IMAPClient(account)
        imap_client.connect()

        # Get server folders
        available_folders = imap_client.list_folders()
        print("[IMAP] Available folders:", available_folders)

        # Map frontend labels to real IMAP folders
        IMAP_FOLDER_MAP = {
            "inbox": "INBOX",
            "sent": "[Gmail]/Sent Mail",
            "draft": "[Gmail]/Drafts",
            "trash": "[Gmail]/Trash",
        }

        # Only sync folders that exist on the server
        folders_to_sync = {}
        for label in requested_folders:
            imap_folder = IMAP_FOLDER_MAP[label]
            if imap_folder in available_folders:
                folders_to_sync[label] = imap_folder
            else:
                print(f"[IMAP] Folder {imap_folder} not found on server, skipping")

        # Fetch and store emails
        for label, imap_folder in folders_to_sync.items():
            try:
                fetched_emails = imap_client.fetch_emails(folder=imap_folder, limit=20)
                new_count = 0
                for email_data in fetched_emails:
                    if not Email.objects.filter(message_id=email_data["message_id"]).exists():
                        Email.objects.create(
                            user=request.user,
                            account=account,
                            folder=email_data.get('folder', label),
                            message_id=email_data['message_id'],
                            subject=email_data.get('subject', '(No Subject)'),
                            from_email=email_data.get('from_email', ''),
                            from_name=email_data.get('from_name', ''),
                            to_emails=email_data.get('to_emails', '[]'),
                            cc_emails=email_data.get('cc_emails', '[]'),
                            bcc_emails=email_data.get('bcc_emails', '[]'),
                            body_text=email_data.get('body_text', ''),
                            body_html=email_data.get('body_html', ''),
                            sent_at=email_data.get('sent_at', timezone.now()),
                            is_encrypted=email_data.get('is_encrypted', False)
                        )
                        new_count += 1
                folder_results[label] = new_count
            except Exception as e:
                print(f"[IMAP] Could not fetch {imap_folder}: {e}")
                folder_results[label] = f"Error: {e}"

        imap_client.disconnect()

        account.last_synced = timezone.now()
        account.save()

        return Response({
            "message": "Sync completed",
            "folders": folder_results
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_emails(request):
    """
    List emails
    Query params:
        - account_id (optional)
        - folder (inbox | sent | draft | trash)
        - limit (default 50)
    """

    account_id = request.query_params.get("account_id")
    folder = request.query_params.get("folder", "inbox")
    limit = int(request.query_params.get("limit", 50))

    emails = Email.objects.filter(
        user=request.user,
        folder=folder
    )

    if account_id:
        emails = emails.filter(account_id=account_id)

    emails = emails.order_by("-sent_at")[:limit]

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
    Send an email via SMTP
    POST /api/mail/send
    Body: {
        account_id, to_emails[], subject, body_text, body_html (optional),
        use_quantum (boolean, default false)
    }
    """
    serializer = SendEmailSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    try:
        account = EmailAccount.objects.get(id=data['account_id'], user=request.user)
    except EmailAccount.DoesNotExist:
        return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        security_level = data.get('security_level', 'regular')
        
        # Prepare email content
        email_content = data['body_text']
        encrypted_metadata = None
        
        # Encrypt if security level is not 'regular'
        if security_level != 'regular':
            from crypto import router as crypto_router
            
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
        
        smtp_client = SMTPClient(account)
        smtp_client.connect()
        
        smtp_client.send_email(
            to_emails=data['to_emails'],
            subject=data['subject'],
            body_text=email_content,
            body_html=data.get('body_html'),
            from_name=request.user.name,
            security_level=security_level,
            encryption_metadata=encrypted_metadata
        )
        
        smtp_client.disconnect()
        
        return Response({
            'message': 'Email sent successfully',
            'security_level': security_level,
            'encrypted': security_level != 'regular',
            'metadata': encrypted_metadata
        })
    
    except Exception as e:
        return Response(
            {'error': f'Failed to send email: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
