import imaplib
import email
from email.header import decode_header
from datetime import datetime
from .models import Email
import json


class IMAPClient:
    """Handle IMAP email fetching"""
    
    def __init__(self, account):
        """Initialize with EmailAccount instance"""
        self.account = account
        self.connection = None
    
    def connect(self):
        """Connect to IMAP server"""
        try:
            if self.account.imap_use_ssl:
                self.connection = imaplib.IMAP4_SSL(self.account.imap_host, self.account.imap_port)
            else:
                self.connection = imaplib.IMAP4(self.account.imap_host, self.account.imap_port)
            
            # Login
            password = self.account.get_app_password()
            # print(f"IMAP Login attempt - Host: {self.account.imap_host}:{self.account.imap_port}")
            # print(f"IMAP Login attempt - Email: {self.account.email}")
            # print(f"IMAP Login attempt - Password length: {len(password)} chars")
            # print(f"IMAP Login attempt - Password first 4 chars: '{password}'")
            
            self.connection.login(self.account.email, password)
            print("IMAP Login successful!")
            return True
        except Exception as e:
            print(f"IMAP Login failed: {str(e)}")
            raise Exception(f"IMAP connection failed: {str(e)}")
    
    def disconnect(self):
        """Disconnect from IMAP server"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except:
                pass
    
    def fetch_emails(self, folder='INBOX', limit=50):
        """Fetch emails from specified folder"""
        if not self.connection:
            self.connect()
        
        # Select mailbox
        self.connection.select(folder)
        
        # Search for all emails
        _, message_numbers = self.connection.search(None, 'ALL')
        
        emails = []
        # Get the last 'limit' emails
        for num in message_numbers[0].split()[-limit:]:
            _, msg_data = self.connection.fetch(num, '(RFC822)')
            
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # Parse email
            parsed_email = self._parse_email(email_message)
            emails.append(parsed_email)
        
        return emails
    
    def _parse_email(self, email_message):
        """Parse email message into dict"""
        # Decode subject
        subject, encoding = decode_header(email_message['Subject'])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or 'utf-8', errors='ignore')
        
        # Get sender
        from_header = email_message.get('From', '')
        from_email = email.utils.parseaddr(from_header)[1]
        from_name = email.utils.parseaddr(from_header)[0]
        
        # Get recipients
        to_emails = [addr[1] for addr in email.utils.getaddresses([email_message.get('To', '')])]
        cc_emails = [addr[1] for addr in email.utils.getaddresses([email_message.get('Cc', '')])]
        
        # Get body
        body_text = ''
        body_html = ''
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    body_text = part.get_payload(decode=True).decode(errors='ignore')
                elif content_type == 'text/html':
                    body_html = part.get_payload(decode=True).decode(errors='ignore')
        else:
            body_text = email_message.get_payload(decode=True).decode(errors='ignore')
        
        # Get date
        date_str = email_message.get('Date')
        sent_at = email.utils.parsedate_to_datetime(date_str) if date_str else datetime.now()
        
        # Message ID
        message_id = email_message.get('Message-ID', f'<{id(email_message)}@local>')
        
        return {
            'message_id': message_id,
            'subject': subject or '(No Subject)',
            'from_email': from_email,
            'from_name': from_name,
            'to_emails': json.dumps(to_emails),
            'cc_emails': json.dumps(cc_emails),
            'bcc_emails': json.dumps([]),
            'body_text': body_text,
            'body_html': body_html,
            'sent_at': sent_at,
        }
