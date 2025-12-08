import imaplib
import email
import base64
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
        
        # Get body and attachments
        body_text = ''
        body_html = ''
        attachments = []
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = part.get('Content-Disposition', '')
                
                # Check if this is an attachment
                if 'attachment' in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        # Decode filename if needed
                        if isinstance(filename, bytes):
                            filename = filename.decode('utf-8', errors='ignore')
                        
                        # Check if encrypted FIRST to determine how to handle payload
                        is_att_encrypted = part.get('X-QuteMail-Attachment-Encrypted') == 'true'
                        att_security_level = part.get('X-QuteMail-Attachment-Security-Level')
                        
                        # Get attachment data
                        # For encrypted attachments, payload is base64 STRING (like email body)
                        # For regular attachments, payload is binary bytes
                        if is_att_encrypted:
                            # Encrypted attachment: payload is base64 string (like email body)
                            # IMPORTANT: Don't use decode=True - we want the string, not decoded bytes!
                            # The email library will handle base64 decoding automatically if Content-Transfer-Encoding is set
                            payload = part.get_payload(decode=False)  # Get as string, not decoded
                            
                            if isinstance(payload, str):
                                # Remove any whitespace/newlines from base64 string
                                encrypted_base64_string = payload.strip().replace('\n', '').replace('\r', '').replace(' ', '')
                                attachment_data_str = encrypted_base64_string
                            elif isinstance(payload, list):
                                # If it's a list (multipart), get the first part
                                if len(payload) > 0:
                                    first_part = payload[0]
                                    if isinstance(first_part, str):
                                        attachment_data_str = first_part.strip().replace('\n', '').replace('\r', '').replace(' ', '')
                                    else:
                                        attachment_data_str = str(first_part).strip()
                                else:
                                    attachment_data_str = ''
                            else:
                                attachment_data_str = str(payload).strip() if payload else ''
                            
                            if not attachment_data_str:
                                print(f"[IMAP] Warning: Empty encrypted attachment data for {filename}")
                                continue
                            
                            # Store original encrypted base64 string for potential decryption later
                            original_encrypted_base64 = attachment_data_str
                            attachment_decrypted = False
                            
                            # Try to decrypt
                            try:
                                from crypto import router as crypto_router
                                
                                # Decrypt using base64 string directly (like email body)
                                decrypt_kwargs = {
                                    'ciphertext': attachment_data_str,  # Already base64 string!
                                    'requester_sae': self.account.email
                                }
                                
                                # Add level-specific parameters
                                if att_security_level == 'qkd':
                                    key_id = part.get('X-QuteMail-Attachment-Key-ID')
                                    if key_id:
                                        decrypt_kwargs['key_id'] = key_id
                                        print(f"[IMAP] Decrypting attachment {filename} with key_id: {key_id}")
                                elif att_security_level == 'aes':
                                    aes_key = part.get('X-QuteMail-Attachment-AES-Key')
                                    if aes_key:
                                        decrypt_kwargs['key_material'] = base64.b64decode(aes_key)
                                
                                # Decrypt attachment (same as email body - pass base64 string directly)
                                decrypted_bytes = crypto_router.decrypt(
                                    security_level=att_security_level,
                                    **decrypt_kwargs
                                )
                                attachment_data = decrypted_bytes
                                attachment_decrypted = True
                                print(f"[IMAP] Successfully decrypted attachment: {filename}")
                            except Exception as e:
                                import traceback
                                print(f"[IMAP] Attachment decryption failed for {filename}: {str(e)}")
                                print(f"[IMAP] Traceback: {traceback.format_exc()}")
                                # Decryption failed - store the encrypted base64 string as bytes
                                # We'll need to decode it back to base64 string on download
                                # Store the base64 string encoded as UTF-8 bytes so we can retrieve it later
                                attachment_data = original_encrypted_base64.encode('utf-8')
                                attachment_decrypted = False
                                print(f"[IMAP] Storing encrypted attachment as base64 string (will retry decryption on download)")
                        else:
                            # Regular (non-encrypted) attachment: get as bytes
                            attachment_data = part.get_payload(decode=True)
                            if attachment_data is None:
                                payload = part.get_payload()
                                if isinstance(payload, str):
                                    try:
                                        attachment_data = base64.b64decode(payload)
                                    except:
                                        attachment_data = payload.encode('utf-8')
                                else:
                                    attachment_data = b''
                            attachment_decrypted = True  # Not encrypted, so "decrypted"
                        
                        if len(attachment_data) == 0:
                            print(f"[IMAP] Warning: Empty attachment data for {filename}")
                            continue
                        
                        # Store attachment info
                        # If decrypted, store decrypted bytes; if not, store encrypted bytes (decoded from base64)
                        attachments.append({
                            'filename': filename,
                            'content_type': content_type or 'application/octet-stream',
                            'size': len(attachment_data),  # Size of stored data
                            'file_data': attachment_data,  # Binary data (decrypted or encrypted bytes)
                            'is_encrypted': is_att_encrypted and not attachment_decrypted,  # Mark as encrypted only if not decrypted
                            'security_level': att_security_level if is_att_encrypted else 'regular',
                            'encryption_metadata': {
                                'key_id': part.get('X-QuteMail-Attachment-Key-ID') if is_att_encrypted else None
                            } if is_att_encrypted else None
                        })
                elif content_type == 'text/plain':
                    body_text = part.get_payload(decode=True).decode(errors='ignore')
                elif content_type == 'text/html':
                    body_html = part.get_payload(decode=True).decode(errors='ignore')
        else:
            body_text = email_message.get_payload(decode=True).decode(errors='ignore')
        
        # Check for encryption headers and decrypt if needed
        security_level = email_message.get('X-QuteMail-Security-Level')
        is_encrypted = email_message.get('X-QuteMail-Encrypted') == 'true'
        
        if is_encrypted and security_level and security_level != 'regular':
            try:
                from crypto import router as crypto_router
                # base64 is already imported at module level
                
                # Prepare decryption parameters based on security level
                decrypt_kwargs = {
                    'ciphertext': body_text,
                    'requester_sae': self.account.email
                }
                
                # Add level-specific parameters
                if security_level == 'qkd':
                    key_id = email_message.get('X-QuteMail-Key-ID')
                    if key_id:
                        decrypt_kwargs['key_id'] = key_id
                elif security_level == 'aes':
                    aes_key = email_message.get('X-QuteMail-AES-Key')
                    aes_salt = email_message.get('X-QuteMail-AES-Salt')
                    if aes_key:
                        decrypt_kwargs['key_material'] = base64.b64decode(aes_key)
                    elif aes_salt:
                        # Would need passphrase - not implemented in this flow
                        decrypt_kwargs['salt'] = base64.b64decode(aes_salt)
                
                # Decrypt the body
                decrypted_bytes = crypto_router.decrypt(
                    security_level=security_level,
                    **decrypt_kwargs
                )
                body_text = decrypted_bytes.decode('utf-8')
                print(f"[IMAP] Successfully decrypted email with security level: {security_level}")
            except Exception as e:
                print(f"[IMAP] Decryption failed: {str(e)}")
                body_text = f"[Encrypted message - decryption failed: {str(e)}]\n\nCiphertext: {body_text}"
        
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
            'is_encrypted': is_encrypted,  # Include encryption flag
            'attachments': attachments,  # Include attachments list
            'security_level': security_level if is_encrypted else 'regular',
            'encryption_metadata': {
                'key_id': email_message.get('X-QuteMail-Key-ID') if is_encrypted else None
            } if is_encrypted else None
        }
