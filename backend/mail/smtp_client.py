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
    
    def send_email(self, to_emails, subject, body_text, body_html=None, from_name=None):
        """
        Send an email
        
        Args:
            to_emails: List of recipient emails
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            from_name: Sender display name (optional)
        """
        if not self.connection:
            self.connect()
        
        # Create message
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = formataddr((from_name or self.account.email, self.account.email))
        msg['To'] = ', '.join(to_emails) if isinstance(to_emails, list) else to_emails
        
        # Set content
        msg.set_content(body_text)
        if body_html:
            msg.add_alternative(body_html, subtype='html')
        
        # Send
        self.connection.send_message(msg)
        
        return True
