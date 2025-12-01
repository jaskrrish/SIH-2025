from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class Email(models.Model):
    """Core email message model with PostgreSQL storage"""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        QUEUED = 'queued', 'Queued'
        SENDING = 'sending', 'Sending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'
        RECEIVED = 'received', 'Received'

    class Folder(models.TextChoices):
        INBOX = 'inbox', 'Inbox'
        SENT = 'sent', 'Sent'
        DRAFTS = 'drafts', 'Drafts'
        TRASH = 'trash', 'Trash'
        SPAM = 'spam', 'Spam'
        ARCHIVE = 'archive', 'Archive'

    # Ownership and routing
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='emails',
        db_index=True
    )
    folder = models.CharField(
        max_length=20,
        choices=Folder.choices,
        default=Folder.INBOX,
        db_index=True
    )

    # Email headers
    message_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Unique RFC822 Message-ID"
    )
    in_reply_to = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Message-ID of email being replied to"
    )
    references = models.TextField(
        null=True,
        blank=True,
        help_text="Space-separated list of Message-IDs in thread"
    )

    subject = models.CharField(max_length=998)  # RFC 2822 limit
    from_address = models.EmailField()
    to_addresses = models.JSONField(
        default=list,
        help_text="List of recipient email addresses"
    )
    cc_addresses = models.JSONField(
        default=list,
        blank=True,
        help_text="List of CC email addresses"
    )
    bcc_addresses = models.JSONField(
        default=list,
        blank=True,
        help_text="List of BCC email addresses"
    )

    # Content stored in PostgreSQL
    body_text = models.TextField(
        blank=True,
        help_text="Plain text body"
    )
    body_html = models.TextField(
        blank=True,
        help_text="HTML body"
    )
    raw_email = models.BinaryField(
        null=True,
        blank=True,
        help_text="Complete RFC822 message (binary)"
    )

    # QKD Encryption metadata
    is_encrypted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether email is QKD encrypted"
    )
    qkd_key_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text="QKD key ID for encryption/decryption"
    )
    encryption_algorithm = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        default='AES-256-GCM',
        help_text="Encryption algorithm used"
    )
    encryption_nonce = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text="Hex-encoded encryption nonce"
    )
    encryption_tag = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text="Hex-encoded authentication tag"
    )

    # Status and tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )

    # Flags
    is_read = models.BooleanField(default=False, db_index=True)
    is_starred = models.BooleanField(default=False, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    has_attachments = models.BooleanField(default=False, db_index=True)

    # Timestamps
    date = models.DateTimeField(
        default=timezone.now,
        help_text="Original email date from headers"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    # Size in bytes
    size = models.IntegerField(
        default=0,
        help_text="Total size of email including attachments in bytes"
    )

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['user', 'folder', '-date']),
            models.Index(fields=['user', 'is_read', '-date']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['qkd_key_id']),
            models.Index(fields=['user', 'is_deleted']),
        ]
        verbose_name = 'Email'
        verbose_name_plural = 'Emails'

    def __str__(self):
        return f"{self.subject[:50]} - {self.from_address}"

    def mark_as_read(self):
        """Mark email as read"""
        self.is_read = True
        self.save(update_fields=['is_read', 'updated_at'])

    def mark_as_unread(self):
        """Mark email as unread"""
        self.is_read = False
        self.save(update_fields=['is_read', 'updated_at'])

    def toggle_star(self):
        """Toggle starred status"""
        self.is_starred = not self.is_starred
        self.save(update_fields=['is_starred', 'updated_at'])

    def move_to_folder(self, folder):
        """Move email to a different folder"""
        if folder in dict(self.Folder.choices):
            self.folder = folder
            self.save(update_fields=['folder', 'updated_at'])

    def soft_delete(self):
        """Move to trash (soft delete)"""
        self.is_deleted = True
        self.folder = self.Folder.TRASH
        self.save(update_fields=['is_deleted', 'folder', 'updated_at'])


