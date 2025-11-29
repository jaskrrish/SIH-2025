# SMTP Server Implementation Status

**Project**: QutEmail Backend - Production-Ready SMTP Server
**Date**: 2025-11-29
**Status**: Phase 1-7 Complete (64% Done)

---

## 📊 Implementation Progress

**Completed**: 7/11 phases ✅
**Remaining**: 4/11 phases 🔄
**Overall Progress**: 64%

---

## ✅ COMPLETED IMPLEMENTATION

### Phase 1: Dependencies (COMPLETED ✅)

**File Modified**: `requirements.txt`

**Added Dependencies**:
```python
# SMTP Server
aiosmtpd==1.4.4              # Async SMTP server framework
email-validator==2.1.0        # Email address validation

# DNS and Email Authentication
dnspython==2.4.2             # DNS queries for MX records
dkimpy==1.1.5                # DKIM signing and verification
pyspf==2.0.14                # SPF record validation
```

**What This Enables**:
- Async SMTP server using aiosmtpd
- Email authentication (DKIM, SPF)
- Email validation

---

### Phase 2: Database Models (COMPLETED ✅)

**File Created/Modified**: `apps/mail/models.py`, `apps/mail/admin.py`

**Models Created**:

#### 1. **Mailbox Model**
```python
class Mailbox(models.Model):
    user = OneToOneField(User)           # Links to Django user
    email_address = EmailField(unique=True)  # user@yourdomain.com
    quota_bytes = BigIntegerField(default=5GB)
    used_bytes = BigIntegerField(default=0)
    created_at, updated_at = DateTimeFields
```

**Features**:
- One mailbox per Django user
- Quota management (default 5GB)
- Automatic quota tracking

#### 2. **Email Model**
```python
class Email(models.Model):
    mailbox = ForeignKey(Mailbox)
    message_id = CharField(unique=True)
    from_address = EmailField()
    to_addresses = JSONField()
    subject = CharField(max_length=998)
    body_plain = TextField()
    body_html = TextField(null=True)

    # QKD Encryption Fields (Internal Only)
    is_internal = BooleanField(default=False)
    qkd_key_id = CharField(null=True)
    qkd_ciphertext = TextField(null=True)
    qkd_nonce = CharField(null=True)
    qkd_auth_tag = CharField(null=True)

    # Metadata
    folder = CharField(default='INBOX')  # INBOX, Sent, Drafts, etc.
    is_read = BooleanField(default=False)
    is_flagged = BooleanField(default=False)
    size_bytes = IntegerField()
    received_at = DateTimeField(auto_now_add=True)
```

**Features**:
- Full email storage with QKD encryption support
- Automatic mailbox quota updates
- Indexed for performance (mailbox, received_at, message_id)
- Folder organization (INBOX, Sent, Trash, etc.)

#### 3. **EmailAttachment Model**
```python
class EmailAttachment(models.Model):
    email = ForeignKey(Email)
    filename = CharField(max_length=255)
    content_type = CharField(max_length=100)
    size_bytes = IntegerField()
    storage_path = CharField(max_length=500)
    is_inline = BooleanField(default=False)
    content_id = CharField(null=True)  # For inline images
```

**Features**:
- Separate attachment storage
- Support for inline images
- File size tracking

#### 4. **EmailDeliveryStatus Model**
```python
class EmailDeliveryStatus(models.Model):
    email = ForeignKey(Email)
    recipient = EmailField()
    status = CharField(choices=['pending', 'sent', 'failed', 'bounced', 'deferred'])
    attempts = IntegerField(default=0)
    next_retry_at = DateTimeField(null=True)
    error_message = TextField()
    smtp_response = TextField()
    delivered_at = DateTimeField(null=True)
```

**Features**:
- Track delivery status for external emails
- Retry scheduling
- SMTP response logging
- Delivery history

**Admin Interface**: All models registered with comprehensive admin views

---

