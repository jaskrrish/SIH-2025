"""
High-level email services for sending and receiving emails with QKD encryption
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

from mail.models import Email, Attachment, EmailQueue, EmailLog, UserEmailSettings
from mail.parsers import MailParserWrapper
from qkd.services import QKDService
from crypto.utils import hybrid_encrypt, hybrid_decrypt
from infra.smtp_client import SMTPClient
from infra.imap_client import IMAPClient

User = get_user_model()
logger = logging.getLogger(__name__)


class EmailSendService:
    """
    High-level service for sending emails with optional QKD encryption

    Workflow:
    1. Create email record (draft)
    2. Optionally encrypt body with QKD
    3. Add to send queue
    4. Send via SMTP (handled by Celery task)
    """

    def __init__(self, user: User):
        """
        Initialize send service for a specific user

        Args:
            user: Django User object
        """
        self.user = user
        self.user_settings = UserEmailSettings.objects.get(user=user)
        self.qkd_service = QKDService()
        self.smtp_client = SMTPClient()

    def compose_email(
        self,
        to_addresses: List[str],
        subject: str,
        body_text: str = '',
        body_html: str = '',
        cc_addresses: List[str] = None,
        bcc_addresses: List[str] = None,
        attachments: List[Dict] = None,
        encrypt: bool = None,
        save_draft: bool = False
    ) -> Email:
        """
        Compose a new email and save as draft or queue for sending

        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            cc_addresses: CC recipients
            bcc_addresses: BCC recipients
            attachments: List of attachment dicts with 'filename', 'content_type', 'data'
            encrypt: Enable QKD encryption (defaults to user setting)
            save_draft: If True, save as draft instead of queueing

        Returns:
            Email object
        """
        # Default to user's encryption preference
        if encrypt is None:
            encrypt = self.user_settings.enable_qkd_encryption

        # Generate RFC822 Message-ID
        import uuid
        message_id = f"<{uuid.uuid4()}@qutemail.local>"

        # Determine initial status
        status = Email.Status.DRAFT if save_draft else Email.Status.QUEUED

        # Create email object
        email = Email.objects.create(
            user=self.user,
            message_id=message_id,
            folder=Email.Folder.DRAFTS if save_draft else Email.Folder.SENT,
            subject=subject,
            from_address=self.user_settings.email_address,
            to_addresses=to_addresses or [],
            cc_addresses=cc_addresses or [],
            bcc_addresses=bcc_addresses or [],
            body_text=body_text,
            body_html=body_html,
            status=status,
            date=timezone.now(),
            has_attachments=bool(attachments),
        )

        # Handle attachments
        if attachments:
            self._attach_files(email, attachments)

        # Log event
        EmailLog.objects.create(
            email=email,
            event_type=EmailLog.EventType.QUEUED if not save_draft else 'draft_created',
            message=f"Email {'draft created' if save_draft else 'queued for sending'}"
        )

        # If not a draft, add to queue
        if not save_draft:
            self._queue_email(email, encrypt=encrypt)

        return email

    def send_email(self, email: Email) -> bool:
        """
        Send an email via SMTP

        This is called by Celery task after dequeuing

        Args:
            email: Email object to send

        Returns:
            True if successful
        """
        try:
            # Update status
            email.status = Email.Status.SENDING
            email.save()

            EmailLog.objects.create(
                email=email,
                event_type=EmailLog.EventType.SENDING,
                message="Attempting to send email"
            )

            # Build the email message
            if email.is_encrypted:
                # Send encrypted email
                result = self._send_encrypted_email(email)
            else:
                # Send plain email
                result = self._send_plain_email(email)

            if result:
                # Mark as sent
                email.status = Email.Status.SENT
                email.sent_at = timezone.now()
                email.save()

                EmailLog.objects.create(
                    email=email,
                    event_type=EmailLog.EventType.SENT,
                    message="Email sent successfully"
                )

                return True
            else:
                # Mark as failed
                email.status = Email.Status.FAILED
                email.save()

                EmailLog.objects.create(
                    email=email,
                    event_type=EmailLog.EventType.FAILED,
                    message="Failed to send email"
                )

                return False

        except Exception as e:
            logger.exception(f"Error sending email {email.id}: {str(e)}")

            email.status = Email.Status.FAILED
            email.save()

            EmailLog.objects.create(
                email=email,
                event_type=EmailLog.EventType.FAILED,
                message=f"Exception during send: {str(e)}",
                error_message=str(e),
                traceback=str(e)
            )

            return False

    def _queue_email(self, email: Email, encrypt: bool = False, priority: int = 5):
        """
        Add email to send queue

        Args:
            email: Email object
            encrypt: Whether to encrypt with QKD
            priority: Queue priority (higher = more urgent)
        """
        # Encrypt if requested
        if encrypt:
            self._encrypt_email_body(email)

        # Create queue entry
        EmailQueue.objects.create(
            email=email,
            priority=priority,
            scheduled_at=timezone.now(),
        )

        logger.info(f"Email {email.id} queued for sending (encrypted={encrypt})")

    def _encrypt_email_body(self, email: Email):
        """
        Encrypt email body using QKD

        Args:
            email: Email object to encrypt
        """
        try:
            # Request QKD key
            qkd_data = self.qkd_service.request_key(key_size=256)
            qkd_key_bytes = bytes.fromhex(qkd_data['key_material'])

            EmailLog.objects.create(
                email=email,
                event_type=EmailLog.EventType.QKD_KEY_REQUESTED,
                message=f"QKD key requested: {qkd_data['key_id']}"
            )

            # Encrypt body text
            plaintext = email.body_text.encode('utf-8')
            encrypted = hybrid_encrypt(plaintext, qkd_key_bytes)

            # Update email with encryption metadata
            email.is_encrypted = True
            email.qkd_key_id = qkd_data['key_id']
            email.encryption_algorithm = encrypted['algorithm']
            email.encryption_nonce = encrypted['nonce']
            email.encryption_tag = encrypted['tag']

            # Replace body with encrypted content marker
            email.body_text = f"""[ENCRYPTED MESSAGE]
