"""
IMAP client for retrieving emails
"""
import imaplib
import email
from email.header import decode_header
from django.conf import settings
from typing import List, Dict


class IMAPClient:
    """Client for retrieving emails via IMAP"""
    
    def __init__(self):
        self.host = settings.IMAP_HOST
        self.port = settings.IMAP_PORT
        self.use_ssl = settings.IMAP_USE_SSL
    
    def connect(self, username: str, password: str):
        """
        Connect to IMAP server
        
        Args:
            username: IMAP username
            password: IMAP password
            
        Returns:
            IMAP connection object
        """
        if self.use_ssl:
            imap = imaplib.IMAP4_SSL(self.host, self.port)
        else:
            imap = imaplib.IMAP4(self.host, self.port)
        
        imap.login(username, password)
        return imap
    
    def fetch_emails(self, username: str, password: str, folder: str = 'INBOX', limit: int = 10) -> List[Dict]:
        """
        Fetch emails from mailbox
        
        Args:
            username: IMAP username
            password: IMAP password
            folder: Mailbox folder (default: INBOX)
            limit: Maximum number of emails to fetch
            
        Returns:
            List of email dictionaries
        """
        emails = []
        
        try:
            imap = self.connect(username, password)
            imap.select(folder)
            
            # Search for all emails
            status, messages = imap.search(None, 'ALL')
            
            if status != 'OK':
                return emails
            
            # Get message IDs
            msg_ids = messages[0].split()[-limit:]
            
            for msg_id in msg_ids:
                status, msg_data = imap.fetch(msg_id, '(RFC822)')
                
                if status != 'OK':
                    continue
                
                # Parse email
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Extract headers
                subject = self._decode_header(msg['Subject'])
                from_addr = msg['From']
                to_addr = msg['To']
                date = msg['Date']
                
                # Extract body
                body = self._get_body(msg)
                
                emails.append({
                    'id': msg_id.decode(),
                    'subject': subject,
                    'from': from_addr,
                    'to': to_addr,
                    'date': date,
                    'body': body
                })
            
            imap.close()
            imap.logout()
            
        except Exception as e:
            print(f"Failed to fetch emails: {str(e)}")
        
        return emails
    
    @staticmethod
    def _decode_header(header_value):
        """Decode email header"""
        if header_value is None:
            return ""
        
        decoded = decode_header(header_value)
        header_text = ""
        
        for text, encoding in decoded:
            if isinstance(text, bytes):
                header_text += text.decode(encoding or 'utf-8')
            else:
                header_text += text
        
        return header_text
    
    @staticmethod
    def _get_body(msg):
        """Extract email body"""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()
        
        return body
