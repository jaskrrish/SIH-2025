"""
Celery tasks for asynchronous email processing
"""
import asyncio
import smtplib
import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone

from qkd.services import QKDService
from crypto.utils import hybrid_encrypt, hybrid_decrypt
from infra.smtp_client import SMTPClient
from infra.imap_client import IMAPClient
from mail.models import EmailDeliveryStatus

logger = logging.getLogger('celery_tasks')


@shared_task
def send_encrypted_email(from_addr, to_addrs, subject, body, username=None, password=None):
    """
    Asynchronously send an encrypted email
    
    Args:
        from_addr: Sender email
        to_addrs: List of recipients
        subject: Email subject
        body: Email body
        username: SMTP username
        password: SMTP password
    """
    try:
        # Request QKD key
        qkd_service = QKDService()
        key_data = qkd_service.request_key(key_size=256)
        qkd_key = bytes.fromhex(key_data['key_material'])
        
        # Encrypt body
        encrypted_data = hybrid_encrypt(body.encode(), qkd_key)
        
        # Prepare encrypted email body
        encrypted_body = f"[ENCRYPTED MESSAGE]\nKey ID: {key_data['key_id']}\nCiphertext: {encrypted_data['ciphertext']}\nNonce: {encrypted_data['nonce']}\nTag: {encrypted_data['tag']}"
        
        # Send email
        smtp_client = SMTPClient()
        success = smtp_client.send_email(
            from_addr=from_addr,
            to_addrs=to_addrs,
            subject=f"[QKD-ENCRYPTED] {subject}",
            body=encrypted_body,
            username=username,
            password=password
        )
        
        return {
            'success': success,
            'key_id': key_data['key_id'],
            'message': 'Email sent successfully' if success else 'Failed to send email'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def fetch_and_decrypt_emails(username, password, folder='INBOX', limit=10):
    """
    Asynchronously fetch and decrypt emails
    
    Args:
        username: IMAP username
        password: IMAP password
        folder: Mailbox folder
        limit: Max emails to fetch
    """
    try:
        imap_client = IMAPClient()
        emails = imap_client.fetch_emails(username, password, folder, limit)
        
        qkd_service = QKDService()
        decrypted_emails = []
        
        for email_data in emails:
            # Check if email is encrypted
            if '[QKD-ENCRYPTED]' in email_data.get('subject', ''):
                try:
                    # Parse encrypted data from body
                    body = email_data['body']
                    
                    # Extract key_id, ciphertext, nonce, tag
                    lines = body.split('\n')
                    key_id = lines[1].split(': ')[1]
                    ciphertext = lines[2].split(': ')[1]
                    nonce = lines[3].split(': ')[1]
                    tag = lines[4].split(': ')[1]
                    
                    # Get QKD key
                    key_data = qkd_service.get_key_by_id(key_id)
                    qkd_key = bytes.fromhex(key_data['key_material'])
                    
                    # Decrypt
                    encrypted_data = {
                        'ciphertext': ciphertext,
                        'nonce': nonce,
                        'tag': tag
                    }
                    
                    plaintext = hybrid_decrypt(encrypted_data, qkd_key)
                    email_data['decrypted_body'] = plaintext.decode()
                    email_data['encrypted'] = True
                    
                except Exception as e:
                    email_data['decryption_error'] = str(e)
                    email_data['encrypted'] = True
            else:
                email_data['encrypted'] = False
            
            decrypted_emails.append(email_data)
        
        return {
            'success': True,
            'emails': decrypted_emails
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def process_incoming_mail():
    """
    Periodic task to process incoming mail
    Can be scheduled with Celery Beat
    """
    # TODO: Implement periodic mail processing
    pass


# ============================================================================
# New SMTP Server Tasks
# ============================================================================

@shared_task(bind=True, max_retries=3)
def process_smtp_email(self, envelope_data):
    """
    Process incoming SMTP email asynchronously.

    This task is queued by SMTP handlers when emails are received.
    It processes the email through EmailProcessingService which handles:
    - Internal emails: QKD encryption and storage
    - External emails: Storage or delivery

    Args:
        envelope_data: Dict with mail_from, rcpt_tos, content, peer

    Returns:
        Dict with success status and message
    """
    try:
        from mail.services import EmailProcessingService

        logger.info(
            f"Processing SMTP email from {envelope_data['mail_from']} "
            f"to {envelope_data['rcpt_tos']}"
        )

        # Create service instance
        service = EmailProcessingService()

        # Process email (run async function in sync context)
        success = asyncio.run(service.process_incoming_email(envelope_data))

        if success:
            logger.info("Email processed successfully")
            return {'success': True, 'message': 'Email processed'}
        else:
            logger.warning("Email processing returned False")
            return {'success': False, 'message': 'Processing failed'}

    except Exception as exc:
        logger.error(f"Error in process_smtp_email task: {str(exc)}", exc_info=True)

        # Retry with exponential backoff
        retry_countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=retry_countdown)


@shared_task(bind=True, max_retries=5)
def deliver_external_email(self, from_addr, to_addr, message_bytes):
    """
    Deliver email to external SMTP server with retry logic.

    This task handles outbound email delivery to external recipients.
    It creates/updates EmailDeliveryStatus records and implements
    exponential backoff retry on failures.

    Args:
        from_addr: Sender email address
        to_addr: Recipient email address
        message_bytes: Raw email message as bytes

    Returns:
        Dict with delivery status
    """
    from django.conf import settings

    delivery = None

    try:
        logger.info(f"Delivering email from {from_addr} to {to_addr}")

        # Create or update delivery status record
        delivery = EmailDeliveryStatus.objects.create(
            recipient=to_addr,
            status='pending',
            attempts=self.request.retries + 1
        )

        # Initialize SMTP client
        smtp_client = SMTPClient(
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            use_tls=settings.SMTP_USE_TLS
        )

        # Attempt delivery
        # Note: Assuming SMTPClient has a send_raw method
        # If not, we'll need to add it or use smtplib directly
        try:
            smtp_client.connect()
            smtp_client.smtp.sendmail(from_addr, [to_addr], message_bytes)
            smtp_client.disconnect()

            # Mark as sent
            delivery.mark_as_sent()
            logger.info(f"Email delivered successfully to {to_addr}")

            return {'success': True, 'recipient': to_addr}

        except smtplib.SMTPException as smtp_exc:
            smtp_response = str(smtp_exc)
            logger.warning(f"SMTP error delivering to {to_addr}: {smtp_response}")

            # Update delivery status
            delivery.mark_as_failed(
                error_msg=str(smtp_exc),
                smtp_response=smtp_response
            )

            # Retry with exponential backoff (5, 10, 20, 40, 80 minutes)
            retry_delay = 300 * (2 ** self.request.retries)  # 5 minutes * 2^retries
            delivery.schedule_retry(delay_minutes=retry_delay // 60)

            raise self.retry(exc=smtp_exc, countdown=retry_delay)

    except Exception as exc:
        logger.error(f"Error in deliver_external_email task: {str(exc)}", exc_info=True)

        if delivery:
            delivery.mark_as_failed(error_msg=str(exc))

        # Don't retry on non-SMTP exceptions
        return {'success': False, 'error': str(exc)}


@shared_task
def cleanup_old_emails():
    """
    Periodic cleanup of old emails based on retention policy.

    This task should be scheduled with Celery Beat to run periodically
    (e.g., daily or weekly). It deletes emails older than the configured
    retention period.

    Returns:
        Dict with number of emails deleted
    """
    from django.conf import settings
    from mail.models import Email

    try:
        retention_days = getattr(settings, 'EMAIL_RETENTION_DAYS', 365)
        cutoff_date = timezone.now() - timedelta(days=retention_days)

        logger.info(f"Starting email cleanup (retention: {retention_days} days)")

        # Delete old emails
        deleted_count, _ = Email.objects.filter(
            received_at__lt=cutoff_date
        ).delete()

        logger.info(f"Deleted {deleted_count} old emails")

        return {'success': True, 'deleted_count': deleted_count}

    except Exception as e:
        logger.error(f"Error in cleanup_old_emails task: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}


@shared_task
def retry_failed_deliveries():
    """
    Retry failed email deliveries that are due for retry.

    This task finds EmailDeliveryStatus records with status 'deferred'
    and next_retry_at <= now, then attempts redelivery.

    Returns:
        Dict with number of retries attempted
    """
    from mail.models import EmailDeliveryStatus, Email

    try:
        # Find deliveries due for retry
        due_retries = EmailDeliveryStatus.objects.filter(
            status='deferred',
            next_retry_at__lte=timezone.now()
        )

        retry_count = 0

        for delivery in due_retries:
            if delivery.email:
                logger.info(f"Retrying delivery to {delivery.recipient}")

                # Get email content
                msg_bytes = delivery.email.as_bytes() if hasattr(delivery.email, 'as_bytes') else b''

                # Queue for delivery
                deliver_external_email.delay(
                    from_addr=delivery.email.from_address,
                    to_addr=delivery.recipient,
                    message_bytes=msg_bytes
                )

                retry_count += 1

        logger.info(f"Queued {retry_count} deliveries for retry")

        return {'success': True, 'retry_count': retry_count}

    except Exception as e:
        logger.error(f"Error in retry_failed_deliveries task: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}