Key ID: {qkd_data['key_id']}
Ciphertext: {encrypted['ciphertext']}
Nonce: {encrypted['nonce']}
Tag: {encrypted['tag']}

This message is encrypted with Quantum Key Distribution (QKD).
"""
            email.subject = f"[QKD-ENCRYPTED] {email.subject}"

            email.save()

            EmailLog.objects.create(
                email=email,
                event_type=EmailLog.EventType.ENCRYPTED,
                message=f"Email encrypted with QKD key {qkd_data['key_id']}",
                metadata={
                    'qkd_key_id': qkd_data['key_id'],
                    'algorithm': encrypted['algorithm']
                }
            )

            logger.info(f"Email {email.id} encrypted with QKD key {qkd_data['key_id']}")

        except Exception as e:
            logger.exception(f"Failed to encrypt email {email.id}: {str(e)}")

            EmailLog.objects.create(
                email=email,
                event_type=EmailLog.EventType.FAILED,
                message=f"Encryption failed: {str(e)}",
                error_message=str(e)
            )

            raise

    def _send_plain_email(self, email: Email) -> bool:
        """Send plain (unencrypted) email via SMTP"""
        # Get attachments
        attachments = []
        for att in email.attachments.all():
            attachments.append({
                'filename': att.filename,
                'content_type': att.content_type,
                'data': bytes(att.data)
            })

        # Send via SMTP
        result = self.smtp_client.send_email(
            from_addr=email.from_address,
            to_addrs=email.to_addresses,
            cc_addrs=email.cc_addresses,
            bcc_addrs=email.bcc_addresses,
            subject=email.subject,
            body_text=email.body_text,
            body_html=email.body_html,
            attachments=attachments,
            username=self.user_settings.email_address,
            password=self._decrypt_smtp_password()
        )

        return result

    def _send_encrypted_email(self, email: Email) -> bool:
        """Send encrypted email via SMTP"""
        # For encrypted emails, body_text already contains the encrypted payload
        return self._send_plain_email(email)

    def _attach_files(self, email: Email, attachments: List[Dict]):
        """
        Attach files to email

        Args:
            email: Email object
            attachments: List of dicts with 'filename', 'content_type', 'data'
        """
        import hashlib

        total_size = 0

        for att_data in attachments:
            # Calculate checksum
            checksum = hashlib.sha256(att_data['data']).hexdigest()

            # Create attachment
            Attachment.objects.create(
                email=email,
                filename=att_data['filename'],
                content_type=att_data.get('content_type', 'application/octet-stream'),
                size=len(att_data['data']),
                data=att_data['data'],
                checksum=checksum,
                content_id=att_data.get('content_id'),
                is_inline=att_data.get('is_inline', False)
            )

            total_size += len(att_data['data'])

        # Update email size
        email.size = total_size
        email.save()

    def _decrypt_smtp_password(self) -> str:
        """Decrypt user's SMTP password from database"""
        # TODO: Implement actual decryption
        # For now, return a placeholder
        return settings.SMTP_PASSWORD if hasattr(settings, 'SMTP_PASSWORD') else ''


