# QtEmail Backend Architecture

## System Overview

QtEmail is a quantum-secured email system that combines traditional email infrastructure (Postfix, Dovecot, OpenDKIM) with Quantum Key Distribution (QKD) for end-to-end encryption.

## Architecture Diagram

```mermaid
flowchart TB
    subgraph Client["Client Applications"]
        WebUI[Web UI]
        MobileApp[Mobile App]
        API_Client[API Client]
    end

    subgraph Django["Django Application Layer"]
        subgraph API["REST API Layer"]
            EmailViewSet[EmailViewSet]
            AttachmentViewSet[AttachmentViewSet]
            SettingsViewSet[SettingsViewSet]
            LabelViewSet[LabelViewSet]
        end

        subgraph Services["Service Layer"]
            EmailSendService[EmailSendService]
            EmailReceiveService[EmailReceiveService]
            QKDService[QKDService]
        end

        subgraph Models["Data Layer"]
            Email[Email Model]
            Attachment[Attachment Model]
            EmailQueue[EmailQueue Model]
            EmailLog[EmailLog Model]
            UserEmailSettings[UserEmailSettings Model]
            Label[Label Model]
        end
    end

    subgraph Workers["Background Workers"]
        CeleryWorker[Celery Worker]
        CeleryBeat[Celery Beat Scheduler]

        subgraph Tasks["Celery Tasks"]
            ProcessQueue[process_email_queue]
            SendEmail[send_single_email]
            FetchEmails[fetch_incoming_emails]
            Cleanup[cleanup_old_logs]
        end
    end

    subgraph Infrastructure["Mail Infrastructure"]
        Postfix[Postfix MTA<br/>Port 25, 587, 465]
        OpenDKIM[OpenDKIM<br/>Port 8891]
        Dovecot[Dovecot IMAP/LMTP<br/>Port 143, 993, 24]
        Maildir[Maildir Storage<br/>/var/mail/vhosts]
    end

    subgraph Crypto["Cryptography Layer"]
        QKDSimulator[BB84 Simulator]
        QKDKM[QKD Key Manager<br/>ETSI GS QKD 014]
        HKDF[HKDF Key Derivation]
        AES[AES-256-GCM]
    end

    subgraph Storage["Data Storage"]
        PostgreSQL[(PostgreSQL<br/>Main Database)]
        Redis[(Redis<br/>Celery Broker)]
        Mailboxes[(Maildir<br/>Email Storage)]
    end

    Client --> API
    API --> Services
    Services --> Models
    Services --> QKDService
    Models --> PostgreSQL

    Services --> CeleryWorker
    CeleryBeat --> Tasks
    Tasks --> CeleryWorker
    CeleryWorker --> Redis

    CeleryWorker --> Postfix
    CeleryWorker --> Dovecot

    Postfix --> OpenDKIM
    OpenDKIM --> Dovecot
    Dovecot --> Mailboxes

    QKDService --> QKDSimulator
    QKDService --> QKDKM
    QKDService --> HKDF
    HKDF --> AES

    style QKDService fill:#9f6
    style Postfix fill:#69f
    style Dovecot fill:#69f
    style OpenDKIM fill:#69f
```

## Component Details

### 1. REST API Layer

**Purpose**: Provides RESTful endpoints for email management

**Components**:
- **EmailViewSet**: CRUD operations, reply, forward, bulk actions
- **AttachmentViewSet**: Upload, download, list attachments
- **SettingsViewSet**: User email settings management
- **LabelViewSet**: Email tagging and organization

**Technology**: Django REST Framework (DRF)

**Endpoints**: `/api/v1/emails/`, `/api/v1/attachments/`, `/api/v1/settings/`, `/api/v1/labels/`

### 2. Service Layer

**Purpose**: Business logic and orchestration

**EmailSendService** (`apps/mail/services.py:28-311`):
- Composes new emails
- Encrypts with QKD (optional)
- Queues for async sending
- Handles attachments
- Sends via SMTP