### Phase 3: SMTP Server Core (COMPLETED ✅)

**File Created**: `apps/infra/smtp_server.py`

**Architecture**:

```
┌─────────────────────────────────────────────────────┐
│           SMTPServerManager                         │
├─────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌───────────┐        │
│  │   MTA    │  │   MSA    │  │  SMTPS    │        │
│  │ Port 25  │  │ Port 587 │  │ Port 465  │        │
│  └──────────┘  └──────────┘  └───────────┘        │
└─────────────────────────────────────────────────────┘
```

#### Components Implemented:

**1. DjangoAuthenticator**
- Authenticates against Django User model
- Supports LOGIN and PLAIN mechanisms
- Stores user info in session

**2. QutEmailHandler (Base)**
- Handles SMTP DATA command
- Queues emails for async processing via Celery
- Logs all email transactions

**3. AuthenticatedSMTPHandler (MSA)**
- **Ports**: 587 (STARTTLS), 465 (implicit TLS)
- **Authentication**: Required before sending
- **Sender Validation**: Users can only send from their own address
- **Usage**: For authenticated users sending emails

**4. MTAHandler (Mail Transfer Agent)**
- **Port**: 25
- **Authentication**: None (accepts from external servers)
- **Recipient Validation**: Only accepts mail for @yourdomain.com
- **Anti-Relay**: Prevents unauthorized relay
- **Mailbox Verification**: Checks if recipient mailbox exists

**5. SMTPServerManager**
- Manages all server instances
- Graceful start/stop
- Context manager support
- Individual or combined server control

**Security Features**:
- TLS 1.2+ enforcement
- SSL context creation with certificates
- Session-based authentication
- Address validation

---

### Phase 4: Email Processing Service (COMPLETED ✅)

**File Created**: `apps/mail/services.py`

**Class**: `EmailProcessingService`

**Email Flow**:

```
┌───────────────────────────────────────────────────────┐
│         Incoming Email                                │
└────────────────┬──────────────────────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │  Parse MIME    │
        │  Extract Meta  │
        └────────┬───────┘
                 │
                 ▼
        ┌────────────────┐
        │  Is Internal?  │
        └────┬───────┬───┘
             │       │
     Yes ────┘       └──── No
     │                    │
     ▼                    ▼
┌─────────────────┐  ┌──────────────────┐
│ QKD Encryption  │  │ Store Plaintext  │
│ Store Encrypted │  │ or Queue Delivery│
└─────────────────┘  └──────────────────┘
```

**Key Methods**:

#### `process_incoming_email(envelope)`
- Main processing pipeline
- Parses MIME messages
- Routes to internal or external handler

#### `_process_internal_email(...)`
**QKD Encryption Flow**:
1. Request QKD key from QKDService
2. Encrypt body with hybrid_encrypt (HKDF + AES-GCM)
3. Store encrypted for each recipient
4. Process attachments
5. Confirm key usage

**Features**:
- Automatic QKD encryption for internal emails
- Per-recipient storage
- Quota checking before storage

#### `_process_external_email(...)`
**External Email Flow**:
1. Check if recipient is local or external
2. **Local**: Store plaintext in database
3. **External**: Queue for delivery via Celery

**Features**:
- Mixed recipient handling
- External delivery queueing
- Attachment processing

#### `decrypt_email(email_obj)`
- Retrieves QKD key by ID
- Decrypts using hybrid_decrypt
- Returns plaintext body

**Additional Capabilities**:
- MIME multipart parsing
- HTML and plain text extraction
- RFC 2047 header decoding
- Attachment extraction and storage
- Email address parsing

---

### Phase 5: Celery Tasks (COMPLETED ✅)

**File Modified**: `apps/mail/tasks.py`

**Tasks Implemented**:

#### 1. `process_smtp_email(envelope_data)`
```python
@shared_task(bind=True, max_retries=3)
def process_smtp_email(self, envelope_data):
    """Process incoming SMTP email asynchronously"""
```