class EmailReceiveService:
    """
    High-level service for receiving emails via IMAP with QKD decryption

    Workflow:
    1. Connect to IMAP server
    2. Fetch new messages (UID-based)
    3. Parse email (headers, body, attachments)
    4. Decrypt if QKD encrypted
    5. Store in database
    """

    def __init__(self, user: User):
        """
        Initialize receive service for a specific user

        Args:
            user: Django User object
        """
        self.user = user
        self.user_settings = UserEmailSettings.objects.get(user=user)
        self.qkd_service = QKDService()
        self.imap_client = IMAPClient()

    def fetch_new_emails(self, folder: str = 'INBOX', limit: int = 50) -> List[Email]:
        """
        Fetch new emails from IMAP server

        Args:
            folder: IMAP folder to fetch from
            limit: Maximum number of emails to fetch

        Returns:
            List of Email objects created
        """
        emails_created = []

        try:
            # Fetch raw emails from IMAP
            raw_emails = self.imap_client.fetch_new_emails(
                username=self.user_settings.email_address,
                password=self._decrypt_imap_password(),
                folder=folder,
                limit=limit,
                last_uid=self._get_last_uid(folder)
            )

            for raw_email_data in raw_emails:
                email = self._process_raw_email(raw_email_data, folder)
                if email:
                    emails_created.append(email)

            # Update last sync time
            self.user_settings.last_sync_at = timezone.now()
            self.user_settings.save()

            logger.info(f"Fetched {len(emails_created)} new emails for user {self.user.id}")

        except Exception as e:
            logger.exception(f"Failed to fetch emails for user {self.user.id}: {str(e)}")

        return emails_created

    def _process_raw_email(self, raw_email_data: Dict, folder: str) -> Optional[Email]:
        """
        Process a raw email: parse, decrypt if needed, store

        Args:
            raw_email_data: Dict with 'uid', 'raw' keys
            folder: Folder name

        Returns:
            Email object or None if failed
        """
        try:
            raw_bytes = raw_email_data['raw']
            uid = raw_email_data['uid']

            # Parse email
            parser = MailParserWrapper(raw_bytes)
            parsed = parser.to_dict()

            # Check if already exists
            if Email.objects.filter(message_id=parsed['message_id']).exists():
                logger.debug(f"Email {parsed['message_id']} already exists, skipping")
                return None

            # Map folder to Email.Folder enum
            folder_mapping = {
                'INBOX': Email.Folder.INBOX,
                'Sent': Email.Folder.SENT,
                'Drafts': Email.Folder.DRAFTS,
                'Trash': Email.Folder.TRASH,
                'Spam': Email.Folder.SPAM,
            }
            email_folder = folder_mapping.get(folder, Email.Folder.INBOX)

            # Create email object
            email = Email.objects.create(
                user=self.user,
                message_id=parsed['message_id'],
                folder=email_folder,
                subject=parsed['subject'],
                from_address=parsed['from_address'],
                to_addresses=parsed['to_addresses'],
                cc_addresses=parsed['cc_addresses'],
                bcc_addresses=parsed['bcc_addresses'],
                body_text=parsed['body_text'],
                body_html=parsed['body_html'],
                raw_email=raw_bytes,
                date=parsed['date'] or timezone.now(),
                status=Email.Status.RECEIVED,
                has_attachments=parsed['has_attachments'],
                is_encrypted=parsed['is_encrypted'],
            )

            # Log receipt
            EmailLog.objects.create(
                email=email,
                event_type=EmailLog.EventType.RECEIVED,
                message=f"Email received via IMAP (UID: {uid})"
            )

            # Handle attachments
            if parsed['attachments']:
                self._store_attachments(email, parsed['attachments'])

            # Decrypt if encrypted
            if parsed['is_encrypted'] and parsed['qkd_metadata']:
                self._decrypt_email(email, parsed['qkd_metadata'])

            logger.info(f"Processed email {email.id} (Message-ID: {email.message_id})")
            return email

        except Exception as e:
            logger.exception(f"Failed to process raw email: {str(e)}")
            return None

    def _decrypt_email(self, email: Email, qkd_metadata: Dict):
        """
        Decrypt QKD-encrypted email

        Args:
            email: Email object
            qkd_metadata: Dict with qkd_key_id, ciphertext, nonce, tag
        """
        try:
            # Retrieve QKD key
            qkd_key_id = qkd_metadata['qkd_key_id']
            qkd_data = self.qkd_service.get_key_by_id(qkd_key_id)
            qkd_key_bytes = bytes.fromhex(qkd_data['key_material'])

            EmailLog.objects.create(
                email=email,
                event_type=EmailLog.EventType.QKD_KEY_RETRIEVED,
                message=f"QKD key retrieved: {qkd_key_id}"
            )

            # Decrypt
            encrypted_data = {
                'ciphertext': qkd_metadata['ciphertext'],
                'nonce': qkd_metadata['nonce'],
                'tag': qkd_metadata['tag'],
            }

            plaintext_bytes = hybrid_decrypt(encrypted_data, qkd_key_bytes)
            decrypted_text = plaintext_bytes.decode('utf-8')

            # Update email with decrypted body
            email.body_text = decrypted_text
            email.qkd_key_id = qkd_key_id
            email.encryption_nonce = qkd_metadata['nonce']
            email.encryption_tag = qkd_metadata['tag']

            # Remove [QKD-ENCRYPTED] prefix from subject
            if email.subject.startswith('[QKD-ENCRYPTED]'):
                email.subject = email.subject.replace('[QKD-ENCRYPTED]', '').strip()

            email.save()

            EmailLog.objects.create(
                email=email,
                event_type=EmailLog.EventType.DECRYPTED,
                message=f"Email decrypted successfully with key {qkd_key_id}",
                metadata={'qkd_key_id': qkd_key_id}
            )

            # Confirm key usage
            self.qkd_service.confirm_key(qkd_key_id)

            logger.info(f"Email {email.id} decrypted with QKD key {qkd_key_id}")

        except Exception as e:
            logger.exception(f"Failed to decrypt email {email.id}: {str(e)}")

            EmailLog.objects.create(
                email=email,
                event_type=EmailLog.EventType.DECRYPTION_FAILED,
                message=f"Decryption failed: {str(e)}",
                error_message=str(e)
            )

    def _store_attachments(self, email: Email, attachments: List[Dict]):
        """
        Store email attachments

        Args:
            email: Email object
            attachments: List of attachment dicts
        """
        for att_data in attachments:
            Attachment.objects.create(
                email=email,
                filename=att_data['filename'],
                content_type=att_data['content_type'],
                size=att_data['size'],
                data=att_data['data'],
                checksum=att_data['checksum'],
                content_id=att_data.get('content_id'),
                is_inline=att_data.get('is_inline', False)
            )

    def _get_last_uid(self, folder: str) -> Optional[int]:
        """Get last processed UID for incremental fetching"""
        # Query last email from this folder
        last_email = Email.objects.filter(
            user=self.user,
            folder=folder
        ).order_by('-created_at').first()

        # TODO: Store UID in email metadata
        return None

    def _decrypt_imap_password(self) -> str:
        """Decrypt user's IMAP password from database"""
        # TODO: Implement actual decryption
        return settings.IMAP_PASSWORD if hasattr(settings, 'IMAP_PASSWORD') else ''