**EmailReceiveService** (`apps/mail/services.py:314-481`):
- Fetches emails via IMAP
- Parses RFC822 messages
- Decrypts QKD-encrypted emails
- Stores in database
- Manages attachments

**QKDService** (`apps/qkd/services.py:10-117`):
- Requests quantum keys
- Retrieves keys by ID
- Confirms key usage
- Switches between simulator and production KM

### 3. Background Workers

**Celery Tasks** (`apps/mail/tasks.py`):

1. **process_email_queue** (every 30s)
   - Dequeues pending emails
   - Locks entries to prevent duplicates
   - Delegates to send_single_email

2. **send_single_email**
   - Sends individual email
   - Implements retry logic (max 5 attempts)
   - Exponential backoff on failure
   - Updates email status

3. **fetch_incoming_emails** (every 60s)
   - Polls IMAP for all users
   - Incremental fetch using UID
   - Calls EmailReceiveService

4. **cleanup_old_logs** (daily at 3 AM)
   - Deletes logs older than 90 days
   - Prevents database bloat

5. **cleanup_old_queue_entries** (every 6 hours)
   - Unlocks stale locked entries
   - Handles crashed workers

### 4. Mail Infrastructure

**Postfix** (`config/postfix/`):
- Receives mail on port 25 (SMTP)
- Accepts authenticated submissions on port 587
- Relays through OpenDKIM
- Delivers to Dovecot via LMTP

**OpenDKIM** (`config/opendkim/`):
- Signs all outgoing mail
- Uses RSA-2048 keys
- Selector: `default`
- Domain: `qutemail.local`

**Dovecot** (`config/dovecot/`):
- IMAP server on ports 143 (plain) and 993 (SSL)
- LMTP server on port 24
- Maildir format storage
- SASL authentication for Postfix

### 5. Data Models

**Email** (`apps/mail/models.py:14-207`):
```python
- message_id: Unique RFC822 ID
- folder: inbox/sent/drafts/trash/spam/archive
- subject, from_address, to_addresses, cc_addresses, bcc_addresses
- body_text, body_html
- is_encrypted, qkd_key_id, encryption_nonce, encryption_tag
- is_read, is_starred
- status: draft/queued/sending/sent/failed/received
- size, has_attachments
- Relationships: attachments, labels, logs, queue
```

**Attachment** (`apps/mail/models.py:210-272`):
```python
- filename, content_type, size
- data: BinaryField (stores in PostgreSQL)
- checksum: SHA-256
- content_id, is_inline (for embedded images)
```

**EmailQueue** (`apps/mail/models.py:275-372`):
```python
- email: ForeignKey to Email
- priority: 1-10 (higher = more urgent)
- attempts, max_attempts
- scheduled_at, next_retry_at
- is_locked, locked_by, locked_at
- Methods: lock(), unlock()
```

**EmailLog** (`apps/mail/models.py:375-452`):
```python
- email: ForeignKey to Email
- event_type: queued/sent/failed/encrypted/decrypted/retry
- message, metadata
- error_message, traceback
- created_at
```

**UserEmailSettings** (`apps/mail/models.py:455-537`):
```python
- user: OneToOne to User
- email_address: user@qutemail.local
- display_name
- smtp_password_encrypted, imap_password_encrypted
- enable_qkd_encryption
- auto_fetch_interval
- storage_quota_mb, storage_used_mb
- last_sync_at
- Methods: get_storage_usage_percentage(), update_storage_usage()
```

## Data Flow Diagrams