**Features**:
- Called by SMTP handlers when email received
- Runs EmailProcessingService
- Exponential backoff retry (60s, 120s, 240s)
- Error logging

#### 2. `deliver_external_email(from_addr, to_addr, message_bytes)`
```python
@shared_task(bind=True, max_retries=5)
def deliver_external_email(self, from_addr, to_addr, message_bytes):
    """Deliver email to external SMTP server"""
```

**Features**:
- Outbound email delivery
- Creates EmailDeliveryStatus records
- Retry logic: 5, 10, 20, 40, 80 minutes
- SMTP error tracking
- Delivery confirmation

#### 3. `cleanup_old_emails()`
```python
@shared_task
def cleanup_old_emails():
    """Periodic cleanup based on retention policy"""
```

**Features**:
- Deletes emails older than EMAIL_RETENTION_DAYS
- Should be scheduled with Celery Beat
- Returns count of deleted emails

#### 4. `retry_failed_deliveries()`
```python
@shared_task
def retry_failed_deliveries():
    """Retry deferred deliveries"""
```

**Features**:
- Finds deliveries with status='deferred'
- Re-queues for delivery
- Scheduled task for periodic retry

**Existing Tasks** (kept for backward compatibility):
- `send_encrypted_email` - Legacy encrypted email sending
- `fetch_and_decrypt_emails` - Legacy IMAP fetching

---

### Phase 6: Management Command (COMPLETED ✅)

**File Created**: `apps/mail/management/commands/run_smtp_server.py`

**Usage**:
```bash
# Start all servers (MTA + MSA + SMTPS)
python manage.py run_smtp_server

# Start only MTA (port 25)
python manage.py run_smtp_server --mta-only

# Start only MSA (ports 587/465)
python manage.py run_smtp_server --msa-only
```

**Features**:
- Django management command integration
- Graceful shutdown (SIGINT, SIGTERM)
- Colorized output
- Server status display
- Signal handling for clean exit

**Output Example**:
```
Starting SMTP servers...
Mode: All servers (MTA + MSA)
All SMTP servers started:
  - MTA:   port 25  (receiving external emails)
  - MSA:   port 587 (authenticated submission with STARTTLS)
  - SMTPS: port 465 (authenticated submission with implicit TLS)

SMTP servers are running
Press Ctrl+C to stop
```

---

### Phase 7: Settings Configuration (COMPLETED ✅)

**File Modified**: `qutemail/settings.py`

**New Configuration Sections**:

#### Email Domain
```python
EMAIL_DOMAIN = config('EMAIL_DOMAIN', default='qutemail.com')
```

#### Server Ports
```python
SMTP_SERVER_HOSTNAME = config('SMTP_SERVER_HOSTNAME', default='0.0.0.0')
SMTP_MTA_PORT = config('SMTP_MTA_PORT', default=25, cast=int)
SMTP_MSA_PORT = config('SMTP_MSA_PORT', default=587, cast=int)
SMTP_SMTPS_PORT = config('SMTP_SMTPS_PORT', default=465, cast=int)
```

#### TLS/SSL Certificates
```python
SMTP_TLS_CERT = config('SMTP_TLS_CERT', default='/etc/letsencrypt/live/yourdomain.com/fullchain.pem')
SMTP_TLS_KEY = config('SMTP_TLS_KEY', default='/etc/letsencrypt/live/yourdomain.com/privkey.pem')
```

#### Email Limits
```python
SMTP_MAX_MESSAGE_SIZE = config('SMTP_MAX_MESSAGE_SIZE', default=25 * 1024 * 1024, cast=int)  # 25MB
```

#### Rate Limiting
```python
SMTP_RATE_LIMIT_PER_IP = config('SMTP_RATE_LIMIT_PER_IP', default=100, cast=int)    # per hour
SMTP_RATE_LIMIT_PER_USER = config('SMTP_RATE_LIMIT_PER_USER', default=500, cast=int)  # per hour
```

