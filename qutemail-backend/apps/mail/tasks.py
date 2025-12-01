"""
Celery tasks for asynchronous email processing with queue management
"""
import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction

from mail.models import Email, EmailQueue, EmailLog, UserEmailSettings
from mail.services import EmailSendService, EmailReceiveService

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def process_email_queue(self):
    """
    Process the email queue and send pending emails

    This task is run periodically to dequeue and send emails.
    Implements retry logic with exponential backoff.

    Returns:
        Dict with processing statistics
    """
    logger.info("Starting email queue processing")

    stats = {
        'processed': 0,
        'sent': 0,
        'failed': 0,
        'locked': 0
    }

    try:
        # Get unlocked queue entries ready to send
        now = timezone.now()
        queue_entries = EmailQueue.objects.filter(
            is_locked=False,
            scheduled_at__lte=now
        ).select_related('email', 'email__user').order_by('-priority', 'scheduled_at')[:10]

        for queue_entry in queue_entries:
            try:
                # Lock the entry
                with transaction.atomic():
                    # Re-fetch with select_for_update to prevent race conditions
                    locked_entry = EmailQueue.objects.select_for_update(
                        nowait=True
                    ).get(id=queue_entry.id, is_locked=False)

                    locked_entry.lock(worker_id=self.request.id)
                    stats['locked'] += 1

                # Send the email
                result = send_single_email.delay(queue_entry.email.id, queue_entry.id)

                stats['processed'] += 1

            except EmailQueue.DoesNotExist:
                # Entry was locked by another worker
                logger.debug(f"Queue entry {queue_entry.id} already locked")
                continue
            except Exception as e:
                logger.exception(f"Error processing queue entry {queue_entry.id}: {str(e)}")
                stats['failed'] += 1
                continue

        logger.info(f"Queue processing complete: {stats}")
        return stats

    except Exception as e:
        logger.exception(f"Fatal error in process_email_queue: {str(e)}")
        raise


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=120,
    autoretry_for=(Exception,)
)
def send_single_email(self, email_id: int, queue_id: int):
    """
    Send a single email from the queue

    Args:
        email_id: Email model ID
        queue_id: EmailQueue entry ID

    Returns:
        Dict with send result
    """
    try:
        # Get email and queue entry
        email = Email.objects.select_related('user').get(id=email_id)
        queue_entry = EmailQueue.objects.get(id=queue_id)

        logger.info(f"Sending email {email_id} (attempt {queue_entry.attempts + 1}/{queue_entry.max_attempts})")

        # Increment attempts
        queue_entry.attempts += 1
        queue_entry.save()

        # Send email using service
        send_service = EmailSendService(email.user)
        success = send_service.send_email(email)

        if success:
            # Delete from queue on success
            queue_entry.delete()

            logger.info(f"Email {email_id} sent successfully")

            return {
                'success': True,
                'email_id': email_id,
                'message': 'Email sent successfully'
            }
        else:
            # Handle failure
            if queue_entry.attempts >= queue_entry.max_attempts:
                # Max retries exceeded, mark as failed
                email.status = Email.Status.FAILED
                email.save()

                queue_entry.unlock()
                queue_entry.save()

                EmailLog.objects.create(
                    email=email,
                    event_type=EmailLog.EventType.FAILED,
                    message=f"Max retry attempts ({queue_entry.max_attempts}) exceeded",
                    error_message="Failed to send after maximum retries"
                )

                logger.error(f"Email {email_id} failed after {queue_entry.attempts} attempts")

                return {
                    'success': False,
                    'email_id': email_id,
                    'message': 'Max retries exceeded'
                }
            else:
                # Schedule retry with exponential backoff
                retry_delay = min(120 * (2 ** queue_entry.attempts), 3600)  # Max 1 hour
                queue_entry.next_retry_at = timezone.now() + timedelta(seconds=retry_delay)
                queue_entry.scheduled_at = queue_entry.next_retry_at
                queue_entry.unlock()
                queue_entry.save()

                EmailLog.objects.create(
                    email=email,
                    event_type=EmailLog.EventType.RETRY,
                    message=f"Retrying in {retry_delay} seconds (attempt {queue_entry.attempts}/{queue_entry.max_attempts})"
                )

                logger.warning(f"Email {email_id} send failed, will retry in {retry_delay}s")

                return {
                    'success': False,
                    'email_id': email_id,
                    'message': f'Will retry in {retry_delay}s',
                    'retry_at': queue_entry.next_retry_at
                }

    except Email.DoesNotExist:
        logger.error(f"Email {email_id} not found")
        return {'success': False, 'error': 'Email not found'}

    except EmailQueue.DoesNotExist:
        logger.error(f"Queue entry {queue_id} not found")
        return {'success': False, 'error': 'Queue entry not found'}

    except Exception as e:
        logger.exception(f"Error sending email {email_id}: {str(e)}")

        # Unlock queue entry on exception
        try:
            queue_entry = EmailQueue.objects.get(id=queue_id)
            queue_entry.unlock()
            queue_entry.save()
        except:
            pass

        raise