### Outbound Email Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant EmailSendService
    participant QKDService
    participant EmailQueue
    participant CeleryWorker
    participant Postfix
    participant OpenDKIM
    participant Dovecot
    participant Recipient

    User->>API: POST /api/v1/emails/
    API->>EmailSendService: compose_email()

    alt Encryption Enabled
        EmailSendService->>QKDService: request_key()
        QKDService-->>EmailSendService: {key_id, key_material}
        EmailSendService->>EmailSendService: encrypt_body(AES-256-GCM)
    end

    EmailSendService->>EmailQueue: create(email, priority=5)
    EmailSendService-->>User: {email_id, status: "queued"}

    Note over CeleryWorker: Every 30 seconds
    CeleryWorker->>EmailQueue: get unlocked entries
    EmailQueue-->>CeleryWorker: [pending emails]
    CeleryWorker->>EmailQueue: lock(worker_id)

    CeleryWorker->>Postfix: SMTP send (port 587)
    Postfix->>OpenDKIM: Sign with DKIM
    OpenDKIM->>Dovecot: Deliver via LMTP
    Dovecot->>Dovecot: Save to Maildir
    Dovecot->>Recipient: Forward to recipient

    CeleryWorker->>EmailQueue: delete (on success)
    CeleryWorker->>API: Update email.status = "sent"
```

### Inbound Email Flow

```mermaid
sequenceDiagram
    participant Sender
    participant Postfix
    participant Dovecot
    participant Maildir
    participant CeleryWorker
    participant IMAPClient
    participant EmailReceiveService
    participant MailParser
    participant QKDService
    participant Database
    participant User

    Sender->>Postfix: SMTP delivery
    Postfix->>Dovecot: LMTP delivery
    Dovecot->>Maildir: Save to /var/mail/vhosts/

    Note over CeleryWorker: Every 60 seconds
    CeleryWorker->>IMAPClient: fetch_new_emails(last_uid)
    IMAPClient->>Dovecot: UID SEARCH/FETCH
    Dovecot->>Maildir: Read messages
    Dovecot-->>IMAPClient: [raw RFC822 messages]

    IMAPClient-->>EmailReceiveService: [{uid, raw}]

    loop Each Email
        EmailReceiveService->>MailParser: parse(raw_bytes)
        MailParser-->>EmailReceiveService: {headers, body, attachments, qkd_metadata}

        alt QKD Encrypted
            EmailReceiveService->>QKDService: get_key_by_id(key_id)
            QKDService-->>EmailReceiveService: {key_material}
            EmailReceiveService->>EmailReceiveService: decrypt_body(AES-256-GCM)
        end

        EmailReceiveService->>Database: create Email
        EmailReceiveService->>Database: create Attachments
        EmailReceiveService->>Database: create EmailLog
    end

    EmailReceiveService-->>User: Emails available via API
```

### QKD Encryption Flow

```mermaid
sequenceDiagram
    participant Sender
    participant QKDService
    participant BB84Simulator
    participant HKDF
    participant AES
    participant Email
    participant Recipient
    participant QKDServiceRecv

    Note over Sender: Outbound Flow
    Sender->>QKDService: request_key(256 bits)

    alt Simulator Mode
        QKDService->>BB84Simulator: generate_key_pair()
        BB84Simulator-->>QKDService: {key_id, alice_key, bob_key}
    else Production Mode
        QKDService->>QKDServiceRecv: GET /api/v1/keys/{sae_id}/enc_keys
        QKDServiceRecv-->>QKDService: {key_id, key_material}
    end

    QKDService-->>Sender: {key_id, key_material}

    Sender->>HKDF: derive_key(qkd_key, info="email-encryption")
    HKDF-->>Sender: aes_key (256-bit)

    Sender->>AES: encrypt(plaintext, aes_key)
    AES-->>Sender: {ciphertext, nonce, tag}

    Sender->>Email: Store {key_id, ciphertext, nonce, tag}
    Email->>Recipient: Send encrypted email

    Note over Recipient: Inbound Flow
    Recipient->>QKDServiceRecv: get_key_by_id(key_id)

    alt Simulator Mode
        QKDServiceRecv->>BB84Simulator: get_key(key_id)
        BB84Simulator-->>QKDServiceRecv: bob_key
    else Production Mode
        QKDServiceRecv->>QKDService: POST /api/v1/keys/{sae_id}/dec_keys
        QKDService-->>QKDServiceRecv: {key_material}
    end

    QKDServiceRecv-->>Recipient: {key_material}

    Recipient->>HKDF: derive_key(qkd_key, info="email-encryption")
    HKDF-->>Recipient: aes_key (256-bit)

    Recipient->>AES: decrypt(ciphertext, aes_key, nonce, tag)
    AES-->>Recipient: plaintext

    Recipient->>QKDServiceRecv: confirm_key(key_id)
