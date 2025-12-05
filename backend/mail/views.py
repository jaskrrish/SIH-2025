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
        
        fetched_emails = imap_client.fetch_emails(limit=50)
        print(f"Fetched {len(fetched_emails)} emails from IMAP")
        imap_client.disconnect()
        
        # Save to database
        new_count = 0
        for email_data in fetched_emails:
            # Check if email already exists
            if not Email.objects.filter(message_id=email_data['message_id']).exists():
                Email.objects.create(
                    user=request.user,
                    account=account,
                    **email_data
                )
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
        # TODO: If use_quantum is True, integrate with crypto hooks from qmailbox
        # For now, send normally
        
        smtp_client = SMTPClient(account)
        smtp_client.connect()
        
        smtp_client.send_email(
            to_emails=data['to_emails'],
            subject=data['subject'],
            body_text=data['body_text'],
            body_html=data.get('body_html'),
            from_name=request.user.name
        )
        
        smtp_client.disconnect()
        
        return Response({
            'message': 'Email sent successfully',
            'encrypted': data['use_quantum']  # Will be true when QKD is integrated
        })
    
    except Exception as e:
        return Response(
            {'error': f'Failed to send email: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
