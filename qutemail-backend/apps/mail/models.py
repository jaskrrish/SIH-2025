from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Index


class Mailbox(models.Model):
    """
    Mailbox for each Django user.
    One-to-one relationship: each user has one mailbox.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='mailbox'
    )
    email_address = models.EmailField(
        unique=True,
        help_text="Email address in format username@yourdomain.com"
    )
    quota_bytes = models.BigIntegerField(
        default=5 * 1024 * 1024 * 1024,  # 5GB default
        help_text="Mailbox storage quota in bytes"
    )
    used_bytes = models.BigIntegerField(
        default=0,
        help_text="Current storage usage in bytes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mail_mailbox'
        verbose_name = 'Mailbox'
        verbose_name_plural = 'Mailboxes'

    def __str__(self):
        return self.email_address

    @property
    def quota_percentage(self):
        """Calculate percentage of quota used"""
        if self.quota_bytes == 0:
            return 0
        return (self.used_bytes / self.quota_bytes) * 100

    def has_quota_available(self, size_bytes):
        """Check if adding size_bytes would exceed quota"""
        return (self.used_bytes + size_bytes) <= self.quota_bytes


class Email(models.Model):
    """
    Email message with QKD encryption support for internal emails.
    """
    FOLDER_CHOICES = [
        ('INBOX', 'Inbox'),
        ('SENT', 'Sent'),
        ('DRAFTS', 'Drafts'),
        ('TRASH', 'Trash'),
        ('SPAM', 'Spam'),
        ('ARCHIVE', 'Archive'),
    ]

    mailbox = models.ForeignKey(
        Mailbox,
        on_delete=models.CASCADE,
        related_name='emails'
    )
    message_id = models.CharField(
        max_length=998,
        unique=True,
        help_text="RFC 5322 Message-ID header"
    )
    from_address = models.EmailField(max_length=254)
    to_addresses = models.JSONField(
        default=list,
        help_text="Array of recipient email addresses"
    )
    cc_addresses = models.JSONField(
        default=list,
        help_text="Array of CC email addresses"
    )
    bcc_addresses = models.JSONField(
        default=list,
        help_text="Array of BCC email addresses"
    )
    subject = models.CharField(max_length=998, blank=True)

    # Body content
    body_plain = models.TextField(
        blank=True,
        help_text="Plain text body (empty if QKD encrypted)"
    )
    body_html = models.TextField(
        blank=True, null=True,
        help_text="HTML body (optional)"
    )

    # QKD Encryption Fields (for internal emails only)
    is_internal = models.BooleanField(
        default=False,
        help_text="True if QKD encrypted (both parties @yourdomain.com)"
    )
    qkd_key_id = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="QKD key identifier for decryption"
    )
    qkd_ciphertext = models.TextField(
        blank=True, null=True,
        help_text="Hex-encoded encrypted body"
    )
    qkd_nonce = models.CharField(
        max_length=64, blank=True, null=True,
        help_text="Hex-encoded AES-GCM nonce"
    )
    qkd_auth_tag = models.CharField(
        max_length=64, blank=True, null=True,
        help_text="Hex-encoded AES-GCM authentication tag"
    )

    # Optional at-rest encryption for external emails
    encrypted_body = models.BinaryField(
        blank=True, null=True,
        help_text="Optional encrypted storage for external emails"
    )

    # Metadata
    size_bytes = models.IntegerField(
        default=0,
        help_text="Total email size in bytes"
    )
    is_read = models.BooleanField(default=False)
    is_flagged = models.BooleanField(default=False)
    folder = models.CharField(
        max_length=20,
        choices=FOLDER_CHOICES,
        default='INBOX'
    )

    # Email headers (stored as JSON)
    headers = models.JSONField(
        default=dict,
        help_text="Additional email headers as key-value pairs"
    )

    # Timestamps
    received_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'mail_email'
        verbose_name = 'Email'
        verbose_name_plural = 'Emails'
        ordering = ['-received_at']
        indexes = [
            Index(fields=['mailbox', 'received_at']),
            Index(fields=['message_id']),
            Index(fields=['is_internal']),
            Index(fields=['folder']),
            Index(fields=['is_read']),
        ]

    def __str__(self):
        return f"{self.subject[:50]} - {self.from_address}"

    def save(self, *args, **kwargs):
        """Update mailbox quota when saving email"""
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            # Update mailbox used_bytes
            self.mailbox.used_bytes += self.size_bytes
            self.mailbox.save()

    def delete(self, *args, **kwargs):
        """Update mailbox quota when deleting email"""
        # Update mailbox used_bytes
        self.mailbox.used_bytes -= self.size_bytes
        self.mailbox.save()
        super().delete(*args, **kwargs)


class EmailAttachment(models.Model):
    """
    Email attachments stored separately for efficient handling.
    """
    email = models.ForeignKey(
        Email,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    filename = models.CharField(max_length=255)
    content_type = models.CharField(
        max_length=100,
        help_text="MIME type (e.g., image/png, application/pdf)"
    )
    size_bytes = models.IntegerField(help_text="Attachment size in bytes")
    storage_path = models.CharField(
        max_length=500,
        help_text="Path to file in storage backend"
    )
    is_inline = models.BooleanField(
        default=False,
        help_text="True if inline image (embedded in HTML body)"
    )
    content_id = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Content-ID for inline images"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mail_email_attachment'
        verbose_name = 'Email Attachment'
        verbose_name_plural = 'Email Attachments'

    def __str__(self):
        return f"{self.filename} ({self.content_type})"


class EmailDeliveryStatus(models.Model):
    """
    Track delivery status for outbound emails (especially external ones).
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
        ('deferred', 'Deferred'),
    ]

    email = models.ForeignKey(
        Email,
        on_delete=models.CASCADE,
        related_name='delivery_statuses',
        blank=True, null=True
    )
    recipient = models.EmailField(max_length=254)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    attempts = models.IntegerField(
        default=0,
        help_text="Number of delivery attempts"
    )
    last_attempt_at = models.DateTimeField(blank=True, null=True)
    next_retry_at = models.DateTimeField(
        blank=True, null=True,
        help_text="Scheduled time for next retry"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error details from failed delivery attempts"
    )
    smtp_response = models.TextField(
        blank=True,
        help_text="SMTP server response code and message"
    )
    delivered_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mail_email_delivery_status'
        verbose_name = 'Email Delivery Status'
        verbose_name_plural = 'Email Delivery Statuses'
        ordering = ['-created_at']
        indexes = [
            Index(fields=['status', 'next_retry_at']),
            Index(fields=['recipient']),
        ]

    def __str__(self):
        return f"{self.recipient} - {self.status}"

    def mark_as_sent(self):
        """Mark delivery as successful"""
        self.status = 'sent'
        self.delivered_at = timezone.now()
        self.save()

    def mark_as_failed(self, error_msg, smtp_response=''):
        """Mark delivery as failed"""
        self.status = 'failed'
        self.error_message = error_msg
        self.smtp_response = smtp_response
        self.last_attempt_at = timezone.now()
        self.save()

    def schedule_retry(self, delay_minutes=5):
        """Schedule next retry attempt"""
        self.status = 'deferred'
        self.next_retry_at = timezone.now() + timezone.timedelta(minutes=delay_minutes)
        self.attempts += 1
        self.last_attempt_at = timezone.now()
        self.save()