@shared_task
def fetch_incoming_emails():
    """
    Periodic task to fetch incoming emails for all users via IMAP

    This task is scheduled by Celery Beat (e.g., every 60 seconds)

    Returns:
        Dict with fetch statistics
    """
    logger.info("Starting periodic email fetch")

    stats = {
        'users_processed': 0,
        'emails_fetched': 0,
        'errors': 0
    }

    try:
        # Get all user email settings
        user_settings = UserEmailSettings.objects.select_related('user').filter(
            auto_fetch_interval__gt=0  # Only users with auto-fetch enabled
        )

        for settings in user_settings:
            try:
                # Check if enough time has passed since last sync
                if settings.last_sync_at:
                    next_sync = settings.last_sync_at + timedelta(seconds=settings.auto_fetch_interval)
                    if timezone.now() < next_sync:
                        logger.debug(f"Skipping user {settings.user.id} - not time for sync yet")
                        continue

                # Fetch emails for this user
                receive_service = EmailReceiveService(settings.user)
                emails = receive_service.fetch_new_emails(folder='INBOX', limit=50)

                stats['users_processed'] += 1
                stats['emails_fetched'] += len(emails)

                logger.info(f"Fetched {len(emails)} emails for user {settings.user.id}")

            except Exception as e:
                logger.exception(f"Error fetching emails for user {settings.user.id}: {str(e)}")
                stats['errors'] += 1
                continue

        logger.info(f"Email fetch complete: {stats}")
        return stats

    except Exception as e:
        logger.exception(f"Fatal error in fetch_incoming_emails: {str(e)}")
        raise


@shared_task
def fetch_user_emails(user_id: int, folder: str = 'INBOX'):
    """
    Fetch emails for a specific user

    Args:
        user_id: User ID
        folder: IMAP folder to fetch from

    Returns:
        Dict with fetch result
    """
    try:
        user = User.objects.get(id=user_id)

        logger.info(f"Fetching emails for user {user_id} from {folder}")

        receive_service = EmailReceiveService(user)
        emails = receive_service.fetch_new_emails(folder=folder, limit=100)

        return {
            'success': True,
            'user_id': user_id,
            'emails_fetched': len(emails),
            'folder': folder
        }

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'success': False, 'error': 'User not found'}

    except Exception as e:
        logger.exception(f"Error fetching emails for user {user_id}: {str(e)}")
        return {
            'success': False,
            'user_id': user_id,
            'error': str(e)
        }


@shared_task
def cleanup_old_logs(days: int = 90):
    """
    Clean up old email logs to prevent database bloat

    Args:
        days: Delete logs older than this many days (default: 90)

    Returns:
        Dict with cleanup statistics
    """
    logger.info(f"Starting email log cleanup (older than {days} days)")

    try:
        cutoff_date = timezone.now() - timedelta(days=days)

        # Delete old logs
        deleted_count, _ = EmailLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()

        logger.info(f"Deleted {deleted_count} old email logs")

        return {
            'success': True,
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date
        }

    except Exception as e:
        logger.exception(f"Error cleaning up logs: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def cleanup_old_queue_entries(hours: int = 24):
    """
    Clean up stale locked queue entries

    If a worker crashes, queue entries may remain locked. This task
    unlocks entries that have been locked for too long.

    Args:
        hours: Unlock entries locked for more than this many hours

    Returns:
        Dict with cleanup statistics
    """
    logger.info(f"Starting queue cleanup (locked for >{hours} hours)")

    try:
        cutoff_time = timezone.now() - timedelta(hours=hours)

        # Find stale locked entries
        stale_entries = EmailQueue.objects.filter(
            is_locked=True,
            locked_at__lt=cutoff_time
        )

        count = 0
        for entry in stale_entries:
            entry.unlock()
            entry.save()
            count += 1

            logger.warning(f"Unlocked stale queue entry {entry.id} (locked by {entry.locked_by})")

        logger.info(f"Unlocked {count} stale queue entries")

        return {
            'success': True,
            'unlocked_count': count
        }

    except Exception as e:
        logger.exception(f"Error cleaning up queue: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
