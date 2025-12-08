import smtplib
import base64
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
                   security_level='regular', encryption_metadata=None, attachments=None):
        """
        Send an email with encrypted attachments
        
        Args:
            to_emails: List of recipient emails
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            from_name: Sender display name (optional)
            security_level: Security level used ('regular', 'aes', 'qkd', 'qrng_pqc')
            encryption_metadata: Encryption metadata dict (for encrypted emails)
            attachments: List of attachment dicts with encrypted_data, filename, etc.
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
        
        # Handle message structure based on whether we have attachments
        if attachments:
            # If we have attachments, message must be multipart/mixed
            msg.make_mixed()
            
            # Add body content as a part
            if body_html:
                # Create multipart/alternative for text/html
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText
                body_part = MIMEMultipart('alternative')
                body_part.attach(MIMEText(body_text, 'plain'))
                body_part.attach(MIMEText(body_html, 'html'))
                msg.attach(body_part)
            else:
                # Just plain text
                from email.mime.text import MIMEText
                msg.attach(MIMEText(body_text, 'plain'))
        else:
            # No attachments - simple message structure
            if body_html:
                msg.add_alternative(body_text, subtype='plain')
                msg.add_alternative(body_html, subtype='html')
            else:
                msg.set_content(body_text)
        
        # Add encrypted attachments
        if attachments:
            for att in attachments:
                try:
                    # IMPORTANT: Send base64 string directly, NOT decoded bytes!
                    # This matches how email body works - send base64 string, receive base64 string
                    encrypted_base64_string = att['encrypted_data']  # This is already a base64 string
                    
                    # Create attachment part
                    attachment_part = EmailMessage()
                    attachment_part.add_header(
                        'Content-Disposition', 
                        f'attachment; filename="{att["filename"]}"'
                    )
                    # Use text/plain for base64 string payload
                    # Don't set Content-Transfer-Encoding - let email library handle it automatically
                    attachment_part.add_header('Content-Type', 'text/plain; charset=utf-8')
                    
                    # Add encryption metadata to attachment headers
                    if security_level != 'regular' and att.get('metadata'):
                        attachment_part['X-QuteMail-Attachment-Encrypted'] = 'true'
                        attachment_part['X-QuteMail-Attachment-Security-Level'] = security_level
                        if 'key_id' in att['metadata']:
                            attachment_part['X-QuteMail-Attachment-Key-ID'] = att['metadata']['key_id']
                        if 'key' in att['metadata']:
                            attachment_part['X-QuteMail-Attachment-AES-Key'] = att['metadata']['key']
                        if 'salt' in att['metadata']:
                            attachment_part['X-QuteMail-Attachment-AES-Salt'] = att['metadata']['salt']
                    
                    # Set encrypted content as base64 STRING (like email body)
                    # The email library will handle the encoding properly
                    attachment_part.set_payload(encrypted_base64_string)
                    
                    # Attach to main message
                    msg.attach(attachment_part)
                    print(f"[SMTP] Attached encrypted file: {att['filename']} (as base64 string)")
                except Exception as e:
                    print(f"[SMTP] Failed to attach {att.get('filename', 'unknown')}: {str(e)}")
                    # Continue with other attachments even if one fails
        
        # Send
        self.connection.send_message(msg)
        
        return True
