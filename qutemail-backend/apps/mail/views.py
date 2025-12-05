from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
import imaplib
import email
from email.header import decode_header

from apps.email_accounts.models import EmailAccount
from .models import Email


def fetch_emails_via_imap(email_account, limit=50):
    """
    Fetch emails from IMAP server
    Returns: (success, message, emails_list)
    """
    try:
        # Connect to IMAP
        if email_account.imap_use_ssl:
            imap = imaplib.IMAP4_SSL(email_account.imap_host, email_account.imap_port)
        else:
            imap = imaplib.IMAP4(email_account.imap_host, email_account.imap_port)
        
        # Login
        imap.login(email_account.email, email_account.get_password())
        
        # Select INBOX
        imap.select('INBOX')
        
        # Search for recent emails
        _, message_numbers = imap.search(None, 'ALL')
        
        if not message_numbers[0]:
            imap.logout()
            return True, 'No emails found', []
        
        # Get message IDs (last N emails)
        msg_ids = message_numbers[0].split()
        msg_ids = msg_ids[-limit:]  # Get last N emails
        
        emails_data = []
        
        for msg_id in msg_ids:
            # Fetch email
            _, msg_data = imap.fetch(msg_id, '(RFC822)')
            
            if not msg_data or not msg_data[0]:
                continue
            
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # Extract email data
            subject = ''
            if email_message['subject']:
                decoded = decode_header(email_message['subject'])[0]
                subject = decoded[0] if isinstance(decoded[0], str) else decoded[0].decode(decoded[1] or 'utf-8', errors='ignore')
            
            from_addr = email_message['from']
            to_addr = email_message['to'] or ''
            date_str = email_message['date']
            message_id = email_message['message-id'] or f"<{msg_id}@{email_account.email}>"
            
            # Get body
            body_text = ''
            body_html = ''
            
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    if content_type == 'text/plain':
                        body_text = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    elif content_type == 'text/html':
                        body_html = part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                body_text = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            emails_data.append({
                'message_id': message_id,
                'subject': subject,
                'from_address': from_addr,
                'to_addresses': [to_addr],
                'body_text': body_text,
                'body_html': body_html,
                'date': date_str,
                'raw_email': email_body
            })
        
        imap.logout()
        return True, f'Fetched {len(emails_data)} emails', emails_data
        
    except Exception as e:
        return False, f'Error fetching emails: {str(e)}', []


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_email_account(request, account_id):
    """
    Sync emails from an email account via IMAP
    POST /api/mail/sync/{account_id}
    """
    try:
        email_account = EmailAccount.objects.get(id=account_id, user=request.user)
    except EmailAccount.DoesNotExist:
        return Response({
            'error': 'Email account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if not email_account.is_active:
        return Response({
            'error': 'Email account is inactive'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Fetch emails via IMAP
    success, message, emails_data = fetch_emails_via_imap(email_account)
    
    if not success:
        return Response({
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Save emails to database
    new_emails_count = 0
    for email_data in emails_data:
        # Check if email already exists
        message_id = email_data['message_id']
        
        if not Email.objects.filter(message_id=message_id, user=request.user).exists():
            # Create new email
            Email.objects.create(
                user=request.user,
                email_account=email_account,
                message_id=message_id,
                subject=email_data['subject'],
                from_address=email_data['from_address'],
                to_addresses=email_data['to_addresses'],
                body_text=email_data['body_text'],
                body_html=email_data['body_html'],
                raw_email=email_data['raw_email'],
                folder=Email.Folder.INBOX,
                status=Email.Status.RECEIVED,
                is_read=False,
                size=len(email_data['raw_email'])
            )
            new_emails_count += 1
    
    # Update last synced timestamp
    email_account.last_synced_at = timezone.now()
    email_account.save()
    
    return Response({
        'message': f'Successfully synced. {new_emails_count} new emails added.',
        'new_emails': new_emails_count,
        'total_fetched': len(emails_data)
    }, status=status.HTTP_200_OK)