class Attachment(models.Model):
    """Email attachment model with PostgreSQL binary storage"""

    email = models.ForeignKey(
        Email,
        on_delete=models.CASCADE,
        related_name='attachments'
    )

    # File information
    filename = models.CharField(max_length=255)
    content_type = models.CharField(
        max_length=100,
        help_text="MIME content type"
    )
    size = models.IntegerField(
        help_text="Size in bytes"
    )

    # Store binary data directly in PostgreSQL
    data = models.BinaryField(
        help_text="Binary attachment data stored in PostgreSQL"
    )
    checksum = models.CharField(
        max_length=64,
        help_text="SHA-256 checksum for integrity verification"
    )

    # Metadata
    content_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Content-ID for inline images"
    )
    is_inline = models.BooleanField(
        default=False,
        help_text="Whether attachment is inline (e.g., embedded image)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['filename']
        indexes = [
            models.Index(fields=['email', 'is_inline']),
        ]
        verbose_name = 'Attachment'
        verbose_name_plural = 'Attachments'

    def __str__(self):
        return f"{self.filename} ({self.size} bytes)"

    def get_size_display(self):
        """Return human-readable file size"""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class EmailQueue(models.Model):
    """Outbound email queue for reliable delivery with retry logic"""

    class Priority(models.IntegerChoices):
        LOW = 1, 'Low'
        NORMAL = 5, 'Normal'
        HIGH = 10, 'High'
        URGENT = 15, 'Urgent'

    email = models.ForeignKey(
        Email,
        on_delete=models.CASCADE,
        related_name='queue_entries'
    )

    # Queue management
    priority = models.IntegerField(
        choices=Priority.choices,
        default=Priority.NORMAL,
        db_index=True,
        help_text="Higher priority emails are processed first"
    )
    attempts = models.IntegerField(
        default=0,
        help_text="Number of send attempts made"
    )
    max_attempts = models.IntegerField(
        default=5,
        help_text="Maximum number of send attempts before giving up"
    )

    # Scheduling
    scheduled_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When to send this email"
    )
    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When to retry after a failed attempt"
    )

    # Locking mechanism to prevent duplicate processing
    is_locked = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this queue entry is currently being processed"
    )
    locked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the queue entry was locked"
    )
    locked_by = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Celery worker ID that locked this entry"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'scheduled_at']
        indexes = [
            models.Index(fields=['scheduled_at', 'is_locked']),
            models.Index(fields=['-priority', 'scheduled_at']),
            models.Index(fields=['is_locked', 'scheduled_at']),
        ]
        verbose_name = 'Email Queue Entry'
        verbose_name_plural = 'Email Queue Entries'

    def __str__(self):
        return f"Queue entry for: {self.email.subject[:50]}"

    def lock(self, worker_id):
        """Lock this queue entry for processing"""
        self.is_locked = True
        self.locked_at = timezone.now()
        self.locked_by = worker_id
        self.save(update_fields=['is_locked', 'locked_at', 'locked_by', 'updated_at'])

    def unlock(self):
        """Unlock this queue entry"""
        self.is_locked = False
        self.locked_at = None
        self.locked_by = None
        self.save(update_fields=['is_locked', 'locked_at', 'locked_by', 'updated_at'])

    def increment_attempts(self):
        """Increment the attempt counter"""
        self.attempts += 1
        self.save(update_fields=['attempts', 'updated_at'])


class EmailLog(models.Model):
    """Detailed logging for email operations and events"""

    class EventType(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        SENDING = 'sending', 'Sending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'
        RETRY = 'retry', 'Retry'
        BOUNCED = 'bounced', 'Bounced'
        RECEIVED = 'received', 'Received'
        PARSED = 'parsed', 'Parsed'
        ENCRYPTED = 'encrypted', 'Encrypted'
        DECRYPTED = 'decrypted', 'Decrypted'
        DECRYPTION_FAILED = 'decryption_failed', 'Decryption Failed'
        QKD_KEY_REQUESTED = 'qkd_key_requested', 'QKD Key Requested'
        QKD_KEY_RETRIEVED = 'qkd_key_retrieved', 'QKD Key Retrieved'

    email = models.ForeignKey(
        Email,
        on_delete=models.CASCADE,
        related_name='logs'
    )

    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices,
        db_index=True
    )
    message = models.TextField(
        help_text="Human-readable log message"
    )

    # Additional context as JSON
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional event metadata"
    )

    # Error tracking
    error_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Error code if applicable"
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Detailed error message"
    )
    traceback = models.TextField(
        null=True,
        blank=True,
        help_text="Python traceback for debugging"
    )

    # Timestamp
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', '-created_at']),
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'

    def __str__(self):
        return f"{self.event_type} - {self.email.subject[:50]} @ {self.created_at}"


