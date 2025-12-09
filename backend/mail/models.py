from django.db import models
from django.conf import settings
from email_accounts.models import EmailAccount


class EmailMetadata(models.Model):
    """Store only email metadata - actual content is cached in Redis"""
    
    # Ownership
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_metadata')
    account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, related_name='email_metadata')
    
    # Essential metadata only
    message_id = models.CharField(max_length=255, unique=True, db_index=True)
    subject = models.CharField(max_length=500, blank=True)  # Truncated for preview
    from_email = models.EmailField()
    from_name = models.CharField(max_length=255, blank=True)
    
    # Flags (for quick filtering)
    is_read = models.BooleanField(default=False)
    is_starred = models.BooleanField(default=False)
    is_encrypted = models.BooleanField(default=False)
    has_attachments = models.BooleanField(default=False)
    
    # Timestamps
    sent_at = models.DateTimeField(db_index=True)
    cached_at = models.DateTimeField(auto_now=True)  # When metadata was last cached
    
    class Meta:
        db_table = 'email_metadata'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['user', 'account', '-sent_at']),
            models.Index(fields=['message_id']),
            models.Index(fields=['is_read', 'is_starred']),
        ]
    
    def __str__(self):
        return f"{self.subject[:50]} - {self.from_email}"


# Keep old Email model for backward compatibility during migration
class Email(models.Model):
    """Legacy model - DO NOT USE for new code. Use EmailMetadata + Redis cache instead."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='emails_legacy')
    account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, related_name='emails_legacy')
    message_id = models.CharField(max_length=255, unique=True)
    subject = models.TextField(blank=True)
    from_email = models.EmailField()
    from_name = models.CharField(max_length=255, blank=True)
    to_emails = models.TextField()
    cc_emails = models.TextField(blank=True)
    bcc_emails = models.TextField(blank=True)
    body_text = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    is_starred = models.BooleanField(default=False)
    is_encrypted = models.BooleanField(default=False)
    sent_at = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'emails_legacy'
        ordering = ['-sent_at']


class Attachment(models.Model):
    """Store email attachments with encryption support"""
    email = models.ForeignKey(Email, on_delete=models.CASCADE, related_name='attachments')
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.IntegerField()  # Size in bytes (original size before encryption)
    file_data = models.BinaryField()  # Store file content (encrypted or plain)
    
    # Encryption fields
    is_encrypted = models.BooleanField(default=False)
    security_level = models.CharField(max_length=20, blank=True, default='regular')  # 'regular', 'aes', 'qs_otp', 'qkd', 'qrng_pqc'
    encryption_metadata = models.JSONField(null=True, blank=True)  # Store key_id, algorithm, etc.
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'attachments'
    
    def __str__(self):
        return f"{self.filename} ({self.size} bytes)"
