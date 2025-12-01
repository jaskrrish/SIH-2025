# QtEmail Developer Guide

Complete reference for all classes, methods, and functions in the QtEmail backend.

## Table of Contents

1. [Models Reference](#models-reference)
2. [Services Reference](#services-reference)
3. [Tasks Reference](#tasks-reference)
4. [Parsers Reference](#parsers-reference)
5. [Serializers Reference](#serializers-reference)
6. [ViewSets Reference](#viewsets-reference)
7. [Infrastructure Clients](#infrastructure-clients)
8. [Cryptography Reference](#cryptography-reference)
9. [Development Workflow](#development-workflow)

---

## Models Reference

### Email Model

**Location**: `apps/mail/models.py:14-207`

**Purpose**: Core email message model with support for QKD encryption

**Fields**:
```python
class Email(models.Model):
    # Core fields
    user = ForeignKey(User)              # Owner of the email
    message_id = CharField(max_length=255, unique=True)  # RFC822 Message-ID
    folder = CharField(choices=Folder.choices)  # inbox/sent/drafts/trash/spam/archive

    # Headers
    subject = CharField(max_length=998)
    from_address = EmailField()
    to_addresses = JSONField()           # List of email addresses
    cc_addresses = JSONField()
    bcc_addresses = JSONField()

    # Content
    body_text = TextField()              # Plain text body
    body_html = TextField()              # HTML body
    raw_email = BinaryField()            # Complete RFC822 message

    # Metadata
    date = DateTimeField()
    is_read = BooleanField(default=False)
    is_starred = BooleanField(default=False)
    has_attachments = BooleanField(default=False)
    size = IntegerField(default=0)       # Size in bytes

    # QKD Encryption
    is_encrypted = BooleanField(default=False)
    qkd_key_id = CharField(max_length=64)
    encryption_algorithm = CharField(max_length=50)
    encryption_nonce = CharField(max_length=128)
    encryption_tag = CharField(max_length=128)

    # Threading
    in_reply_to = CharField(max_length=255)  # Message-ID of parent
    references = TextField()                  # Space-separated Message-IDs

    # Status
    status = CharField(choices=Status.choices)  # draft/queued/sending/sent/failed/received

    # Timestamps
    sent_at = DateTimeField()
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Methods**:

```python
def mark_as_read(self):
    """Mark email as read"""
    self.is_read = True
    self.save()

def toggle_star(self):
    """Toggle starred status"""
    self.is_starred = not self.is_starred
    self.save()

def move_to_folder(self, folder: str):
    """Move email to different folder"""
    self.folder = folder
    self.save()
```

**Usage**:

```python
from mail.models import Email

# Create email
email = Email.objects.create(
    user=user,
    message_id='<unique@qutemail.local>',
    folder=Email.Folder.INBOX,
    subject='Test Email',
    from_address='sender@example.com',
    to_addresses=['recipient@qutemail.local'],
    body_text='Email content',
    status=Email.Status.RECEIVED
)

# Mark as read
email.mark_as_read()

# Move to archive
email.move_to_folder(Email.Folder.ARCHIVE)

# Query emails
inbox_emails = Email.objects.filter(
    user=user,
    folder=Email.Folder.INBOX,
    is_read=False
).order_by('-date')
```

---

### Attachment Model

**Location**: `apps/mail/models.py:210-272`

**Purpose**: Store email attachments with binary data in PostgreSQL

**Fields**:
```python
class Attachment(models.Model):
    email = ForeignKey(Email, on_delete=CASCADE, related_name='attachments')
    filename = CharField(max_length=255)
    content_type = CharField(max_length=100)  # MIME type
    size = IntegerField()                      # Bytes
    data = BinaryField()                       # Binary data stored in PostgreSQL
    checksum = CharField(max_length=64)        # SHA-256 hash
    content_id = CharField(max_length=255)     # For inline images
    is_inline = BooleanField(default=False)    # Embedded vs attached
    created_at = DateTimeField(auto_now_add=True)
```

**Usage**:

```python
from mail.models import Attachment
import hashlib

# Create attachment
file_data = b"File content here"
checksum = hashlib.sha256(file_data).hexdigest()

attachment = Attachment.objects.create(
    email=email,
    filename='document.pdf',
    content_type='application/pdf',
    size=len(file_data),
    data=file_data,
    checksum=checksum
)

# Retrieve attachment data
data = bytes(attachment.data)

# Get all attachments for an email
attachments = email.attachments.all()
```

---

### EmailQueue Model

**Location**: `apps/mail/models.py:275-372`

**Purpose**: Queue emails for async sending with retry logic and locking

**Fields**:
```python
class EmailQueue(models.Model):
    email = ForeignKey(Email, on_delete=CASCADE)
    priority = IntegerField(choices=Priority.choices, default=5)  # 1-10
    attempts = IntegerField(default=0)
    max_attempts = IntegerField(default=5)
    scheduled_at = DateTimeField()        # When to send
    next_retry_at = DateTimeField()       # Next retry time
    is_locked = BooleanField(default=False)  # Prevent duplicate processing
    locked_by = CharField(max_length=255)    # Worker ID
    locked_at = DateTimeField()
    created_at = DateTimeField(auto_now_add=True)
```

**Methods**:

```python
def lock(self, worker_id: str):
    """Lock queue entry for processing"""
    self.is_locked = True
    self.locked_by = worker_id
    self.locked_at = timezone.now()
    self.save()

def unlock(self):
    """Unlock queue entry after processing"""
    self.is_locked = False
    self.locked_by = None
    self.locked_at = None
    self.save()
```

**Usage**:

```python
from mail.models import EmailQueue
from django.utils import timezone

# Create queue entry
queue = EmailQueue.objects.create(
    email=email,
    priority=5,
    scheduled_at=timezone.now()
)

# Lock for processing
queue.lock(worker_id='worker-123')

# Process email...

# Unlock after processing
queue.unlock()

# Or delete on success
queue.delete()
```

---

### EmailLog Model

**Location**: `apps/mail/models.py:375-452`

**Purpose**: Event logging for email operations

**Fields**:
```python
class EmailLog(models.Model):
    email = ForeignKey(Email, on_delete=CASCADE, related_name='logs')
    event_type = CharField(choices=EventType.choices)  # queued/sent/failed/encrypted/etc
    message = TextField()
    metadata = JSONField(default=dict)     # Additional event data
    error_message = TextField()            # Error details
    traceback = TextField()                # Python traceback
    created_at = DateTimeField(auto_now_add=True)
```

**Event Types**:
- `queued`: Email added to send queue
- `sent`: Email sent successfully
- `failed`: Send attempt failed
- `retry`: Scheduled for retry
- `encrypted`: Body encrypted with QKD
- `decrypted`: Body decrypted successfully
- `qkd_key_requested`: QKD key requested
- `qkd_key_retrieved`: QKD key retrieved
- `decryption_failed`: Decryption error

**Usage**:

```python
from mail.models import EmailLog

# Log event
EmailLog.objects.create(
    email=email,
    event_type=EmailLog.EventType.SENT,
    message='Email sent successfully',
    metadata={'smtp_server': 'localhost:587'}
)

# Log error
EmailLog.objects.create(
    email=email,
    event_type=EmailLog.EventType.FAILED,
    message='SMTP connection failed',
    error_message=str(e),
    traceback=traceback.format_exc()
)

# Get logs for email
logs = EmailLog.objects.filter(email=email).order_by('-created_at')
```

---

### UserEmailSettings Model

**Location**: `apps/mail/models.py:455-537`

**Purpose**: User-specific email configuration

**Fields**:
```python
class UserEmailSettings(models.Model):
    user = OneToOneField(User, on_delete=CASCADE)
    email_address = EmailField(unique=True)  # user@qutemail.local
    display_name = CharField(max_length=255)
    signature = TextField()
    smtp_password_encrypted = BinaryField()
    imap_password_encrypted = BinaryField()
    enable_qkd_encryption = BooleanField(default=True)
    auto_fetch_interval = IntegerField(default=60)  # Seconds
    storage_quota_mb = IntegerField(default=1024)
    storage_used_mb = IntegerField(default=0)
    last_sync_at = DateTimeField()
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Methods**:

```python
def get_storage_usage_percentage(self) -> float:
    """Calculate storage usage percentage"""
    if self.storage_quota_mb == 0:
        return 0
    return (self.storage_used_mb / self.storage_quota_mb) * 100

def update_storage_usage(self):
    """Recalculate storage usage from database"""
    from django.db.models import Sum
    total_size = Email.objects.filter(user=self.user).aggregate(
        total=Sum('size')
    )['total'] or 0
    self.storage_used_mb = total_size // (1024 * 1024)
    self.save()
```

**Usage**:

```python
from mail.models import UserEmailSettings

# Get or create settings
settings, created = UserEmailSettings.objects.get_or_create(
    user=user,
    defaults={
        'email_address': f'{user.username}@qutemail.local',
        'display_name': user.get_full_name(),
        'enable_qkd_encryption': True,
    }
)

# Update settings
settings.enable_qkd_encryption = False
settings.auto_fetch_interval = 120
settings.save()

# Check storage
usage = settings.get_storage_usage_percentage()
print(f"Storage: {usage:.1f}%")
```

---

## Services Reference

### EmailSendService

**Location**: `apps/mail/services.py:28-311`

**Purpose**: High-level service for composing and sending emails

**Constructor**:
```python
def __init__(self, user: User):
    """
    Initialize send service for a specific user

    Args:
        user: Django User object
    """
```

**Methods**:

#### compose_email()

```python
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
```

**Usage**:

```python
from mail.services import EmailSendService

service = EmailSendService(user)

# Send plain email
email = service.compose_email(
    to_addresses=['recipient@example.com'],
    subject='Test Email',
    body_text='Hello, World!',
    encrypt=False
)

# Send encrypted email
encrypted_email = service.compose_email(
    to_addresses=['recipient@qutemail.local'],
    subject='Secret Message',
    body_text='Confidential information',
    encrypt=True
)

# Save as draft
draft = service.compose_email(
    to_addresses=['recipient@example.com'],
    subject='Draft Email',
    body_text='Work in progress',
    save_draft=True
)
```

#### send_email()

```python
def send_email(self, email: Email) -> bool:
    """
    Send an email via SMTP

    This is called by Celery task after dequeuing

    Args:
        email: Email object to send

    Returns:
        True if successful
    """
```

**Internal Methods**:

```python
def _queue_email(self, email: Email, encrypt: bool, priority: int):
    """Add email to send queue"""

def _encrypt_email_body(self, email: Email):
    """Encrypt email body using QKD"""

def _send_plain_email(self, email: Email) -> bool:
    """Send plain (unencrypted) email via SMTP"""

def _send_encrypted_email(self, email: Email) -> bool:
    """Send encrypted email via SMTP"""

def _attach_files(self, email: Email, attachments: List[Dict]):
    """Attach files to email"""
```

---

### EmailReceiveService

**Location**: `apps/mail/services.py:314-481`

**Purpose**: High-level service for receiving and processing emails

**Constructor**:
```python
def __init__(self, user: User):
    """
    Initialize receive service for a specific user

    Args:
        user: Django User object
    """
```

**Methods**:

#### fetch_new_emails()

```python
def fetch_new_emails(self, folder: str = 'INBOX', limit: int = 50) -> List[Email]:
    """
    Fetch new emails from IMAP server

    Args:
        folder: IMAP folder to fetch from
        limit: Maximum number of emails to fetch

    Returns:
        List of Email objects created
    """
```

**Usage**:

```python
from mail.services import EmailReceiveService

service = EmailReceiveService(user)

# Fetch new emails
emails = service.fetch_new_emails(folder='INBOX', limit=50)

print(f"Fetched {len(emails)} new emails")
for email in emails:
    print(f"  From: {email.from_address}")
    print(f"  Subject: {email.subject}")
    print(f"  Encrypted: {email.is_encrypted}")
```

**Internal Methods**:

```python
def _process_raw_email(self, raw_email_data: Dict, folder: str) -> Optional[Email]:
    """Process a raw email: parse, decrypt if needed, store"""

def _decrypt_email(self, email: Email, qkd_metadata: Dict):
    """Decrypt QKD-encrypted email"""

def _store_attachments(self, email: Email, attachments: List[Dict]):
    """Store email attachments"""

def _get_last_uid(self, folder: str) -> Optional[int]:
    """Get last processed UID for incremental fetching"""
```

---

## Tasks Reference

### process_email_queue

**Location**: `apps/mail/tasks.py:18-85`

**Purpose**: Celery task to process the email send queue

**Signature**:
```python
@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def process_email_queue(self):
    """
    Process the email queue and send pending emails

    Runs every 30 seconds via Celery Beat

    Returns:
        Dict with processing statistics
    """
```

**Behavior**:
1. Fetches unlocked queue entries ready to send
2. Locks entries to prevent duplicate processing
3. Delegates to `send_single_email` task
4. Returns statistics (processed, sent, failed, locked)

**Schedule**: Every 30 seconds (configured in `settings.py`)

---

### send_single_email

**Location**: `apps/mail/tasks.py:88-197`

**Purpose**: Send a single email with retry logic

**Signature**:
```python
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
```

**Retry Logic**:
1. Max 5 retry attempts
2. Exponential backoff: `min(120 * (2 ** attempts), 3600)` seconds
3. Marks email as failed after max retries
4. Unlocks queue entry on failure for retry

**Usage**:

```python
from mail.tasks import send_single_email

# Trigger manually
result = send_single_email.delay(email_id=42, queue_id=10)

# Wait for result
send_result = result.get(timeout=30)
print(send_result)
# {'success': True, 'email_id': 42, 'message': 'Email sent successfully'}
```

---

### fetch_incoming_emails

**Location**: `apps/mail/tasks.py:200-252`

**Purpose**: Periodic task to fetch emails for all users

**Signature**:
```python
@shared_task
def fetch_incoming_emails():
    """
    Periodic task to fetch incoming emails for all users via IMAP

    Runs every 60 seconds via Celery Beat

    Returns:
        Dict with fetch statistics
    """
```

**Behavior**:
1. Iterates through all users with `auto_fetch_interval > 0`
2. Checks if enough time has passed since last sync
3. Calls `EmailReceiveService.fetch_new_emails()` for each user
4. Returns statistics (users_processed, emails_fetched, errors)

**Schedule**: Every 60 seconds (configured in `settings.py`)

---

### cleanup_old_logs

**Location**: `apps/mail/tasks.py:295-329`

**Purpose**: Delete old email logs to prevent database bloat

**Signature**:
```python
@shared_task
def cleanup_old_logs(days: int = 90):
    """
    Clean up old email logs

    Args:
        days: Delete logs older than this many days (default: 90)

    Returns:
        Dict with cleanup statistics
    """
```

**Schedule**: Daily at 3:00 AM (configured in `settings.py`)

**Usage**:

```python
from mail.tasks import cleanup_old_logs

# Delete logs older than 30 days
result = cleanup_old_logs.delay(days=30)
print(result.get())
# {'success': True, 'deleted_count': 1523, 'cutoff_date': '2024-12-30T00:00:00Z'}
```

---

## Parsers Reference

### MailParserWrapper

**Location**: `apps/mail/parsers.py:11-318`

**Purpose**: Wrapper around mail-parser library for RFC822 email parsing

**Constructor**:
```python
def __init__(self, raw_email: bytes):
    """
    Initialize parser with raw RFC822 email bytes

    Args:
        raw_email: Complete RFC822 message as bytes
    """
```

**Methods**:

#### get_headers()

```python
def get_headers(self) -> Dict[str, str]:
    """Extract all email headers"""
```

#### get_body_text() / get_body_html()

```python
def get_body_text(self) -> str:
    """Get plain text body"""

def get_body_html(self) -> str:
    """Get HTML body"""
```

#### get_attachments()

```python
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
```

#### is_encrypted()

```python
def is_encrypted(self) -> bool:
    """
    Check if email is QKD encrypted

    Detects encryption by looking for:
    - [QKD-ENCRYPTED] marker in subject or body
    - X-QKD-Encrypted header
    """
```

#### get_qkd_metadata()

```python
def get_qkd_metadata(self) -> Optional[Dict]:
    """
    Extract QKD encryption metadata from email body

    Expected format:
    [ENCRYPTED MESSAGE]
    Key ID: <key_id>
    Ciphertext: <hex_ciphertext>
    Nonce: <hex_nonce>
    Tag: <hex_tag>

    Returns:
        Dictionary with qkd_key_id, ciphertext, nonce, tag or None
    """
```

**Usage**:

```python
from mail.parsers import MailParserWrapper

# Parse email
raw_email = b"From: sender@example.com\nTo: recipient@example.com\n\nBody"
parser = MailParserWrapper(raw_email)

# Extract data
headers = parser.get_headers()
body = parser.get_body_text()
attachments = parser.get_attachments()

# Check encryption
if parser.is_encrypted():
    metadata = parser.get_qkd_metadata()
    print(f"QKD Key ID: {metadata['qkd_key_id']}")

# Convert to dict
email_data = parser.to_dict()
```

---

## Infrastructure Clients

### SMTPClient

**Location**: `apps/infra/smtp_client.py:17-193`

**Purpose**: Enhanced SMTP client with attachment support

**Methods**:

#### send_email()

```python
def send_email(
    self,
    from_addr: str,
    to_addrs: List[str],
    subject: str,
    body_text: str = '',
    body_html: str = '',
    cc_addrs: List[str] = None,
    bcc_addrs: List[str] = None,
    attachments: List[Dict] = None,
    message_id: str = None,
    in_reply_to: str = None,
    references: str = None,
    username: str = None,
    password: str = None
) -> bool:
    """Send email via SMTP with full RFC822 support"""
```

**Usage**:

```python
from infra.smtp_client import SMTPClient

client = SMTPClient()

# Send simple email
result = client.send_email(
    from_addr='sender@qutemail.local',
    to_addrs=['recipient@example.com'],
    subject='Test Email',
    body_text='Hello, World!',
    username='sender@qutemail.local',
    password='password'
)

# Send with attachments
result = client.send_email(
    from_addr='sender@qutemail.local',
    to_addrs=['recipient@example.com'],
    subject='Email with Attachment',
    body_text='See attached',
    attachments=[{
        'filename': 'document.pdf',
        'content_type': 'application/pdf',
        'data': pdf_bytes
    }]
)
```

---

### IMAPClient

**Location**: `apps/infra/imap_client.py:14-365`

**Purpose**: Enhanced IMAP client with UID-based incremental fetching

**Methods**:

#### fetch_new_emails()

```python
def fetch_new_emails(
    self,
    username: str,
    password: str,
    folder: str = 'INBOX',
    last_uid: Optional[int] = None,
    limit: int = 50
) -> List[Dict]:
    """
    Fetch new emails using UID-based incremental fetching

    Args:
        username: IMAP username
        password: IMAP password
        folder: Mailbox folder
        last_uid: Last processed UID (fetch only newer)
        limit: Maximum emails to fetch

    Returns:
        List of dicts with 'uid' and 'raw' (RFC822 bytes)
    """
```

**Usage**:

```python
from infra.imap_client import IMAPClient

client = IMAPClient()

# Fetch new emails
emails = client.fetch_new_emails(
    username='user@qutemail.local',
    password='password',
    folder='INBOX',
    last_uid=1234,  # Only fetch UIDs > 1234
    limit=50
)

for email_data in emails:
    uid = email_data['uid']
    raw_bytes = email_data['raw']
    # Process email...
```

---

## Cryptography Reference

### derive_key()

**Location**: `apps/crypto/utils.py:13-37`

```python
def derive_key(
    master_key: bytes,
    info: bytes = b'',
    salt: bytes = None,
    length: int = 32
) -> bytes:
    """
    Derive a key using HKDF (HMAC-based Key Derivation Function)

    Args:
        master_key: Master key material (from QKD)
        info: Application-specific context information
        salt: Optional salt value
        length: Desired output key length in bytes

    Returns:
        Derived key material
    """
```

---

### hybrid_encrypt()

**Location**: `apps/crypto/utils.py:131-154`

```python
def hybrid_encrypt(plaintext: bytes, qkd_key: bytes) -> dict:
    """
    Hybrid encryption: Use QKD key with AES-GCM

    Process:
    1. Derive encryption key from QKD key using HKDF
    2. Encrypt with AES-256-GCM
    3. Return ciphertext, nonce, tag

    Args:
        plaintext: Data to encrypt
        qkd_key: Quantum-generated key material

    Returns:
        Dict containing:
        - ciphertext: hex-encoded encrypted data
        - nonce: hex-encoded nonce
        - tag: hex-encoded authentication tag
        - algorithm: 'AES-256-GCM'
        - kdf: 'HKDF-SHA256'
    """
```

---

### hybrid_decrypt()

**Location**: `apps/crypto/utils.py:157-179`

```python
def hybrid_decrypt(encrypted_data: dict, qkd_key: bytes) -> bytes:
    """
    Hybrid decryption: Use QKD key with AES-GCM

    Args:
        encrypted_data: Dict with ciphertext, nonce, tag
        qkd_key: Quantum-generated key material

    Returns:
        Decrypted plaintext bytes
    """
```

**Usage**:

```python
from crypto.utils import hybrid_encrypt, hybrid_decrypt
import os

# Generate or retrieve QKD key
qkd_key = os.urandom(32)  # In production, from QKDService

# Encrypt
plaintext = b"Secret message"
encrypted = hybrid_encrypt(plaintext, qkd_key)

print(encrypted)
# {
#   'ciphertext': 'abc123...',
#   'nonce': 'def456...',
#   'tag': 'ghi789...',
#   'algorithm': 'AES-256-GCM',
#   'kdf': 'HKDF-SHA256'
# }

# Decrypt
decrypted = hybrid_decrypt(encrypted, qkd_key)
assert decrypted == plaintext
```

---

## Development Workflow

### Adding a New Feature

1. **Create Database Model** (if needed):
   ```python
   # apps/mail/models.py
   class NewFeature(models.Model):
       # Define fields
       pass
   ```

2. **Create Migration**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **Create Service** (if needed):
   ```python
   # apps/mail/services.py
   class NewFeatureService:
       def __init__(self, user):
           self.user = user

       def do_something(self):
           # Implementation
           pass
   ```

4. **Create Serializer**:
   ```python
   # apps/mail/serializers.py
   class NewFeatureSerializer(serializers.ModelSerializer):
       class Meta:
           model = NewFeature
           fields = '__all__'
   ```

5. **Create ViewSet**:
   ```python
   # apps/mail/viewsets.py
   class NewFeatureViewSet(viewsets.ModelViewSet):
       serializer_class = NewFeatureSerializer
       permission_classes = [IsAuthenticated]

       def get_queryset(self):
           return NewFeature.objects.filter(user=self.request.user)
   ```

6. **Add URLs**:
   ```python
   # apps/mail/urls.py
   router.register(r'newfeature', NewFeatureViewSet, basename='newfeature')
   ```

7. **Write Tests**:
   ```python
   # tests/test_newfeature.py
   class NewFeatureTest(TestCase):
       def test_feature(self):
           # Test implementation
           pass
   ```

8. **Run Tests**:
   ```bash
   python manage.py test tests.test_newfeature
   ```

---

### Debugging Tips

#### Enable SQL Query Logging

```python
# settings.py
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

#### Debug Celery Tasks

```python
# Use .apply() instead of .delay() for synchronous execution
from mail.tasks import send_single_email

# Synchronous (blocks, easier to debug)
result = send_single_email.apply(args=[email_id, queue_id])

# Asynchronous (normal)
result = send_single_email.delay(email_id, queue_id)
```

#### Django Debug Toolbar

```bash
pip install django-debug-toolbar

# Add to INSTALLED_APPS
INSTALLED_APPS += ['debug_toolbar']

# Add to MIDDLEWARE
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

# Add to urls.py
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
```

---

### Code Style Guidelines

**Follow PEP 8**:
```bash
# Install linters
pip install flake8 black

# Format code
black apps/

# Check style
flake8 apps/
```

**Type Hints**:
```python
from typing import List, Dict, Optional

def process_emails(
    emails: List[Email],
    folder: str = 'inbox'
) -> Dict[str, int]:
    """
    Process a list of emails

    Args:
        emails: List of Email objects
        folder: Target folder

    Returns:
        Statistics dictionary
    """
    processed = 0
    # Implementation
    return {'processed': processed}
```

**Docstrings**:
```python
def complex_function(param1: str, param2: int) -> bool:
    """
    One-line summary

    Detailed description of what the function does,
    edge cases, and important notes.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When param2 is negative
        TypeError: When param1 is not a string
    """
    pass
```

---

### Performance Best Practices

1. **Use select_related() and prefetch_related()**:
   ```python
   # Bad (N+1 queries)
   emails = Email.objects.filter(user=user)
   for email in emails:
       print(email.user.username)  # Extra query per email

   # Good (2 queries)
   emails = Email.objects.filter(user=user).select_related('user')
   for email in emails:
       print(email.user.username)  # No extra query
   ```

2. **Bulk Operations**:
   ```python
   # Bad (N queries)
   for email in emails:
       email.is_read = True
       email.save()

   # Good (1 query)
   Email.objects.filter(id__in=email_ids).update(is_read=True)
   ```

3. **Database Indexes**:
   ```python
   class Email(models.Model):
       # Add indexes for frequently queried fields
       class Meta:
           indexes = [
               models.Index(fields=['user', 'folder', '-date']),
               models.Index(fields=['status', 'created_at']),
           ]
   ```

4. **Caching**:
   ```python
   from django.core.cache import cache

   # Cache expensive queries
   cache_key = f'user_{user.id}_inbox_count'
   count = cache.get(cache_key)

   if count is None:
       count = Email.objects.filter(user=user, folder='inbox').count()
       cache.set(cache_key, count, timeout=300)  # 5 minutes
   ```

---

This developer guide provides comprehensive reference material for all components of the QtEmail system. Use it alongside the API Reference and Testing Guide for complete documentation!
