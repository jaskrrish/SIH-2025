"""
Email parsing utilities using mail-parser library
"""
import mailparser
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re


class MailParserWrapper:
    """
    Wrapper around mail-parser library for parsing RFC822 email messages

    Provides structured extraction of:
    - Headers (From, To, CC, BCC, Subject, Message-ID, etc.)
    - Body (plain text and HTML)
    - Attachments (files and inline images)
    - Threading metadata (In-Reply-To, References)
    - QKD encryption metadata
    """

    def __init__(self, raw_email: bytes):
        """
        Initialize parser with raw RFC822 email bytes

        Args:
            raw_email: Complete RFC822 message as bytes
        """
        self.raw_email = raw_email
        self.parsed = mailparser.parse_from_bytes(raw_email)

    def get_headers(self) -> Dict[str, str]:
        """
        Extract all email headers

        Returns:
            Dictionary of header name -> value
        """
        return {
            'message_id': self.get_message_id(),
            'subject': self.get_subject(),
            'from': self.get_from(),
            'to': self.get_to(),
            'cc': self.get_cc(),
            'bcc': self.get_bcc(),
            'date': self.get_date(),
            'in_reply_to': self.get_in_reply_to(),
            'references': self.get_references(),
        }

    def get_message_id(self) -> str:
        """Get RFC822 Message-ID header"""
        msg_id = self.parsed.message_id
        if not msg_id:
            # Generate fallback Message-ID if missing
            msg_id = self._generate_message_id()
        return msg_id

    def get_subject(self) -> str:
        """Get email subject"""
        return self.parsed.subject or ''

    def get_from(self) -> str:
        """Get From address"""
        from_list = self.parsed.from_
        if isinstance(from_list, list) and len(from_list) > 0:
            # Extract email address from tuple (name, email)
            return from_list[0][1] if isinstance(from_list[0], tuple) else from_list[0]
        return ''

    def get_to(self) -> List[str]:
        """Get To addresses"""
        return self._extract_email_list(self.parsed.to)

    def get_cc(self) -> List[str]:
        """Get CC addresses"""
        return self._extract_email_list(self.parsed.cc)

    def get_bcc(self) -> List[str]:
        """Get BCC addresses"""
        return self._extract_email_list(self.parsed.bcc)

    def get_date(self) -> Optional[datetime]:
        """
        Get email date from headers

        Returns:
            datetime object or None if parsing fails
        """
        try:
            if self.parsed.date:
                return self.parsed.date
        except:
            pass
        return None

    def get_in_reply_to(self) -> Optional[str]:
        """Get In-Reply-To header for threading"""
        return self.parsed.headers.get('In-Reply-To')

    def get_references(self) -> Optional[str]:
        """Get References header for threading"""
        refs = self.parsed.headers.get('References')
        if refs:
            # References is space-separated list of Message-IDs
            return ' '.join(refs.split()) if isinstance(refs, str) else refs
        return None

    def get_body_text(self) -> str:
        """Get plain text body"""
        return self.parsed.text_plain[0] if self.parsed.text_plain else ''

    def get_body_html(self) -> str:
        """Get HTML body"""
        return self.parsed.text_html[0] if self.parsed.text_html else ''

    def get_attachments(self) -> List[Dict]:
        """
        Extract all attachments including inline images

        Returns:
            List of attachment dictionaries with keys:
            - filename: str
            - content_type: str
            - size: int (bytes)
            - data: bytes
            - checksum: str (SHA-256)
            - content_id: Optional[str] (for inline images)
            - is_inline: bool
        """
        attachments = []

        for attachment in self.parsed.attachments:
            # Extract attachment data
            filename = attachment.get('filename', 'unknown')
            content_type = attachment.get('mail_content_type', 'application/octet-stream')
            data = attachment.get('payload', b'')

            # Calculate SHA-256 checksum
            checksum = hashlib.sha256(data).hexdigest()

            # Check if inline (embedded image)
            content_id = attachment.get('content-id')
            is_inline = content_id is not None

            attachments.append({
                'filename': filename,
                'content_type': content_type,
                'size': len(data),
                'data': data,
                'checksum': checksum,
                'content_id': content_id,
                'is_inline': is_inline,
            })

        return attachments

    def is_encrypted(self) -> bool:
        """
        Check if email is QKD encrypted

        Detects encryption by looking for:
        - [QKD-ENCRYPTED] marker in subject or body
        - X-QKD-Encrypted header
        """
        subject = self.get_subject()
        body = self.get_body_text()

        # Check for encryption markers
        if '[QKD-ENCRYPTED]' in subject or '[ENCRYPTED MESSAGE]' in body:
            return True

        # Check custom header
        if self.parsed.headers.get('X-QKD-Encrypted') == 'true':
            return True

        return False

    def get_qkd_metadata(self) -> Optional[Dict]:
        """
        Extract QKD encryption metadata from email body

        Expected format in body:
        [ENCRYPTED MESSAGE]
        Key ID: <key_id>
        Ciphertext: <hex_ciphertext>
        Nonce: <hex_nonce>
        Tag: <hex_tag>

        Returns:
            Dictionary with qkd_key_id, ciphertext, nonce, tag or None
        """
        if not self.is_encrypted():
            return None

        body = self.get_body_text()

        # Extract QKD metadata using regex
        metadata = {}

        # Extract Key ID
        key_match = re.search(r'Key ID:\s*([a-zA-Z0-9\-_]+)', body)
        if key_match:
            metadata['qkd_key_id'] = key_match.group(1)

        # Extract Ciphertext (hex encoded)
        cipher_match = re.search(r'Ciphertext:\s*([a-fA-F0-9]+)', body)
        if cipher_match:
            metadata['ciphertext'] = cipher_match.group(1)

        # Extract Nonce (hex encoded)
        nonce_match = re.search(r'Nonce:\s*([a-fA-F0-9]+)', body)
        if nonce_match:
            metadata['nonce'] = nonce_match.group(1)

        # Extract Tag (hex encoded)
        tag_match = re.search(r'Tag:\s*([a-fA-F0-9]+)', body)
        if tag_match:
            metadata['tag'] = tag_match.group(1)

        return metadata if metadata else None

    def has_attachments(self) -> bool:
        """Check if email has any attachments"""
        return len(self.parsed.attachments) > 0

    @staticmethod
    def _extract_email_list(email_data) -> List[str]:
        """
        Extract email addresses from mail-parser data structure

        Args:
            email_data: Can be list of tuples (name, email) or strings

        Returns:
            List of email address strings
        """
        if not email_data:
            return []

        emails = []
        for item in email_data:
            if isinstance(item, tuple) and len(item) >= 2:
                # Tuple format: (name, email)
                emails.append(item[1])
            elif isinstance(item, str):
                emails.append(item)

        return emails

    def _generate_message_id(self) -> str:
        """
        Generate a Message-ID if missing from headers

        Uses SHA-256 hash of raw email content
        """
        hash_obj = hashlib.sha256(self.raw_email)
        return f"<{hash_obj.hexdigest()}@qutemail.local>"

    def to_dict(self) -> Dict:
        """
        Convert parsed email to dictionary format suitable for database storage

        Returns:
            Dictionary with all email data
        """
        return {
            'message_id': self.get_message_id(),
            'subject': self.get_subject(),
            'from_address': self.get_from(),
            'to_addresses': self.get_to(),
            'cc_addresses': self.get_cc(),
            'bcc_addresses': self.get_bcc(),
            'date': self.get_date(),
            'in_reply_to': self.get_in_reply_to(),
            'references': self.get_references(),
            'body_text': self.get_body_text(),
            'body_html': self.get_body_html(),
            'raw_email': self.raw_email,
            'is_encrypted': self.is_encrypted(),
            'qkd_metadata': self.get_qkd_metadata(),
            'has_attachments': self.has_attachments(),
            'attachments': self.get_attachments(),
        }


def parse_email(raw_email: bytes) -> Dict:
    """
    Convenience function to parse an email and return dictionary

    Args:
        raw_email: Complete RFC822 message as bytes

    Returns:
        Dictionary with parsed email data
    """
    parser = MailParserWrapper(raw_email)
    return parser.to_dict()
