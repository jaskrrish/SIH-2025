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
        
        # Add attachments (regular or encrypted)
        if attachments:
            for att in attachments:
                try:
                    if security_level == 'regular':
                        # REGULAR: No encryption - send as binary with proper content type
                        # Decode base64 back to binary (it was base64 encoded for storage only)
                        print(f"[SMTP] Processing REGULAR attachment: {att['filename']}")
                        print(f"[SMTP]   - encrypted_data type: {type(att['encrypted_data'])}, len: {len(att['encrypted_data']) if isinstance(att['encrypted_data'], str) else 'N/A'}")
                        attachment_data = base64.b64decode(att['encrypted_data'])
                        print(f"[SMTP]   - Decoded to binary: {len(attachment_data)} bytes")
                        content_type = att.get('content_type', 'application/octet-stream')
                        print(f"[SMTP]   - Content-Type: {content_type}")
                        
                        # Use MIMEBase for binary files (properly handles encoding)
                        from email.mime.base import MIMEBase
                        from email import encoders
                        attachment_part = MIMEBase(*content_type.split('/', 1))
                        attachment_part.set_payload(attachment_data)
                        encoders.encode_base64(attachment_part)  # Base64 encode for email transport
                        attachment_part.add_header(
                            'Content-Disposition', 
                            f'attachment; filename="{att["filename"]}"'
                        )
                        print(f"[SMTP]   - NO encryption headers added (regular attachment)")
                        print(f"[SMTP] Attached regular file: {att['filename']} ({len(attachment_data)} bytes, {content_type})")
                    else:
                        # ENCRYPTED (AES or QKD): Send as base64 string (like email body)
                        # Create attachment part
                        attachment_part = EmailMessage()
                        attachment_part.add_header(
                            'Content-Disposition', 
                            f'attachment; filename="{att["filename"]}"'
                        )
                        encrypted_base64_string = att['encrypted_data']  # Already a base64 string
                        attachment_part.add_header('Content-Type', 'text/plain; charset=utf-8')
                        
                        # Add encryption metadata to headers (same as email body headers)
                        attachment_part['X-QuteMail-Attachment-Encrypted'] = 'true'
                        attachment_part['X-QuteMail-Attachment-Security-Level'] = security_level
                        
                        print(f"[SMTP] Processing ENCRYPTED attachment: {att['filename']} (security: {security_level})")
                        print(f"[SMTP]   - metadata: {att.get('metadata', {})}")
                        
                        if att.get('metadata'):
                            # For QKD: store key_id (same as email body)
                            if 'key_id' in att['metadata']:
                                attachment_part['X-QuteMail-Attachment-Key-ID'] = att['metadata']['key_id']
                                print(f"[SMTP]   - Set X-QuteMail-Attachment-Key-ID: {att['metadata']['key_id']}")
                            # For AES: store key (same as email body)
                            if 'key' in att['metadata']:
                                attachment_part['X-QuteMail-Attachment-AES-Key'] = att['metadata']['key']
                                print(f"[SMTP]   - Set X-QuteMail-Attachment-AES-Key: {att['metadata']['key'][:50]}... (base64 key)")
                            if 'salt' in att['metadata']:
                                attachment_part['X-QuteMail-Attachment-AES-Salt'] = att['metadata']['salt']
                                print(f"[SMTP]   - Set X-QuteMail-Attachment-AES-Salt")
                        else:
                            print(f"[SMTP]   - WARNING: No metadata found for encrypted attachment!")
                        
                        # Set encrypted content as base64 STRING (like email body)
                        attachment_part.set_payload(encrypted_base64_string)
                        print(f"[SMTP] Attached encrypted file: {att['filename']} (security: {security_level}, as base64 string, length: {len(encrypted_base64_string)})")
                    
                    # Attach to main message
                    msg.attach(attachment_part)
                except Exception as e:
                    print(f"[SMTP] Failed to attach {att.get('filename', 'unknown')}: {str(e)}")
                    import traceback
                    print(f"[SMTP] Traceback: {traceback.format_exc()}")
                    # Continue with other attachments even if one fails
        
        # Send
        self.connection.send_message(msg)
        
        return True
