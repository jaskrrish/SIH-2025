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
    
    def fetch_email_by_id(self, message_id, folder='INBOX'):
        """
        Fetch a single email by Message-ID (on-demand fetch)
        
        Args:
            message_id: Email Message-ID header value
            folder: IMAP folder to search (default: INBOX)
        
        Returns:
            Parsed email dict or None if not found
        """
        if not self.connection:
            self.connect()
        
        # Select mailbox
        self.connection.select(folder)
        
        # Search for email by Message-ID
        # IMAP search syntax: HEADER <field-name> <string>
        search_criteria = f'HEADER Message-ID "{message_id}"'
        _, message_numbers = self.connection.search(None, search_criteria)
        
        if not message_numbers[0]:
            print(f"[IMAP] Email with Message-ID {message_id} not found")
            return None
        
        # Get first match (should be unique)
        num = message_numbers[0].split()[0]
        _, msg_data = self.connection.fetch(num, '(RFC822)')
        
        email_body = msg_data[0][1]
        email_message = email.message_from_bytes(email_body)
        
        # Parse and return email
        return self._parse_email(email_message)
    
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
        
        # Check email body security level FIRST (SAME LOGIC AS EMAIL BODY DECRYPTION)
        email_security_level = email_message.get('X-QuteMail-Security-Level')
        email_is_encrypted = email_message.get('X-QuteMail-Encrypted') == 'true'
        print(f"[IMAP] Email body security check: security_level={email_security_level}, is_encrypted={email_is_encrypted}")
        
        # Get body and attachments
        body_text = ''
        body_html = ''
        attachments = []
        
        if email_message.is_multipart():
            print(f"[IMAP] Email is multipart, walking through parts...")
            part_count = 0
            for part in email_message.walk():
                part_count += 1
                content_type = part.get_content_type()
                content_disposition = part.get('Content-Disposition', '')
                print(f"[IMAP] Part {part_count}: content_type={content_type}, content_disposition={content_disposition}")
                
                # Check if this is an attachment
                if 'attachment' in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        # Decode filename if needed
                        if isinstance(filename, bytes):
                            filename = filename.decode('utf-8', errors='ignore')
                        
                        # Check if encrypted - EXACT SAME LOGIC AS EMAIL BODY
                        # Email body checks: X-QuteMail-Encrypted == 'true' AND X-QuteMail-Security-Level exists and != 'regular'
                        # Attachment checks: X-QuteMail-Attachment-Encrypted == 'true' AND X-QuteMail-Attachment-Security-Level exists and != 'regular'
                        # If headers are NOT present or security_level is 'regular', it's REGULAR (NOT encrypted)
                        att_encrypted_header = part.get('X-QuteMail-Attachment-Encrypted')
                        att_security_level_header = part.get('X-QuteMail-Attachment-Security-Level')
                        
                        # EXACT SAME LOGIC AS EMAIL BODY (line 315-318)
                        if att_encrypted_header == 'true' and att_security_level_header and att_security_level_header != 'regular':
                            is_att_encrypted = True
                            att_security_level = att_security_level_header
                            print(f"[IMAP] Attachment is ENCRYPTED: security_level={att_security_level}")
                        else:
                            # NO encryption headers OR security_level is 'regular' = REGULAR attachment
                            # SAME AS EMAIL BODY: if headers don't exist or security_level is 'regular', it's NOT encrypted
                            is_att_encrypted = False
                            att_security_level = 'regular'
                            print(f"[IMAP] Attachment is REGULAR (X-QuteMail-Attachment-Encrypted={att_encrypted_header}, X-QuteMail-Attachment-Security-Level={att_security_level_header})")
                        
                        # DEBUG: Log attachment detection
                        print(f"[IMAP] Processing attachment: {filename}")
                        print(f"[IMAP]   - is_att_encrypted: {is_att_encrypted}")
                        print(f"[IMAP]   - att_security_level: {att_security_level}")
                        print(f"[IMAP]   - email_security_level: {email_security_level}")
                        print(f"[IMAP]   - email_is_encrypted: {email_is_encrypted}")
                        print(f"[IMAP]   - Content-Type: {content_type}")
                        print(f"[IMAP]   - Content-Disposition: {content_disposition}")
                        print(f"[IMAP]   - All headers: {dict(part.items())}")
                        
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
                            
                            # Store encrypted attachment as-is - DO NOT DECRYPT during fetch!
                            # Decryption will happen on-demand when user downloads attachment
                            original_encrypted_base64 = attachment_data_str
                            attachment_decrypted = False
                            attachment_data = original_encrypted_base64.encode('utf-8')
                            
                            # Extract metadata for later decryption
                            att_metadata = {}
                            if att_security_level == 'qkd':
                                key_id = part.get('X-QuteMail-Attachment-Key-ID')
                                if key_id:
                                    att_metadata['key_id'] = key_id
                            elif att_security_level == 'aes':
                                aes_key = part.get('X-QuteMail-Attachment-AES-Key')
                                aes_salt = part.get('X-QuteMail-Attachment-AES-Salt')
                                if aes_key:
                                    att_metadata['key'] = aes_key
                                elif aes_salt:
                                    att_metadata['salt'] = aes_salt
                            
                            stored_metadata = att_metadata if att_metadata else None
                            print(f"[IMAP] Encrypted attachment stored as-is (security_level={att_security_level}) - will decrypt on download")
                        else:
                            # Regular (non-encrypted) attachment: get as bytes
                            print(f"[IMAP] Regular attachment detected: {filename}")
                            attachment_data = part.get_payload(decode=True)
                            print(f"[IMAP]   - get_payload(decode=True) returned: type={type(attachment_data)}, len={len(attachment_data) if attachment_data else 0}")
                            
                            if attachment_data is None:
                                print(f"[IMAP]   - Payload is None, trying alternative method")
                                payload = part.get_payload()
                                print(f"[IMAP]   - get_payload() returned: type={type(payload)}")
                                if isinstance(payload, str):
                                    try:
                                        attachment_data = base64.b64decode(payload)
                                        print(f"[IMAP]   - Decoded base64 string, len={len(attachment_data)}")
                                    except Exception as e:
                                        print(f"[IMAP]   - Base64 decode failed: {e}, using UTF-8 encode")
                                        attachment_data = payload.encode('utf-8')
                                else:
                                    attachment_data = b''
                                    print(f"[IMAP]   - Payload is not string, using empty bytes")
                            
                            attachment_decrypted = True  # Not encrypted, so "decrypted"
                            stored_metadata = None  # No metadata for regular attachments
                            print(f"[IMAP]   - Final attachment_data: len={len(attachment_data)}, is_encrypted=False, security_level=regular")
                        
                        if len(attachment_data) == 0:
                            print(f"[IMAP] Warning: Empty attachment data for {filename}")
                            continue
                        
                        # Store attachment info
                        # If decrypted, store decrypted bytes; if not, store encrypted bytes (decoded from base64)
                        # CRITICAL: For regular attachments, is_att_encrypted is False (already set above using SAME LOGIC AS EMAIL BODY)
                        final_is_encrypted = is_att_encrypted and not attachment_decrypted
                        final_security_level = att_security_level  # Already set to 'regular' if not encrypted (line 133)
                        
                        # FINAL SAFETY CHECK: Ensure regular attachments are never marked as encrypted
                        if not is_att_encrypted or att_security_level == 'regular':
                            final_is_encrypted = False
                            final_security_level = 'regular'
                            if stored_metadata:
                                stored_metadata = None  # Clear metadata for regular attachments
                            print(f"[IMAP] FINAL SAFETY CHECK: Ensuring regular attachment (is_att_encrypted={is_att_encrypted}, att_security_level={att_security_level})")
                        
                        print(f"[IMAP] Storing attachment: {filename}")
                        print(f"[IMAP]   - is_encrypted: {final_is_encrypted}")
                        print(f"[IMAP]   - security_level: {final_security_level}")
                        print(f"[IMAP]   - size: {len(attachment_data)}")
                        print(f"[IMAP]   - has_metadata: {stored_metadata is not None}")
                        
                        attachments.append({
                            'filename': filename,
                            'content_type': content_type or 'application/octet-stream',
                            'size': len(attachment_data),  # Size of stored data
                            'file_data': attachment_data,  # Binary data (decrypted or encrypted bytes)
                            'is_encrypted': final_is_encrypted,  # Mark as encrypted only if not decrypted
                            'security_level': final_security_level,
                            'encryption_metadata': stored_metadata  # Store metadata (key_id for QKD, key/salt for AES) - same as email body
                        })
                elif content_type == 'text/plain':
                    body_text = part.get_payload(decode=True).decode(errors='ignore')
                elif content_type == 'text/html':
                    body_html = part.get_payload(decode=True).decode(errors='ignore')
        else:
            body_text = email_message.get_payload(decode=True).decode(errors='ignore')
        
        # Check for encryption headers - DO NOT DECRYPT during fetch!
        # Decryption will happen on-demand when user opens the email
        security_level = email_message.get('X-QuteMail-Security-Level')
        is_encrypted = email_message.get('X-QuteMail-Encrypted') == 'true'
        
        if is_encrypted and security_level and security_level != 'regular':
            # Store encrypted content as-is - will decrypt on-demand
            print(f"[IMAP] Encrypted email detected (security_level={security_level}) - storing encrypted, will decrypt on-demand")
            # Keep body_text as encrypted base64 string
        
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
            'sent_at': sent_at.isoformat() if hasattr(sent_at, 'isoformat') else str(sent_at),  # Serialize datetime
            'is_encrypted': is_encrypted,  # Include encryption flag
            'attachments': attachments,  # Include attachments list
            'security_level': security_level if is_encrypted else 'regular',
            'encryption_metadata': {
                'key_id': email_message.get('X-QuteMail-Key-ID') if is_encrypted else None
            } if is_encrypted else None
        }
