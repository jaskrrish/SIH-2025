"""
Email Processing Service

Handles email routing, QKD encryption for internal emails,
and integration with external SMTP for outbound delivery.
"""

import email
import logging
import uuid
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr, formataddr, make_msgid
from typing import List, Tuple, Optional
from datetime import timezone as dt_timezone

from django.conf import settings
from django.utils import timezone

from mail.models import Mailbox, Email, EmailAttachment
from qkd.services import QKDService
from crypto.utils import hybrid_encrypt, hybrid_decrypt
from infra.storage import LocalStorageAdapter

logger = logging.getLogger('email_processing')


class EmailProcessingService:
    """
    Core service for processing incoming and outgoing emails.

    Responsibilities:
    - Parse MIME messages
    - Determine internal vs external emails
    - Apply QKD encryption for internal emails
    - Store emails in database
    - Handle attachments
    - Queue external emails for delivery
    """

    def __init__(self):
        self.qkd_service = QKDService()
        self.storage_adapter = LocalStorageAdapter()
        self.domain = settings.EMAIL_DOMAIN

    def is_internal_email(self, from_addr: str, to_addrs: List[str]) -> bool:
        """
        Check if email is internal (all parties are @yourdomain.com).

        Args:
            from_addr: Sender email address
            to_addrs: List of recipient email addresses

        Returns:
            True if all addresses are internal, False otherwise
        """
        all_addrs = [from_addr] + to_addrs

        for addr in all_addrs:
            # Extract email from "Name <email>" format
            _, email_addr = parseaddr(addr)
            if not email_addr.lower().endswith(f'@{self.domain}'.lower()):
                return False

        return True

    async def process_incoming_email(self, envelope: dict) -> bool:
        """
        Main processing pipeline for incoming SMTP emails.

        Args:
            envelope: Dictionary with mail_from, rcpt_tos, content, peer

        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            # Parse MIME message
            msg = BytesParser(policy=policy.default).parsebytes(envelope['content'])

            # Extract metadata
            from_addr = envelope['mail_from']
            to_addrs = envelope['rcpt_tos']
            subject = self._decode_header(msg.get('Subject', ''))
            message_id = msg.get('Message-ID', make_msgid())

            # Extract body content
            body_plain = self._extract_plain_body(msg)
            body_html = self._extract_html_body(msg)

            # Determine internal vs external
            is_internal = self.is_internal_email(from_addr, to_addrs)

            logger.info(
                f"Processing {'internal' if is_internal else 'external'} email "
                f"from {from_addr} to {to_addrs}"
            )

            # Process based on type
            if is_internal:
                return await self._process_internal_email(
                    from_addr, to_addrs, subject, body_plain, body_html, msg, message_id
                )
            else:
                return await self._process_external_email(
                    from_addr, to_addrs, subject, body_plain, body_html, msg, message_id
                )

        except Exception as e:
            logger.error(f"Error processing incoming email: {str(e)}", exc_info=True)
            return False

    async def _process_internal_email(
        self,
        from_addr: str,
        to_addrs: List[str],
        subject: str,
        body_plain: str,
        body_html: Optional[str],
        msg: email.message.Message,
        message_id: str
    ) -> bool:
        """
        Process internal email with QKD encryption.

        Args:
            from_addr: Sender address
            to_addrs: List of recipients
            subject: Email subject
            body_plain: Plain text body
            body_html: HTML body (optional)
            msg: Full MIME message
            message_id: Message ID

        Returns:
            True if successful
        """
        try:
            logger.info("Processing internal email with QKD encryption")

            # Request QKD key
            key_id, key_material = self.qkd_service.request_key(size=256)
            logger.info(f"Obtained QKD key: {key_id}")

            # Encrypt body using QKD key
            ciphertext, nonce, auth_tag = hybrid_encrypt(
                plaintext=body_plain.encode('utf-8'),
                key_material=key_material,
                context=b'email-encryption'
            )

            # Calculate email size
            size_bytes = len(msg.as_bytes())

            # Store email for each recipient
            for to_addr in to_addrs:
                _, email_addr = parseaddr(to_addr)

                try:
                    # Get recipient mailbox
                    mailbox = Mailbox.objects.get(email_address__iexact=email_addr)

                    # Check quota
                    if not mailbox.has_quota_available(size_bytes):
                        logger.warning(
                            f"Mailbox {email_addr} quota exceeded, email rejected"
                        )
                        continue

                    # Create email record
                    email_obj = Email.objects.create(
                        mailbox=mailbox,
                        message_id=message_id,
                        from_address=from_addr,
                        to_addresses=to_addrs,
                        cc_addresses=self._extract_addresses(msg.get_all('Cc', [])),
                        bcc_addresses=[],
                        subject=subject,
                        body_plain='',  # Stored encrypted
                        body_html='',
                        is_internal=True,
                        qkd_key_id=key_id,
                        qkd_ciphertext=ciphertext.hex(),
                        qkd_nonce=nonce.hex(),
                        qkd_auth_tag=auth_tag.hex(),
                        size_bytes=size_bytes,
                        folder='INBOX',
                        headers=self._extract_headers(msg)
                    )

                    logger.info(f"Email stored for {email_addr} with QKD encryption")

                    # Process attachments
                    await self._process_attachments(msg, email_obj)

                except Mailbox.DoesNotExist:
                    logger.error(f"Mailbox not found: {email_addr}")
                    continue

            # Confirm key usage with QKD service
            self.qkd_service.confirm_key(key_id)
            logger.info(f"QKD key {key_id} confirmed")

            return True

        except Exception as e:
            logger.error(f"Error processing internal email: {str(e)}", exc_info=True)
            return False

    async def _process_external_email(
        self,
        from_addr: str,
        to_addrs: List[str],
        subject: str,
        body_plain: str,
        body_html: Optional[str],
        msg: email.message.Message,
        message_id: str
    ) -> bool:
        """
        Process external email (no QKD encryption).

        Args:
            from_addr: Sender address
            to_addrs: List of recipients
            subject: Email subject
            body_plain: Plain text body
            body_html: HTML body (optional)
            msg: Full MIME message
            message_id: Message ID

        Returns:
            True if successful
        """
        try:
            logger.info("Processing external email (no QKD)")

            size_bytes = len(msg.as_bytes())

            # Process each recipient
            for to_addr in to_addrs:
                _, email_addr = parseaddr(to_addr)

                # Check if recipient is local
                if email_addr.lower().endswith(f'@{self.domain}'.lower()):
                    # Incoming external email - store locally
                    try:
                        mailbox = Mailbox.objects.get(email_address__iexact=email_addr)

                        # Check quota
                        if not mailbox.has_quota_available(size_bytes):
                            logger.warning(
                                f"Mailbox {email_addr} quota exceeded, email rejected"
                            )
                            continue

                        # Create email record
                        email_obj = Email.objects.create(
                            mailbox=mailbox,
                            message_id=message_id,
                            from_address=from_addr,
                            to_addresses=[to_addr],
                            cc_addresses=self._extract_addresses(msg.get_all('Cc', [])),
                            bcc_addresses=[],
                            subject=subject,
                            body_plain=body_plain,
                            body_html=body_html,
                            is_internal=False,
                            size_bytes=size_bytes,
                            folder='INBOX',
                            headers=self._extract_headers(msg)
                        )

                        logger.info(f"External email stored for {email_addr}")

                        # Process attachments
                        await self._process_attachments(msg, email_obj)

                    except Mailbox.DoesNotExist:
                        logger.error(f"Mailbox not found: {email_addr}")
                        continue

                else:
                    # Outgoing external email - queue for delivery
                    await self._queue_external_delivery(from_addr, to_addr, msg)

            return True

        except Exception as e:
            logger.error(f"Error processing external email: {str(e)}", exc_info=True)
            return False

    async def _queue_external_delivery(
        self,
        from_addr: str,
        to_addr: str,
        msg: email.message.Message
    ):
        """
        Queue outbound email to external SMTP server.

        Args:
            from_addr: Sender address
            to_addr: Recipient address
            msg: MIME message
        """
        try:
            from mail.tasks import deliver_external_email

            logger.info(f"Queueing external delivery from {from_addr} to {to_addr}")

            # Queue Celery task
            deliver_external_email.delay(
                from_addr=from_addr,
                to_addr=to_addr,
                message_bytes=msg.as_bytes()
            )

            logger.info(f"External delivery queued for {to_addr}")

        except Exception as e:
            logger.error(f"Error queueing external delivery: {str(e)}", exc_info=True)

    async def _process_attachments(
        self,
        msg: email.message.Message,
        email_obj: Email
    ):
        """
        Extract and store email attachments.

        Args:
            msg: MIME message
            email_obj: Email model instance
        """
        for part in msg.walk():
            # Check if this is an attachment
            content_disposition = part.get_content_disposition()

            if content_disposition in ('attachment', 'inline'):
                filename = part.get_filename()

                if not filename:
                    # Generate filename for unnamed attachments
                    ext = part.get_content_type().split('/')[-1]
                    filename = f"attachment_{uuid.uuid4().hex[:8]}.{ext}"

                try:
                    # Get attachment content
                    content = part.get_payload(decode=True)

                    if content:
                        # Save to storage
                        storage_path = self.storage_adapter.save(
                            f'attachments/{email_obj.id}/{filename}',
                            content
                        )

                        # Create attachment record
                        EmailAttachment.objects.create(
                            email=email_obj,
                            filename=filename,
                            content_type=part.get_content_type(),
                            size_bytes=len(content),
                            storage_path=storage_path,
                            is_inline=(content_disposition == 'inline'),
                            content_id=part.get('Content-ID', '').strip('<>')
                        )

                        logger.info(f"Attachment saved: {filename} ({len(content)} bytes)")

                except Exception as e:
                    logger.error(f"Error processing attachment {filename}: {str(e)}")

    def _extract_plain_body(self, msg: email.message.Message) -> str:
        """
        Extract plain text body from MIME message.

        Args:
            msg: MIME message

        Returns:
            Plain text body
        """
        body = ''

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            body = payload.decode(charset, errors='replace')
                            break
                        except Exception as e:
                            logger.warning(f"Error decoding body: {str(e)}")
        else:
            if msg.get_content_type() == 'text/plain':
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    try:
                        body = payload.decode(charset, errors='replace')
                    except Exception as e:
                        logger.warning(f"Error decoding body: {str(e)}")

        return body

    def _extract_html_body(self, msg: email.message.Message) -> Optional[str]:
        """
        Extract HTML body from MIME message.

        Args:
            msg: MIME message

        Returns:
            HTML body or None
        """
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/html':
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            return payload.decode(charset, errors='replace')
                        except Exception as e:
                            logger.warning(f"Error decoding HTML body: {str(e)}")
        else:
            if msg.get_content_type() == 'text/html':
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    try:
                        return payload.decode(charset, errors='replace')
                    except Exception as e:
                        logger.warning(f"Error decoding HTML body: {str(e)}")

        return None

    def _decode_header(self, header_value: str) -> str:
        """
        Decode email header (handles RFC 2047 encoded words).

        Args:
            header_value: Raw header value

        Returns:
            Decoded header string
        """
        if not header_value:
            return ''

        try:
            from email.header import decode_header
            decoded_parts = decode_header(header_value)
            result = ''
            for content, encoding in decoded_parts:
                if isinstance(content, bytes):
                    result += content.decode(encoding or 'utf-8', errors='replace')
                else:
                    result += content
            return result
        except Exception as e:
            logger.warning(f"Error decoding header: {str(e)}")
            return str(header_value)

    def _extract_addresses(self, address_list: List[str]) -> List[str]:
        """
        Extract email addresses from address list.

        Args:
            address_list: List of addresses (may include names)

        Returns:
            List of email addresses only
        """
        addresses = []
        if not address_list:
            return addresses

        for addr in address_list:
            if addr:
                _, email_addr = parseaddr(addr)
                if email_addr:
                    addresses.append(email_addr)

        return addresses

    def _extract_headers(self, msg: email.message.Message) -> dict:
        """
        Extract important headers from message.

        Args:
            msg: MIME message

        Returns:
            Dictionary of headers
        """
        headers = {}
        important_headers = [
            'From', 'To', 'Cc', 'Date', 'Reply-To',
            'In-Reply-To', 'References', 'X-Mailer',
            'User-Agent', 'MIME-Version', 'Content-Type'
        ]

        for header in important_headers:
            value = msg.get(header)
            if value:
                headers[header] = str(value)

        return headers

    async def decrypt_email(self, email_obj: Email) -> str:
        """
        Decrypt internal email using QKD key.

        Args:
            email_obj: Email model instance

        Returns:
            Decrypted plaintext body

        Raises:
            ValueError: If email is not internal or missing encryption data
        """
        if not email_obj.is_internal:
            raise ValueError("Email is not QKD encrypted")

        if not all([email_obj.qkd_key_id, email_obj.qkd_ciphertext,
                    email_obj.qkd_nonce, email_obj.qkd_auth_tag]):
            raise ValueError("Email missing encryption metadata")

        try:
            # Retrieve QKD key
            key_material = self.qkd_service.get_key_by_id(email_obj.qkd_key_id)

            # Decrypt
            plaintext = hybrid_decrypt(
                ciphertext=bytes.fromhex(email_obj.qkd_ciphertext),
                nonce=bytes.fromhex(email_obj.qkd_nonce),
                auth_tag=bytes.fromhex(email_obj.qkd_auth_tag),
                key_material=key_material,
                context=b'email-encryption'
            )

            return plaintext.decode('utf-8')

        except Exception as e:
            logger.error(f"Error decrypting email: {str(e)}", exc_info=True)
            raise
