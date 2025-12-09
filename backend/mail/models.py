from django.db import models
from django.conf import settings
from email_accounts.models import EmailAccount


class Email(models.Model):
    """Store fetched emails from external providers"""

    FOLDER_CHOICES = (
        ('inbox', 'Inbox'),
        ('sent', 'Sent'),
        ('draft', 'Draft'),
        ('trash', 'Trash'),
    )

    # Ownership
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='emails')
    account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, related_name='emails')

    # ✅ NEW
    folder = models.CharField(
        max_length=10,
        choices=FOLDER_CHOICES,
        default='inbox',
        db_index=True
    )

    # Email metadata
    message_id = models.CharField(max_length=255, unique=True)
    subject = models.TextField(blank=True)
    from_email = models.EmailField()
    from_name = models.CharField(max_length=255, blank=True)
    to_emails = models.TextField()
    cc_emails = models.TextField(blank=True)
    bcc_emails = models.TextField(blank=True)

    # Content
    body_text = models.TextField(blank=True)
    body_html = models.TextField(blank=True)

    # Flags
    is_read = models.BooleanField(default=False)
    is_starred = models.BooleanField(default=False)
    is_encrypted = models.BooleanField(default=False)

    # Timestamps
    sent_at = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True)

    
    class Meta:
        db_table = 'emails'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['user', 'account', '-sent_at']),
            models.Index(fields=['message_id']),
        ]
    
    def __str__(self):
        return f"{self.subject[:50]} - {self.from_email}"


class Attachment(models.Model):
    """Store email attachments"""
    email = models.ForeignKey(Email, on_delete=models.CASCADE, related_name='attachments')
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.IntegerField()  # Size in bytes
    file_data = models.BinaryField()  # Store file content
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'attachments'
    
    def __str__(self):
        return f"{self.filename} ({self.size} bytes)"
