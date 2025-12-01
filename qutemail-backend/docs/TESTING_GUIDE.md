# QtEmail Testing Guide

Comprehensive guide for testing all functionalities of the QtEmail backend system.

## Table of Contents

1. [Setup Test Environment](#setup-test-environment)
2. [Unit Testing](#unit-testing)
3. [Integration Testing](#integration-testing)
4. [End-to-End Testing](#end-to-end-testing)
5. [Performance Testing](#performance-testing)
6. [Security Testing](#security-testing)
7. [Troubleshooting](#troubleshooting)

---

## Setup Test Environment

### Prerequisites

```bash
# Ensure all dependencies are installed
pip install -r requirements.txt

# Verify Docker is running
docker --version
docker-compose --version

# Check PostgreSQL connection (if using)
psql -U qutemail_user -h localhost -d qutemail_db -c "SELECT version();"

# Check Redis connection
redis-cli ping
```

### Start Infrastructure Services

```bash
# Start all Docker services
docker-compose up -d

# Verify services are running
docker-compose ps

# Expected output:
# qutemail_db         running
# qutemail_redis      running
# qutemail_postfix    running
# qutemail_dovecot    running
# qutemail_opendkim   running
```

### Generate DKIM Keys

```bash
# Create keys directory
mkdir -p config/opendkim/keys

# Generate DKIM key pair
cd config/opendkim/keys
docker exec qutemail_opendkim opendkim-genkey -b 2048 -d qutemail.local -s default -v

# Set proper permissions
docker exec chmod 600 default.private
docker exec chmod 644 default.txt

cd ../../..
```

### Initialize Database

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
# Username: admin
# Email: admin@qutemail.local
# Password: [your secure password]

# Create test users
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from mail.models import UserEmailSettings

User = get_user_model()

# Create test users
users_data = [
    ('alice', 'alice@qutemail.local', 'Alice Smith'),
    ('bob', 'bob@qutemail.local', 'Bob Johnson'),
    ('charlie', 'charlie@qutemail.local', 'Charlie Brown'),
]

for username, email, display_name in users_data:
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': email}
    )
    if created:
        user.set_password('testpass123')
        user.save()

    UserEmailSettings.objects.get_or_create(
        user=user,
        defaults={
            'email_address': email,
            'display_name': display_name,
            'enable_qkd_encryption': True,
            'auto_fetch_interval': 60,
            'storage_quota_mb': 1024,
        }
    )
    print(f"Created user: {username}")
```

### Start Application Services

```bash
# Terminal 1: Django development server
python manage.py runserver

# Terminal 2: Celery worker
celery -A qutemail worker -l info

# Terminal 3: Celery beat scheduler
celery -A qutemail beat -l info
```

---

## Unit Testing

### Test Database Models

**Test Email Model**:

```python
# tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from mail.models import Email, EmailQueue, EmailLog, UserEmailSettings

User = get_user_model()

class EmailModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.settings = UserEmailSettings.objects.create(
            user=self.user,
            email_address='testuser@qutemail.local',
            display_name='Test User'
        )

    def test_email_creation(self):
        """Test creating an email"""
        email = Email.objects.create(
            user=self.user,
            message_id='<test@qutemail.local>',
            folder=Email.Folder.INBOX,
            subject='Test Email',
            from_address='sender@example.com',
            to_addresses=['testuser@qutemail.local'],
            body_text='This is a test email',
            status=Email.Status.RECEIVED
        )

        self.assertEqual(email.subject, 'Test Email')
        self.assertFalse(email.is_read)
        self.assertFalse(email.is_starred)
        self.assertFalse(email.is_encrypted)

    def test_mark_as_read(self):
        """Test marking email as read"""
        email = Email.objects.create(
            user=self.user,
            message_id='<test2@qutemail.local>',
            folder=Email.Folder.INBOX,
            subject='Test',
            from_address='sender@example.com',
            to_addresses=['testuser@qutemail.local'],
            body_text='Test',
            status=Email.Status.RECEIVED
        )

        self.assertFalse(email.is_read)
        email.mark_as_read()
        self.assertTrue(email.is_read)

    def test_move_to_folder(self):
        """Test moving email to different folder"""
        email = Email.objects.create(
            user=self.user,
            message_id='<test3@qutemail.local>',
            folder=Email.Folder.INBOX,
            subject='Test',
            from_address='sender@example.com',
            to_addresses=['testuser@qutemail.local'],
            body_text='Test',
            status=Email.Status.RECEIVED
        )

        email.move_to_folder(Email.Folder.ARCHIVE)
        self.assertEqual(email.folder, Email.Folder.ARCHIVE)

# Run tests
python manage.py test tests.test_models
```

**Test Email Queue**:

```python
def test_queue_locking(self):
    """Test queue entry locking mechanism"""
    email = Email.objects.create(
        user=self.user,
        message_id='<test4@qutemail.local>',
        folder=Email.Folder.SENT,
        subject='Test',
        from_address='testuser@qutemail.local',
        to_addresses=['recipient@example.com'],
        body_text='Test',
        status=Email.Status.QUEUED
    )

    queue = EmailQueue.objects.create(email=email)

    # Test locking
    self.assertFalse(queue.is_locked)
    queue.lock(worker_id='worker-1')
    self.assertTrue(queue.is_locked)
    self.assertEqual(queue.locked_by, 'worker-1')

    # Test unlocking
    queue.unlock()
    self.assertFalse(queue.is_locked)
    self.assertIsNone(queue.locked_by)
```

### Test Services

**Test EmailSendService**:

```python
# tests/test_services.py
from django.test import TestCase
from mail.services import EmailSendService
from mail.models import Email, EmailQueue

class EmailSendServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.settings = UserEmailSettings.objects.create(
            user=self.user,
            email_address='testuser@qutemail.local',
            display_name='Test User',
            enable_qkd_encryption=True
        )
        self.service = EmailSendService(self.user)

    def test_compose_email_plain(self):
        """Test composing plain (unencrypted) email"""
        email = self.service.compose_email(
            to_addresses=['recipient@example.com'],
            subject='Test Email',
            body_text='Hello, World!',
            encrypt=False
        )

        self.assertIsNotNone(email)
        self.assertEqual(email.subject, 'Test Email')
        self.assertFalse(email.is_encrypted)
        self.assertEqual(email.status, Email.Status.QUEUED)

        # Check queue entry was created
        self.assertTrue(EmailQueue.objects.filter(email=email).exists())

    def test_compose_email_encrypted(self):
        """Test composing QKD-encrypted email"""
        email = self.service.compose_email(
            to_addresses=['recipient@example.com'],
            subject='Secure Email',
            body_text='Secret message',
            encrypt=True
        )

        self.assertIsNotNone(email)
        self.assertTrue(email.is_encrypted)
        self.assertIsNotNone(email.qkd_key_id)
        self.assertIn('[QKD-ENCRYPTED]', email.subject)
        self.assertIn('Key ID:', email.body_text)

# Run tests
python manage.py test tests.test_services
```

**Test QKD Service**:

```python
from qkd.services import QKDService

class QKDServiceTest(TestCase):
    def test_request_key_simulator_mode(self):
        """Test requesting key in simulator mode"""
        service = QKDService()
        result = service.request_key(key_size=256)

        self.assertIn('key_id', result)
        self.assertIn('key_material', result)
        self.assertEqual(result['source'], 'simulator')
        self.assertEqual(len(result['key_material']), 64)  # 256 bits = 64 hex chars

    def test_get_key_by_id(self):
        """Test retrieving key by ID"""
        service = QKDService()

        # Request a key
        key_data = service.request_key(256)
        key_id = key_data['key_id']

        # Retrieve the same key
        retrieved = service.get_key_by_id(key_id)
        self.assertEqual(retrieved['key_id'], key_id)
        self.assertIn('key_material', retrieved)
```

### Test Crypto Utilities

```python
# tests/test_crypto.py
from django.test import TestCase
from crypto.utils import (
    derive_key, aes_gcm_encrypt, aes_gcm_decrypt,
    otp_encrypt, otp_decrypt, hybrid_encrypt, hybrid_decrypt
)
import os

class CryptoTest(TestCase):
    def test_hkdf_derivation(self):
        """Test HKDF key derivation"""
        master_key = os.urandom(32)
        derived1 = derive_key(master_key, info=b'test-context')
        derived2 = derive_key(master_key, info=b'test-context')

        # Same input should give same output (with fixed salt)
        self.assertEqual(len(derived1), 32)
        self.assertEqual(len(derived2), 32)

    def test_aes_gcm_encryption(self):
        """Test AES-256-GCM encryption/decryption"""
        key = os.urandom(32)
        plaintext = b"Secret message"

        ciphertext, nonce, tag = aes_gcm_encrypt(plaintext, key)
        decrypted = aes_gcm_decrypt(ciphertext, key, nonce, tag)

        self.assertEqual(decrypted, plaintext)

    def test_otp_encryption(self):
        """Test one-time pad encryption"""
        plaintext = b"Hello, World!"
        key = os.urandom(len(plaintext))

        ciphertext = otp_encrypt(plaintext, key)
        decrypted = otp_decrypt(ciphertext, key)

        self.assertEqual(decrypted, plaintext)

    def test_hybrid_encryption(self):
        """Test hybrid QKD + AES encryption"""
        qkd_key = os.urandom(32)
        plaintext = b"Quantum-secured message"

        encrypted = hybrid_encrypt(plaintext, qkd_key)

        self.assertIn('ciphertext', encrypted)
        self.assertIn('nonce', encrypted)
        self.assertIn('tag', encrypted)
        self.assertEqual(encrypted['algorithm'], 'AES-256-GCM')

        # Decrypt
        decrypted = hybrid_decrypt(encrypted, qkd_key)
        self.assertEqual(decrypted, plaintext)

# Run tests
python manage.py test tests.test_crypto
```

### Test Parsers

```python
# tests/test_parsers.py
from mail.parsers import MailParserWrapper

class MailParserTest(TestCase):
    def test_parse_simple_email(self):
        """Test parsing a simple email"""
        raw_email = b"""From: sender@example.com
To: recipient@qutemail.local
Subject: Test Email
Date: Mon, 29 Jan 2025 10:00:00 +0000
Message-ID: <test@example.com>

Hello, this is a test email.
"""
        parser = MailParserWrapper(raw_email)

        self.assertEqual(parser.get_subject(), 'Test Email')
        self.assertEqual(parser.get_from(), 'sender@example.com')
        self.assertIn('recipient@qutemail.local', parser.get_to())
        self.assertIn('Hello', parser.get_body_text())
        self.assertFalse(parser.is_encrypted())

    def test_parse_encrypted_email(self):
        """Test parsing QKD-encrypted email"""
        raw_email = b"""From: sender@qutemail.local
To: recipient@qutemail.local
Subject: [QKD-ENCRYPTED] Secure Message
Date: Mon, 29 Jan 2025 10:00:00 +0000

[ENCRYPTED MESSAGE]
Key ID: test-key-123
Ciphertext: abc123def456
Nonce: 789xyz
Tag: tag123

This message is encrypted with QKD.
"""
        parser = MailParserWrapper(raw_email)

        self.assertTrue(parser.is_encrypted())
        metadata = parser.get_qkd_metadata()

        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['qkd_key_id'], 'test-key-123')
        self.assertEqual(metadata['ciphertext'], 'abc123def456')

# Run tests
python manage.py test tests.test_parsers
```

---

## Integration Testing

### Test Email Composition and Queueing

```python
# Django shell
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from mail.services import EmailSendService
from mail.models import Email, EmailQueue, EmailLog

User = get_user_model()
user = User.objects.get(username='alice')
service = EmailSendService(user)

# Test 1: Compose plain email
email = service.compose_email(
    to_addresses=['bob@qutemail.local'],
    subject='Test Plain Email',
    body_text='This is a test of the email system.',
    encrypt=False
)

print(f"Email ID: {email.id}")
print(f"Status: {email.status}")
print(f"Encrypted: {email.is_encrypted}")
print(f"Queued: {EmailQueue.objects.filter(email=email).exists()}")

# Test 2: Compose encrypted email
encrypted_email = service.compose_email(
    to_addresses=['bob@qutemail.local'],
    subject='Test Encrypted Email',
    body_text='This is a secret message.',
    encrypt=True
)

print(f"\nEncrypted Email ID: {encrypted_email.id}")
print(f"Subject: {encrypted_email.subject}")
print(f"QKD Key ID: {encrypted_email.qkd_key_id}")
print(f"Body preview: {encrypted_email.body_text[:100]}")

# Test 3: Check logs
logs = EmailLog.objects.filter(email=encrypted_email).order_by('created_at')
for log in logs:
    print(f"\nLog: {log.event_type} - {log.message}")
```

### Test Celery Task Execution

```bash
# In one terminal, monitor Celery worker logs
celery -A qutemail worker -l info

# In another terminal, trigger tasks manually
python manage.py shell
```

```python
from mail.tasks import process_email_queue, send_single_email, fetch_incoming_emails
from mail.models import EmailQueue

# Test queue processing
result = process_email_queue.delay()
print(f"Task ID: {result.id}")
print(f"Status: {result.status}")

# Wait a few seconds and check result
import time
time.sleep(5)
print(f"Result: {result.get()}")

# Test single email sending
queue_entry = EmailQueue.objects.first()
if queue_entry:
    result = send_single_email.delay(queue_entry.email.id, queue_entry.id)
    print(f"Send result: {result.get(timeout=30)}")

# Test email fetching
result = fetch_incoming_emails.delay()
print(f"Fetch result: {result.get(timeout=60)}")
```

### Test SMTP Integration

```python
# Test SMTP client directly
from infra.smtp_client import SMTPClient

client = SMTPClient()

# Verify connection
connected = client.verify_connection()
print(f"SMTP connected: {connected}")

# Send test email
result = client.send_email(
    from_addr='alice@qutemail.local',
    to_addrs=['bob@qutemail.local'],
    subject='SMTP Test',
    body_text='Testing SMTP integration',
    attachments=None
)

print(f"Email sent: {result}")
```

### Test IMAP Integration

```python
# Test IMAP client directly
from infra.imap_client import IMAPClient

client = IMAPClient()

# Verify connection (requires credentials)
connected = client.verify_connection('alice@qutemail.local', 'password')
print(f"IMAP connected: {connected}")

# Fetch emails
emails = client.fetch_new_emails(
    username='alice@qutemail.local',
    password='password',
    folder='INBOX',
    last_uid=None,
    limit=10
)

print(f"Fetched {len(emails)} emails")
for email_data in emails:
    print(f"  UID: {email_data['uid']}")
```

---

## End-to-End Testing

### Test Scenario 1: Send Unencrypted Email

```mermaid
sequenceDiagram
    participant Test as Test Script
    participant API as REST API
    participant Queue as Email Queue
    participant Celery as Celery Worker
    participant SMTP as Postfix/SMTP
    participant IMAP as Dovecot/IMAP

    Test->>API: POST /api/v1/emails/ (encrypt=false)
    API->>Queue: Create email + queue entry
    API-->>Test: 201 Created

    Note over Celery: Every 30 seconds
    Celery->>Queue: Process queue
    Celery->>SMTP: Send email
    SMTP->>IMAP: Deliver to mailbox

    Test->>API: GET /api/v1/emails/sync/
    API->>Celery: Trigger IMAP fetch
    Celery->>IMAP: Fetch emails
    IMAP-->>Celery: Email data
    Celery->>API: Store in database

    Test->>API: GET /api/v1/emails/?folder=inbox
    API-->>Test: Email received!
```

**Test Script**:

```bash
# test_e2e_plain.sh
#!/bin/bash

# Step 1: Compose email via API
curl -X POST \
  'http://localhost:8000/api/v1/emails/' \
  -H 'Content-Type: application/json' \
  -b cookies.txt \
  -d '{
    "to_addresses": ["bob@qutemail.local"],
    "subject": "E2E Test Plain",
    "body_text": "This is an end-to-end test.",
    "encrypt": false
  }' | jq

# Step 2: Wait for queue processing (30 seconds)
echo "Waiting 30 seconds for queue processing..."
sleep 30

# Step 3: Trigger sync for recipient
curl -X POST \
  'http://localhost:8000/api/v1/emails/sync/' \
  -H 'Content-Type: application/json' \
  -b cookies-bob.txt \
  -d '{"folder": "INBOX"}' | jq

# Step 4: Wait for IMAP fetch (60 seconds)
echo "Waiting 60 seconds for IMAP fetch..."
sleep 60

# Step 5: Check recipient's inbox
curl -X GET \
  'http://localhost:8000/api/v1/emails/?folder=inbox&search=E2E' \
  -b cookies-bob.txt | jq

echo "Test complete! Check if email was received."
```

### Test Scenario 2: Send QKD-Encrypted Email

**Test Script**:

```python
# test_e2e_encrypted.py
import requests
import time
import json

BASE_URL = 'http://localhost:8000'

# Login as Alice
session_alice = requests.Session()
session_alice.post(f'{BASE_URL}/api-auth/login/', data={
    'username': 'alice',
    'password': 'testpass123'
})

# Login as Bob
session_bob = requests.Session()
session_bob.post(f'{BASE_URL}/api-auth/login/', data={
    'username': 'bob',
    'password': 'testpass123'
})

# Step 1: Alice sends encrypted email to Bob
print("Step 1: Alice composing encrypted email...")
response = session_alice.post(f'{BASE_URL}/api/v1/emails/', json={
    'to_addresses': ['bob@qutemail.local'],
    'subject': 'E2E Encrypted Test',
    'body_text': 'This is a quantum-secured secret message.',
    'encrypt': True
})

email_data = response.json()
print(f"Email created: ID={email_data['id']}, Encrypted={email_data['is_encrypted']}")
print(f"QKD Key ID: {email_data.get('qkd_key_id')}")

# Step 2: Wait for queue processing
print("\nStep 2: Waiting for email to be sent (30s)...")
time.sleep(30)

# Step 3: Check email status
response = session_alice.get(f"{BASE_URL}/api/v1/emails/{email_data['id']}/")
email_status = response.json()
print(f"Email status: {email_status['status']}")

# Step 4: Check email logs
response = session_alice.get(f"{BASE_URL}/api/v1/emails/{email_data['id']}/logs/")
logs = response.json()
print(f"\nEmail logs:")
for log in logs:
    print(f"  - {log['event_type']}: {log['message']}")

# Step 5: Trigger sync for Bob
print("\nStep 5: Triggering sync for Bob...")
response = session_bob.post(f'{BASE_URL}/api/v1/emails/sync/', json={
    'folder': 'INBOX'
})
print(f"Sync triggered: {response.json()}")

# Step 6: Wait for IMAP fetch
print("\nStep 6: Waiting for IMAP fetch (60s)...")
time.sleep(60)

# Step 7: Bob checks inbox
print("\nStep 7: Bob checking inbox...")
response = session_bob.get(f'{BASE_URL}/api/v1/emails/', params={
    'folder': 'inbox',
    'search': 'E2E Encrypted'
})

emails = response.json()['results']
if emails:
    received_email = emails[0]
    print(f"Email received!")
    print(f"  Subject: {received_email['subject']}")
    print(f"  Encrypted: {received_email['is_encrypted']}")
    print(f"  From: {received_email['from_address']}")

    # Get full email details
    response = session_bob.get(f"{BASE_URL}/api/v1/emails/{received_email['id']}/")
    full_email = response.json()
    print(f"  Body (decrypted): {full_email['body_text'][:100]}")
else:
    print("ERROR: Email not received!")

print("\n✅ End-to-end encrypted email test complete!")
```

Run the test:

```bash
python test_e2e_encrypted.py
```

### Test Scenario 3: Reply and Forward

```python
# test_reply_forward.py
import requests

BASE_URL = 'http://localhost:8000'
session = requests.Session()
session.post(f'{BASE_URL}/api-auth/login/', data={
    'username': 'alice',
    'password': 'testpass123'
})

# Get an email from inbox
response = session.get(f'{BASE_URL}/api/v1/emails/', params={'folder': 'inbox'})
emails = response.json()['results']

if emails:
    original_email = emails[0]
    email_id = original_email['id']

    # Test 1: Reply
    print("Test 1: Replying to email...")
    response = session.post(f'{BASE_URL}/api/v1/emails/{email_id}/reply/', json={
        'body_text': 'Thank you for your message!',
        'encrypt': True
    })

    reply = response.json()
    print(f"Reply created: ID={reply['id']}")
    print(f"  Subject: {reply['subject']}")
    print(f"  In-Reply-To: {reply['in_reply_to']}")

    # Test 2: Forward
    print("\nTest 2: Forwarding email...")
    response = session.post(f'{BASE_URL}/api/v1/emails/{email_id}/forward/', json={
        'to_addresses': ['charlie@qutemail.local'],
        'include_attachments': True
    })

    forwarded = response.json()
    print(f"Forwarded email created: ID={forwarded['id']}")
    print(f"  Subject: {forwarded['subject']}")
    print(f"  To: {forwarded['to_addresses']}")
else:
    print("No emails in inbox to test with!")
```

### Test Scenario 4: Attachments

```python
# test_attachments.py
import requests
import os

BASE_URL = 'http://localhost:8000'
session = requests.Session()
session.post(f'{BASE_URL}/api-auth/login/', data={
    'username': 'alice',
    'password': 'testpass123'
})

# Create a test file
test_file_content = b"This is a test attachment file.\nIt has multiple lines.\n"
with open('test_file.txt', 'wb') as f:
    f.write(test_file_content)

# Test 1: Upload attachment
print("Test 1: Uploading attachment...")
with open('test_file.txt', 'rb') as f:
    response = session.post(
        f'{BASE_URL}/api/v1/attachments/upload/',
        files={'file': ('test_file.txt', f, 'text/plain')},
        data={'is_inline': 'false'}
    )

attachment_data = response.json()
print(f"Attachment uploaded:")
print(f"  Filename: {attachment_data['filename']}")
print(f"  Size: {attachment_data['size']} bytes")
print(f"  Checksum: {attachment_data['checksum']}")

# Test 2: Send email with attachment
print("\nTest 2: Sending email with attachment...")
response = session.post(f'{BASE_URL}/api/v1/emails/', json={
    'to_addresses': ['bob@qutemail.local'],
    'subject': 'Email with Attachment',
    'body_text': 'Please see attached file.',
    'encrypt': False,
    'attachment_ids': []  # Note: Current implementation needs enhancement for this
})

# Test 3: Download attachment
print("\nTest 3: Listing and downloading attachments...")
response = session.get(f'{BASE_URL}/api/v1/attachments/')
attachments = response.json()['results']

if attachments:
    attachment_id = attachments[0]['id']

    # Download
    response = session.get(f'{BASE_URL}/api/v1/attachments/{attachment_id}/download/')

    with open('downloaded_file.txt', 'wb') as f:
        f.write(response.content)

    print(f"Attachment {attachment_id} downloaded successfully!")

    # Verify content
    with open('downloaded_file.txt', 'rb') as f:
        downloaded_content = f.read()

    assert downloaded_content == test_file_content, "Downloaded content doesn't match!"
    print("✅ Content verification passed!")

# Cleanup
os.remove('test_file.txt')
os.remove('downloaded_file.txt')
```

---

## Performance Testing

### Load Testing with Locust

Create `locustfile.py`:

```python
from locust import HttpUser, task, between
import random

class QtEmailUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        """Login on start"""
        self.client.post('/api-auth/login/', data={
            'username': 'alice',
            'password': 'testpass123'
        })

    @task(3)
    def list_emails(self):
        """List inbox emails"""
        self.client.get('/api/v1/emails/', params={'folder': 'inbox'})

    @task(2)
    def view_email(self):
        """View random email"""
        response = self.client.get('/api/v1/emails/', params={'folder': 'inbox'})
        emails = response.json().get('results', [])
        if emails:
            email_id = random.choice(emails)['id']
            self.client.get(f'/api/v1/emails/{email_id}/')

    @task(1)
    def compose_email(self):
        """Compose new email"""
        self.client.post('/api/v1/emails/', json={
            'to_addresses': ['bob@qutemail.local'],
            'subject': f'Load Test Email {random.randint(1000, 9999)}',
            'body_text': 'This is a load test email.',
            'encrypt': False
        })

    @task(1)
    def mark_read(self):
        """Mark email as read"""
        response = self.client.get('/api/v1/emails/', params={
            'folder': 'inbox',
            'is_read': 'false'
        })
        emails = response.json().get('results', [])
        if emails:
            email_id = random.choice(emails)['id']
            self.client.post(f'/api/v1/emails/{email_id}/mark_read/')
```

Run load test:

```bash
# Install locust
pip install locust

# Run with 10 users, spawn rate 1/sec
locust -f locustfile.py --host=http://localhost:8000 --users 10 --spawn-rate 1

# Open web UI
open http://localhost:8089
```

### Database Query Performance

```python
# Check slow queries
from django.db import connection
from django.test.utils import CaptureQueriesContext

from mail.models import Email
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.get(username='alice')

# Measure queries for list endpoint
with CaptureQueriesContext(connection) as context:
    emails = list(Email.objects.filter(user=user).select_related('user').prefetch_related('attachments')[:50])

print(f"Number of queries: {len(context)}")
for query in context.captured_queries:
    print(f"  {query['time']}s: {query['sql'][:100]}")
```

### Celery Task Performance

```python
# Monitor task execution time
from mail.tasks import process_email_queue
import time

start = time.time()
result = process_email_queue.delay()
result.get(timeout=60)
end = time.time()

print(f"Task execution time: {end - start:.2f}s")
```

---

## Security Testing

### Test QKD Encryption Security

```python
# Verify encryption is working
from qkd.services import QKDService
from crypto.utils import hybrid_encrypt, hybrid_decrypt
import os

# Request key
qkd = QKDService()
key_data = qkd.request_key(256)
qkd_key = bytes.fromhex(key_data['key_material'])

# Encrypt
plaintext = b"Top secret message"
encrypted = hybrid_encrypt(plaintext, qkd_key)

print(f"Plaintext: {plaintext}")
print(f"Ciphertext: {encrypted['ciphertext'][:50]}...")
print(f"Algorithm: {encrypted['algorithm']}")

# Verify ciphertext is different from plaintext
assert encrypted['ciphertext'] != plaintext.hex()

# Decrypt
decrypted = hybrid_decrypt(encrypted, qkd_key)
print(f"Decrypted: {decrypted}")

# Verify decryption worked
assert decrypted == plaintext
print("✅ Encryption test passed!")

# Test that wrong key fails
wrong_key = os.urandom(32)
try:
    hybrid_decrypt(encrypted, wrong_key)
    print("❌ ERROR: Decryption with wrong key should fail!")
except Exception as e:
    print(f"✅ Correct: Wrong key failed with {type(e).__name__}")
```

### Test DKIM Signing

```bash
# Send test email
curl -X POST \
  'http://localhost:8000/api/v1/emails/' \
  -H 'Content-Type: application/json' \
  -b cookies.txt \
  -d '{
    "to_addresses": ["external@gmail.com"],
    "subject": "DKIM Test",
    "body_text": "Testing DKIM signatures",
    "encrypt": false
  }'

# Wait for delivery and check headers
# The received email should have DKIM-Signature header
# Verify at https://mxtoolbox.com/dkim.aspx
```

### Test Authentication & Authorization

```python
# Test unauthorized access
import requests

# Try to access API without authentication
response = requests.get('http://localhost:8000/api/v1/emails/')
assert response.status_code == 403, "Should require authentication"

# Try to access another user's email
session = requests.Session()
session.post('http://localhost:8000/api-auth/login/', data={
    'username': 'alice',
    'password': 'testpass123'
})

# Get Bob's email ID
session_bob = requests.Session()
session_bob.post('http://localhost:8000/api-auth/login/', data={
    'username': 'bob',
    'password': 'testpass123'
})

response = session_bob.get('http://localhost:8000/api/v1/emails/')
bob_emails = response.json()['results']

if bob_emails:
    bob_email_id = bob_emails[0]['id']

    # Try to access with Alice's session
    response = session.get(f'http://localhost:8000/api/v1/emails/{bob_email_id}/')
    assert response.status_code == 404, "Should not be able to access other user's email"

print("✅ Authorization test passed!")
```

---

## Troubleshooting

### Common Issues and Solutions

**Issue 1: Emails not being sent**

```bash
# Check Celery worker is running
celery -A qutemail inspect active

# Check queue
python manage.py shell
```

```python
from mail.models import EmailQueue
pending = EmailQueue.objects.filter(is_locked=False)
print(f"Pending emails: {pending.count()}")

# Check for locked entries
locked = EmailQueue.objects.filter(is_locked=True)
print(f"Locked emails: {locked.count()}")

# Unlock stale entries
from mail.tasks import cleanup_old_queue_entries
result = cleanup_old_queue_entries.delay(hours=1)
print(result.get())
```

**Issue 2: Emails not being received**

```bash
# Check Dovecot is running
docker-compose ps dovecot

# Check mailbox exists
docker-compose exec dovecot doveadm mailbox list -u alice@qutemail.local

# Check mail directory
docker-compose exec dovecot ls -la /var/mail/vhosts/qutemail.local/alice/
```

**Issue 3: QKD encryption failing**

```python
# Test QKD service
from qkd.services import QKDService

qkd = QKDService()
try:
    result = qkd.request_key(256)
    print(f"QKD working: {result}")
except Exception as e:
    print(f"QKD error: {e}")

# Check simulator mode
from django.conf import settings
print(f"Simulator mode: {settings.QKD_SIMULATOR_MODE}")
```

**Issue 4: DKIM signing not working**

```bash
# Check OpenDKIM is running
docker-compose ps opendkim

# Check DKIM keys exist
ls -la config/opendkim/keys/

# Test DKIM signing
docker-compose exec opendkim opendkim-testkey -d qutemail.local -s default

# Check Postfix can reach OpenDKIM
docker-compose exec postfix telnet opendkim 8891
```

### Debug Logging

Enable debug logging in Django:

```python
# qutemail/settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'mail': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### Health Check Script

```bash
#!/bin/bash
# healthcheck.sh

echo "=== QtEmail Health Check ==="

# Check Django
echo "1. Django server..."
curl -s http://localhost:8000/api/v1/emails/ > /dev/null && echo "✅ Django OK" || echo "❌ Django FAIL"

# Check Redis
echo "2. Redis..."
redis-cli ping > /dev/null && echo "✅ Redis OK" || echo "❌ Redis FAIL"

# Check PostgreSQL
echo "3. PostgreSQL..."
pg_isready -U qutemail_user > /dev/null && echo "✅ PostgreSQL OK" || echo "❌ PostgreSQL FAIL"

# Check Celery
echo "4. Celery worker..."
celery -A qutemail inspect active > /dev/null && echo "✅ Celery OK" || echo "❌ Celery FAIL"

# Check Postfix
echo "5. Postfix..."
docker-compose exec -T postfix postqueue -p > /dev/null && echo "✅ Postfix OK" || echo "❌ Postfix FAIL"

# Check Dovecot
echo "6. Dovecot..."
docker-compose exec -T dovecot doveadm who > /dev/null && echo "✅ Dovecot OK" || echo "❌ Dovecot FAIL"

# Check OpenDKIM
echo "7. OpenDKIM..."
docker-compose ps opendkim | grep -q "running" && echo "✅ OpenDKIM OK" || echo "❌ OpenDKIM FAIL"

echo "=== Health Check Complete ==="
```

Run health check:

```bash
chmod +x healthcheck.sh
./healthcheck.sh
```

---

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: QtEmail Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: qutemail_test
          POSTGRES_USER: qutemail_user
          POSTGRES_PASSWORD: qutemail_pass
        ports:
          - 5432:5432

      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run migrations
        run: |
          python manage.py migrate
        env:
          DATABASE_URL: postgresql://qutemail_user:qutemail_pass@localhost:5432/qutemail_test

      - name: Run tests
        run: |
          python manage.py test
        env:
          DATABASE_URL: postgresql://qutemail_user:qutemail_pass@localhost:5432/qutemail_test
          REDIS_URL: redis://localhost:6379/0
```

---

This comprehensive testing guide covers all aspects of the QtEmail system. Start with unit tests, move to integration tests, and finally perform end-to-end testing to ensure everything works correctly!
