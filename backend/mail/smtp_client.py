import smtplib
from email.message import EmailMessage
from email.utils import formataddr


class SMTPClient:
    """Handle SMTP email sending"""
    
    def __init__(self, account):
        """Initialize with EmailAccount instance"""
        self.account = account
        self.connection = None
    
    def connect(self):
        """Connect to SMTP server"""
        try:
            self.connection = smtplib.SMTP(self.account.smtp_host, self.account.smtp_port)
            
            if self.account.smtp_use_tls:
                self.connection.starttls()
            
            # Login
            self.connection.login(self.account.email, self.account.get_app_password())
            return True
        except Exception as e:
            raise Exception(f"SMTP connection failed: {str(e)}")
    
    def disconnect(self):
        """Disconnect from SMTP server"""
        if self.connection:
            try:
                self.connection.quit()
            except:
                pass
    
    def send_email(self, to_emails, subject, body_text, body_html=None, from_name=None, 
                   security_level='regular', encryption_metadata=None):
        """
        Send an email
        
        Args:
            to_emails: List of recipient emails
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            from_name: Sender display name (optional)
            security_level: Security level used ('regular', 'aes', 'qkd', 'qrng_pqc')
            encryption_metadata: Encryption metadata dict (for encrypted emails)
        """
        if not self.connection:
            self.connect()
        
        # Create message
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = formataddr((from_name or self.account.email, self.account.email))
        msg['To'] = ', '.join(to_emails) if isinstance(to_emails, list) else to_emails
        
        # Add custom headers for encrypted emails
        if security_level != 'regular' and encryption_metadata:
            msg['X-QuteMail-Security-Level'] = security_level
            if 'key_id' in encryption_metadata:
                msg['X-QuteMail-Key-ID'] = encryption_metadata['key_id']
            if 'key' in encryption_metadata:
                msg['X-QuteMail-AES-Key'] = encryption_metadata['key']
            if 'salt' in encryption_metadata:
                msg['X-QuteMail-AES-Salt'] = encryption_metadata['salt']
            msg['X-QuteMail-Encrypted'] = 'true'
        
        # Set content
        msg.set_content(body_text)
        if body_html:
            msg.add_alternative(body_html, subtype='html')
        
        # Send
        self.connection.send_message(msg)
        
        return True