```

## Technology Stack

### Backend Framework
- **Django 5.0.1**: Web framework
- **Django REST Framework 3.14.0**: REST API
- **PostgreSQL 15**: Primary database
- **Redis 7**: Celery broker and cache

### Asynchronous Processing
- **Celery 5.3.4**: Task queue
- **Celery Beat**: Periodic task scheduler

### Mail Infrastructure
- **Postfix**: SMTP MTA
- **Dovecot**: IMAP server and LDA
- **OpenDKIM**: DKIM signing

### Cryptography
- **cryptography 41.0.7**: Python crypto library
- **HKDF**: Key derivation function
- **AES-256-GCM**: Authenticated encryption
- **QKD**: Quantum key distribution

### Email Processing
- **mail-parser 3.15.0**: RFC822 parsing
- **imaplib**: IMAP client
- **smtplib**: SMTP client

### Deployment
- **Docker & Docker Compose**: Containerization
- **Gunicorn 21.2.0**: WSGI HTTP server

## Security Architecture

### Authentication & Authorization
- Django session-based authentication
- User-based permission model
- Each user can only access their own emails

### Encryption Layers

1. **Transport Layer**: TLS/SSL for SMTP/IMAP
2. **Storage Layer**: Encrypted passwords in database
3. **Content Layer**: QKD-based email body encryption
4. **Signing Layer**: DKIM signatures on all outbound mail

### QKD Security Model

```mermaid
graph LR
    A[QKD Key Generation] --> B[HKDF Key Derivation]
    B --> C[AES-256-GCM Encryption]
    C --> D[Authenticated Ciphertext]

    A --> E[One-Time Use]
    E --> F[Key Confirmation]
    F --> G[Key Deletion]

    style A fill:#9f6
    style E fill:#f96
```

**Key Properties**:
- **One-Time Use**: Each key used only once
- **Information-Theoretic Security**: QKD provides unconditional security
- **Forward Secrecy**: Past communications secure even if future keys compromised
- **Authentication**: AES-GCM provides authenticated encryption

### Threat Model

**Protected Against**:
- ✅ Man-in-the-middle attacks (QKD + TLS)
- ✅ Email spoofing (DKIM signatures)
- ✅ Passive eavesdropping (QKD encryption)
- ✅ Brute force attacks (Quantum-secure keys)
- ✅ SQL injection (Django ORM)
- ✅ XSS attacks (DRF serialization)

**Not Protected Against**:
- ❌ Endpoint compromise (if attacker controls sender/receiver device)
- ❌ Social engineering
- ❌ Physical access to servers
- ❌ Quantum computer attacks on RSA (DKIM keys should be rotated)

## Performance Characteristics

### Throughput
- **Queue Processing**: 10 emails per batch, every 30 seconds = ~1,200 emails/hour
- **IMAP Polling**: 60-second intervals, 50 emails per fetch
- **API Requests**: Limited by Django/DRF (typically 100-1000 req/s)

### Latency
- **Email Composition**: <100ms
- **QKD Key Request**: 10-50ms (simulator), 100-500ms (production KM)
- **Encryption**: ~1ms per email
- **Queue → Sent**: 30-90 seconds (queue interval + SMTP delivery)
- **Inbox → API**: 60-120 seconds (IMAP polling interval)

### Scalability
- **Horizontal Scaling**: Add more Celery workers
- **Vertical Scaling**: Increase worker concurrency
- **Database Scaling**: PostgreSQL read replicas
- **Queue Scaling**: Redis Cluster

### Resource Usage
- **Memory**: ~500MB per Celery worker
- **CPU**: Low (I/O bound workload)
- **Disk**: Depends on email volume (avg 50KB/email)
- **Network**: Depends on email size and frequency

## Configuration

### Environment Variables

See `.env.example` for full configuration options.

**Critical Settings**:
```bash
# QKD Mode
QKD_SIMULATOR_MODE=True  # False for production QKD KM