class UserEmailSettings(models.Model):
    """User-specific email settings and mailbox configuration"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='email_settings',
        primary_key=True
    )

    # Email identity
    email_address = models.EmailField(
        unique=True,
        help_text="User's email address (username@qutemail.local)"
    )
    display_name = models.CharField(
        max_length=255,
        help_text="Display name for outgoing emails"
    )
    signature = models.TextField(
        blank=True,
        help_text="Email signature appended to outgoing emails"
    )

    # Encrypted mailbox credentials (stored as binary)
    smtp_password_encrypted = models.BinaryField(
        default=bytes,
        blank=True,
        help_text="Encrypted SMTP password"
    )
    imap_password_encrypted = models.BinaryField(
        default=bytes,
        blank=True,
        help_text="Encrypted IMAP password"
    )

    # Preferences
    auto_fetch_interval = models.IntegerField(
        default=60,
        help_text="IMAP auto-fetch interval in seconds (0 to disable)"
    )
    enable_qkd_encryption = models.BooleanField(
        default=True,
        help_text="Enable QKD encryption for outgoing emails by default"
    )

    # Quota and limits
    storage_quota_mb = models.IntegerField(
        default=1024,
        help_text="Storage quota in megabytes (0 for unlimited)"
    )
    storage_used_bytes = models.BigIntegerField(
        default=0,
        help_text="Current storage usage in bytes"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time emails were synced from IMAP"
    )

    class Meta:
        verbose_name = 'User Email Settings'
        verbose_name_plural = 'User Email Settings'

    def __str__(self):
        return f"{self.user.username} - {self.email_address}"

    def get_storage_usage_percentage(self):
        """Calculate storage usage as percentage of quota"""
        if self.storage_quota_mb == 0:  # Unlimited
            return 0
        quota_bytes = self.storage_quota_mb * 1024 * 1024
        return (self.storage_used_bytes / quota_bytes) * 100 if quota_bytes > 0 else 0

    def is_quota_exceeded(self):
        """Check if storage quota is exceeded"""
        if self.storage_quota_mb == 0:  # Unlimited
            return False
        quota_bytes = self.storage_quota_mb * 1024 * 1024
        return self.storage_used_bytes >= quota_bytes

    def update_storage_usage(self):
        """Recalculate storage usage from emails and attachments"""
        total_size = 0

        # Sum email sizes
        emails = Email.objects.filter(user=self.user, is_deleted=False)
        total_size += sum(email.size for email in emails)

        # Sum attachment sizes
        attachments = Attachment.objects.filter(email__user=self.user, email__is_deleted=False)
        total_size += sum(att.size for att in attachments)

        self.storage_used_bytes = total_size
        self.save(update_fields=['storage_used_bytes', 'updated_at'])

        return total_size


class Label(models.Model):
    """Custom labels/tags for email organization"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_labels'
    )
    name = models.CharField(max_length=100)
    color = models.CharField(
        max_length=7,
        default='#3B82F6',
        help_text="Hex color code (e.g., #3B82F6)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['user', 'name']]
        ordering = ['name']
        verbose_name = 'Label'
        verbose_name_plural = 'Labels'

    def __str__(self):
        return f"{self.user.username} - {self.name}"

    def get_email_count(self):
        """Get number of emails with this label"""
        return self.email_labels.count()


class EmailLabel(models.Model):
    """Many-to-many relationship between emails and labels"""

    email = models.ForeignKey(
        Email,
        on_delete=models.CASCADE,
        related_name='email_labels'
    )
    label = models.ForeignKey(
        Label,
        on_delete=models.CASCADE,
        related_name='email_labels'
    )

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['email', 'label']]
        indexes = [
            models.Index(fields=['email', 'label']),
            models.Index(fields=['label', 'created_at']),
        ]
        verbose_name = 'Email Label'
        verbose_name_plural = 'Email Labels'

    def __str__(self):
        return f"{self.email.subject[:30]} - {self.label.name}"