#### Mailbox Configuration
```python
MAILBOX_DEFAULT_QUOTA_GB = config('MAILBOX_DEFAULT_QUOTA_GB', default=5, cast=int)
```

#### Retention Policy
```python
EMAIL_RETENTION_DAYS = config('EMAIL_RETENTION_DAYS', default=365, cast=int)
```

#### DKIM Configuration
```python
DKIM_SELECTOR = config('DKIM_SELECTOR', default='mail')
DKIM_PRIVATE_KEY_PATH = config('DKIM_PRIVATE_KEY_PATH', default='/etc/dkim/private.key')
```

**All settings use environment variables with sensible defaults**

---

## 🔄 REMAINING TASKS

### Phase 8: Security Features (PENDING 🔄)

**What Needs to Be Done**:

#### 1. Rate Limiter Implementation
**File to Create**: `apps/infra/rate_limiter.py`

```python
class RateLimiter:
    - check_rate_limit(key, limit, window)
    - check_ip_limit(ip_address)
    - check_user_limit(username)
```

**Integration**: Add to SMTP handlers to enforce limits

#### 2. Spam Filter
**File to Create**: `apps/infra/spam_filter.py`

```python
class SpamFilter:
    - check_spf(envelope)         # Verify SPF records
    - verify_dkim(message)        # Verify DKIM signature
    - content_filter(body)        # Basic spam keyword detection
```

#### 3. DKIM Signing
**Enhancement**: Add DKIM signing to outbound emails

#### 4. TLS Certificate Management
**Documentation**: Guide for Let's Encrypt setup

---

### Phase 9: REST API Endpoints (PENDING 🔄)

**File to Create/Modify**: `apps/mail/views.py`, `apps/mail/serializers.py`, `apps/mail/urls.py`

**Endpoints Needed**:

```python
# Email Management
GET    /api/emails/              # List user's emails
GET    /api/emails/{id}/         # Get email detail
GET    /api/emails/{id}/decrypt/ # Decrypt internal email
POST   /api/emails/send/         # Send new email
DELETE /api/emails/{id}/         # Delete email
PATCH  /api/emails/{id}/         # Mark as read/flagged

# Mailbox Management
GET    /api/mailbox/             # Get mailbox info
GET    /api/mailbox/quota/       # Check quota usage

# Attachments
GET    /api/emails/{id}/attachments/        # List attachments
GET    /api/emails/{id}/attachments/{id}/   # Download attachment
```

**Components Needed**:
- Serializers for Email, Mailbox, EmailAttachment
- ViewSets with authentication
- URL routing
- Permission classes

---

### Phase 10: Docker Integration (PENDING 🔄)

**File to Modify**: `docker-compose.yml`

**Service to Add**:

```yaml
services:
  smtp_server:
    build: .
    command: python manage.py run_smtp_server
    ports:
      - "25:25"
      - "587:587"
      - "465:465"
    volumes:
      - ./:/app
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - ./storage:/app/storage
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/qutemail
      - CELERY_BROKER_URL=redis://redis:6379/0
      - EMAIL_DOMAIN=yourdomain.com
    depends_on:
      - db
      - redis
    restart: unless-stopped
```

---

### Phase 11: Documentation (PENDING 🔄)

**Files to Create**:

#### 1. `docs/smtp-server-architecture.md`
- System architecture diagrams
- Email flow diagrams
- QKD integration details
- Component relationships

#### 2. `docs/smtp-server-installation.md`
- Prerequisites
- Step-by-step installation
- Database migration guide
- Initial setup

#### 3. `docs/smtp-server-dns-setup.md`
- MX record configuration
- SPF record setup
- DKIM key generation and DNS
- DMARC policy configuration
- PTR (reverse DNS) setup

