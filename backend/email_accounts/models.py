from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet
import base64


class EmailAccount(models.Model):
    """
    Store external email account connections (Gmail, Outlook, etc.)
    Credentials are encrypted before storing
    """
    PROVIDER_CHOICES = [
        ('gmail', 'Gmail'),
        ('outlook', 'Outlook'),
        ('yahoo', 'Yahoo'),
        ('qutemail', 'QuTeMail'),
        ('custom', 'Custom IMAP/SMTP'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_accounts')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    email = models.EmailField()
    
    # Encrypted credentials
    _app_password = models.BinaryField()  # Encrypted app password
    
    # IMAP Settings
    imap_host = models.CharField(max_length=255, blank=True)
    imap_port = models.IntegerField(default=993)
    imap_use_ssl = models.BooleanField(default=True)
    
    # SMTP Settings
    smtp_host = models.CharField(max_length=255, blank=True)
    smtp_port = models.IntegerField(default=587)
    smtp_use_tls = models.BooleanField(default=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'email_accounts'
        unique_together = ['user', 'email']
    
    def __str__(self):
        return f"{self.email} ({self.provider})"
    
    @staticmethod
    def _get_cipher():
        """Get Fernet cipher for encryption/decryption"""
        # Use Django's SECRET_KEY for encryption (in production, use a dedicated key)
        key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32].ljust(32, b'0'))
        return Fernet(key)
    
    def set_app_password(self, plain_password):
        """Encrypt and store app password"""
        cipher = self._get_cipher()
        self._app_password = cipher.encrypt(plain_password.encode())
    
    def get_app_password(self):
        """Decrypt and return app password"""
        cipher = self._get_cipher()
        return cipher.decrypt(self._app_password).decode()
    
    def save(self, *args, **kwargs):
        # Set default IMAP/SMTP settings based on provider
        if not self.imap_host:
            if self.provider == 'gmail':
                self.imap_host = 'imap.gmail.com'
                self.smtp_host = 'smtp.gmail.com'
                self.imap_port = 993
                self.smtp_port = 587
            elif self.provider == 'outlook':
                self.imap_host = 'outlook.office365.com'
                self.smtp_host = 'smtp.office365.com'
                self.imap_port = 993
                self.smtp_port = 587
            elif self.provider == 'qutemail':
                self.imap_host = 'imappro.zoho.in'
                self.smtp_host = 'smtppro.zoho.in'
                self.imap_port = 993
                self.smtp_port = 587
                self.imap_use_ssl = True
                self.smtp_use_tls = True
            elif self.provider == 'yahoo':
                self.imap_host = 'imap.mail.yahoo.com'
                self.smtp_host = 'smtp.mail.yahoo.com'
                self.imap_port = 993
                self.smtp_port = 587
        
        super().save(*args, **kwargs)
