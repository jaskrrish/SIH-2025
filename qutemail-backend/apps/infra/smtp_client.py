"""
SMTP client for sending emails
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from typing import List


class SMTPClient:
    """Client for sending emails via SMTP"""
    
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.use_tls = settings.SMTP_USE_TLS
    
    def send_email(self, 
                   from_addr: str,
                   to_addrs: List[str],
                   subject: str,
                   body: str,
                   username: str = None,
                   password: str = None) -> bool:
        """
        Send an email via SMTP
        
        Args:
            from_addr: Sender email address
            to_addrs: List of recipient email addresses
            subject: Email subject
            body: Email body content
            username: SMTP auth username
            password: SMTP auth password
            
        Returns:
            True if successful
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = from_addr
            msg['To'] = ', '.join(to_addrs)
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.host, self.port) as server:
                if self.use_tls:
                    server.starttls()
                
                if username and password:
                    server.login(username, password)
                
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            return False