#### 4. `docs/smtp-server-production.md`
- TLS certificate setup (Let's Encrypt)
- Security hardening checklist
- Firewall configuration
- Monitoring and logging
- Backup strategies
- Performance tuning

#### 5. `docs/smtp-server-api.md`
- REST API reference
- Authentication guide
- Request/response examples
- Code samples for frontend integration

---

## 🚀 GETTING STARTED

### Prerequisites

```bash
# Python 3.10+
# PostgreSQL 15+
# Redis 7+
```

### Installation Steps

#### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 2. Configure Environment
Create `.env` file:
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/qutemail

# Redis
CELERY_BROKER_URL=redis://localhost:6379/0

# Email Domain
EMAIL_DOMAIN=yourdomain.com

# TLS Certificates (optional for development)
SMTP_TLS_CERT=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
SMTP_TLS_KEY=/etc/letsencrypt/live/yourdomain.com/privkey.pem

# QKD
QKD_SIMULATOR_MODE=True
```

#### 3. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

#### 4. Create Superuser
```bash
python manage.py createsuperuser
```

#### 5. Create Mailboxes
```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
from mail.models import Mailbox

for user in User.objects.all():
    Mailbox.objects.get_or_create(
        user=user,
        email_address=f'{user.username}@yourdomain.com'
    )
```

#### 6. Start Services

**Terminal 1 - Celery Worker**:
```bash
celery -A qutemail worker -l info
```

**Terminal 2 - SMTP Server**:
```bash
python manage.py run_smtp_server
```

**Terminal 3 - Django Dev Server** (for admin):
```bash
python manage.py runserver
```

---

## 📧 TESTING THE SMTP SERVER

### Test Internal Email (QKD Encrypted)

**Using Telnet**:
```bash
telnet localhost 587
EHLO test.com
AUTH LOGIN
# Enter base64(username)
# Enter base64(password)
MAIL FROM:<alice@yourdomain.com>
RCPT TO:<bob@yourdomain.com>
DATA
Subject: Test QKD Email
From: alice@yourdomain.com
To: bob@yourdomain.com

This email will be QKD encrypted!
.
QUIT
```

**Expected Result**:
- Email encrypted with QKD key
- Stored in Bob's mailbox
- Accessible via Django admin or API

### Test External Email Reception

**Send from External SMTP** (e.g., Gmail):
```bash
# Configure Gmail to send to: user@yourdomain.com
# Ensure port 25 is open and DNS MX record points to your server
```

**Expected Result**:
- Email accepted on port 25
- Stored as plaintext (no QKD for external)
- Available in user's mailbox

---

## 📁 FILE STRUCTURE

```
qutemail-backend/
├── apps/
│   ├── mail/
│   │   ├── models.py                    ✅ NEW - Database models
│   │   ├── admin.py                     ✅ MODIFIED - Admin interface
│   │   ├── services.py                  ✅ NEW - Email processing service
│   │   ├── tasks.py                     ✅ MODIFIED - Celery tasks
│   │   └── management/
│   │       └── commands/
│   │           └── run_smtp_server.py   ✅ NEW - Django command
│   │
│   └── infra/
│       ├── smtp_server.py               ✅ NEW - SMTP server core
│       ├── smtp_client.py               (existing)
│       ├── imap_client.py               (existing)
│       └── storage.py                   (existing)
│
├── qutemail/
│   └── settings.py                      ✅ MODIFIED - SMTP config
│
├── requirements.txt                     ✅ MODIFIED - New dependencies
│
└── SMTP_IMPLEMENTATION_STATUS.md        ✅ NEW - This file
```

---

## 🔍 KEY FEATURES IMPLEMENTED

### ✅ Dual-Mode SMTP Server
- **MTA (Port 25)**: Receives emails from external servers
- **MSA (Port 587/465)**: Authenticated user submission

### ✅ QKD Encryption
- Automatic for internal emails (both users @yourdomain.com)
- Uses existing QKDService integration
- Hybrid encryption (HKDF + AES-256-GCM)

### ✅ Database Persistence
- All emails stored in PostgreSQL
- Quota management per user
- Attachment storage via LocalStorageAdapter

### ✅ Async Processing
- Celery-based email processing
- Retry logic for failed deliveries
- Exponential backoff

### ✅ Security
- Django user authentication
- TLS/STARTTLS support
- Sender validation
- Anti-relay protection
- Mailbox verification

---

## 🎯 NEXT IMMEDIATE STEPS

1. **Test the Implementation**:
   ```bash
   # Install dependencies
   pip install -r requirements.txt

   # Run migrations
   python manage.py makemigrations && python manage.py migrate

   # Create test user and mailbox
   python manage.py createsuperuser

   # Start Celery worker
   celery -A qutemail worker -l info

   # Start SMTP server
   python manage.py run_smtp_server
   ```

2. **Send Test Email**:
   - Use telnet to send internal email
   - Check Django admin for stored email
   - Verify QKD encryption fields populated

3. **Complete Remaining Phases**:
   - Phase 8: Security features (rate limiting, spam filter)
   - Phase 9: REST API endpoints
   - Phase 10: Docker integration
   - Phase 11: Documentation

---

## 📊 ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────┐
│                    QutEmail SMTP Server                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  External Senders    ──────────►  MTA (Port 25)             │
│  (Other Mail Servers)              │                         │
│                                    │                         │
│  Authenticated Users ──────────►  MSA (Ports 587/465)       │
│  (Your Users)                      │                         │
│                                    │                         │
│                                    ▼                         │
│                          ┌──────────────────┐               │
│                          │  SMTP Handlers   │               │
│                          │  - Validate      │               │
│                          │  - Authenticate  │               │
│                          └────────┬─────────┘               │
│                                   │                         │
│                                   ▼                         │
│                          ┌──────────────────┐               │
│                          │  Celery Queue    │               │
│                          └────────┬─────────┘               │
│                                   │                         │
│                                   ▼                         │
│                     ┌──────────────────────────┐            │
│                     │ EmailProcessingService   │            │
│                     │                          │            │
│                     │  Internal? ──► QKD Enc  │            │
│                     │  External? ──► Store    │            │
│                     └──────────┬───────────────┘            │
│                                │                            │
│                                ▼                            │
│                     ┌──────────────────┐                    │
│                     │   PostgreSQL     │                    │
│                     │   - Mailboxes    │                    │
│                     │   - Emails       │                    │
│                     │   - Attachments  │                    │
│                     └──────────────────┘                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 💡 IMPORTANT NOTES

### Production Readiness

**Currently Suitable For**:
- ✅ Development and testing
- ✅ Internal network deployment
- ✅ Proof of concept

**Requires for Production**:
- 🔄 Rate limiting implementation
- 🔄 Spam filtering
- 🔄 DKIM signing
- 🔄 Real TLS certificates (Let's Encrypt)
- 🔄 DNS configuration (MX, SPF, DKIM, DMARC)
- 🔄 Monitoring and logging
- 🔄 Firewall configuration

### Security Considerations

**Implemented**:
- ✅ Authentication required for MSA
- ✅ Sender address validation
- ✅ Anti-relay protection
- ✅ TLS/STARTTLS support
- ✅ QKD encryption for internal emails

**Pending**:
- 🔄 Rate limiting (DoS protection)
- 🔄 SPF/DKIM verification
- 🔄 Content filtering
- 🔄 Attachment scanning

---

## 🤝 SUPPORT

For issues or questions:
1. Check this status document
2. Review the implementation plan: `/Users/jaskrrishsingh/.claude/plans/staged-plotting-puffin.md`
3. Check Django admin for email storage
4. Review Celery logs for async processing

---

**Last Updated**: 2025-11-29
**Implementation Version**: 1.0.0-beta
**Django Version**: 5.0.1
**aiosmtpd Version**: 1.4.4