# Mail Server
SMTP_HOST=localhost
SMTP_PORT=587
IMAP_HOST=localhost
IMAP_PORT=993

# Celery Schedules
# Defined in qutemail/settings.py CELERY_BEAT_SCHEDULE
```

### Celery Beat Schedule

```python
CELERY_BEAT_SCHEDULE = {
    'process-email-queue': {
        'task': 'mail.tasks.process_email_queue',
        'schedule': 30.0,  # Every 30 seconds
    },
    'fetch-incoming-emails': {
        'task': 'mail.tasks.fetch_incoming_emails',
        'schedule': 60.0,  # Every 60 seconds
    },
    'cleanup-old-logs': {
        'task': 'mail.tasks.cleanup_old_logs',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
        'kwargs': {'days': 90},
    },
    'cleanup-stale-queue-entries': {
        'task': 'mail.tasks.cleanup_old_queue_entries',
        'schedule': crontab(hour='*/6', minute=0),  # Every 6 hours
        'kwargs': {'hours': 24},
    },
}
```

## Monitoring & Logging

### Log Locations
- **Django**: Console or configured log file
- **Celery**: Console with `-l info` flag
- **Postfix**: `/var/log/postfix/postfix.log`
- **Dovecot**: `/var/log/dovecot/dovecot.log`
- **OpenDKIM**: Syslog

### Metrics to Monitor
- Queue depth (EmailQueue.count)
- Failed emails (Email.status = 'failed')
- IMAP sync lag (time since last_sync_at)
- Storage usage (UserEmailSettings.storage_used_mb)
- Celery worker health
- Redis connection status
- PostgreSQL query performance

### Health Checks
```bash
# Django
curl http://localhost:8000/api/v1/emails/

# Celery
celery -A qutemail inspect active

# Redis
redis-cli ping

# PostgreSQL
pg_isready -U qutemail_user

# Postfix
postqueue -p

# Dovecot
doveadm who
```

## Backup Strategy

### Database Backups
```bash
# PostgreSQL dump
pg_dump -U qutemail_user qutemail_db > backup.sql

# Restore
psql -U qutemail_user qutemail_db < backup.sql
```

### Maildir Backups
```bash
# Rsync mailboxes
rsync -avz /var/mail/vhosts/ /backup/mailboxes/
```

### Configuration Backups
```bash
# Backup all configs
tar -czf qutemail-config-$(date +%Y%m%d).tar.gz \
  config/ \
  .env \
  docker-compose.yml
```

## Future Enhancements

### Planned Features
- [ ] PGP/GPG integration alongside QKD
- [ ] S/MIME support
- [ ] Email threading and conversation view
- [ ] Full-text search (Elasticsearch)
- [ ] Spam filtering (SpamAssassin)
- [ ] Virus scanning (ClamAV)
- [ ] Webmail interface
- [ ] Mobile push notifications
- [ ] Calendar integration (CalDAV)
- [ ] Contacts sync (CardDAV)

### Performance Optimizations
- [ ] Celery result caching
- [ ] Database query optimization
- [ ] Connection pooling
- [ ] CDN for attachments
- [ ] Message deduplication

### Security Enhancements
- [ ] Rate limiting
- [ ] Two-factor authentication
- [ ] Email encryption at rest
- [ ] Audit logging
- [ ] Security headers (CSP, HSTS)

## References

1. [ETSI GS QKD 014 - Protocol and data format of REST-based key delivery API](https://www.etsi.org/deliver/etsi_gs/QKD/001_099/014/01.01.01_60/gs_QKD014v010101p.pdf)
2. [RFC 5321 - Simple Mail Transfer Protocol](https://tools.ietf.org/html/rfc5321)
3. [RFC 3501 - Internet Message Access Protocol](https://tools.ietf.org/html/rfc3501)
4. [RFC 6376 - DomainKeys Identified Mail (DKIM)](https://tools.ietf.org/html/rfc6376)
5. [RFC 5322 - Internet Message Format](https://tools.ietf.org/html/rfc5322)
