# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QtEmail Backend is a quantum-secured email system that uses Quantum Key Distribution (QKD) based on the ETSI GS QKD 014 standard. The backend provides a Django REST API for sending and receiving encrypted emails using quantum-generated keys.

## Development Commands

### Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Start infrastructure services
docker-compose up -d db redis

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Running the Application
```bash
# Start Django development server
python manage.py runserver

# Start Celery worker (in separate terminal)
celery -A qutemail worker -l info

# Start Celery beat scheduler (in separate terminal)
celery -A qutemail beat -l info

# Or start all services with Docker
docker-compose up --build
```

### Testing
```bash
# Run all tests
python manage.py test

# Run tests for specific app
python manage.py test apps.qkd
python manage.py test apps.mail
python manage.py test apps.crypto

# Run specific test class or method
python manage.py test apps.qkd.tests.TestQKDService
python manage.py test apps.qkd.tests.TestQKDService.test_request_key
```

### Database Operations
```bash
# Create new migration after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Rollback migration
python manage.py migrate app_name migration_name

# Open Django shell
python manage.py shell
```

## Architecture

### Core Components

The system is organized into five main Django apps under the `apps/` directory:

1. **apps/accounts/** - User authentication and profile management
2. **apps/mail/** - Email composition, inbox, and encryption orchestration
3. **apps/qkd/** - QKD integration and BB84 simulator
4. **apps/crypto/** - Cryptographic utilities (AES-GCM, HKDF, OTP)
5. **apps/infra/** - Infrastructure clients (SMTP, IMAP, storage)

### QKD Integration

The QKD subsystem has two operational modes controlled by `QKD_SIMULATOR_MODE` in settings:

**Simulator Mode (Development):**
- Uses `apps/qkd/simulator.py` which implements BB84 protocol
- No external QKD hardware required
- Generates key pairs for testing

**Production Mode:**
- Uses `apps/qkd/km_client.py` to communicate with ETSI GS QKD 014 compliant KM
- Implements three main operations:
  - `get_key()` - Request new encryption keys via POST to `/api/v1/keys/{sae_id}/enc_keys`
  - `get_key_with_id()` - Retrieve decryption keys via POST to `/api/v1/keys/{sae_id}/dec_keys`
  - `get_status()` - Check QKD system status via GET to `/api/v1/keys/{sae_id}/status`

The `QKDService` class in `apps/qkd/services.py` provides a unified interface that automatically switches between simulator and production modes.

### Email Processing Flow

1. **Sending encrypted email** (`apps/mail/tasks.py:send_encrypted_email`):
   - Request QKD key via `QKDService.request_key()`
   - Encrypt email body using `crypto.utils.hybrid_encrypt()` with the QKD key
   - The hybrid encryption uses HKDF to derive AES-256 key from QKD key material
   - Send via SMTP with encrypted payload and key ID

2. **Receiving encrypted email** (`apps/mail/tasks.py:fetch_and_decrypt_emails`):
   - Fetch emails via IMAP
   - Identify encrypted emails by `[QKD-ENCRYPTED]` subject prefix
   - Extract key_id from email body
   - Retrieve key using `QKDService.get_key_by_id()`
   - Decrypt using `crypto.utils.hybrid_decrypt()`

### Cryptographic Architecture

The system uses a hybrid encryption approach (`apps/crypto/utils.py`):

- **HKDF (HMAC-based Key Derivation)**: Derives AES keys from QKD key material
- **AES-256-GCM**: Provides authenticated encryption of email content
- **One-Time Pad (OTP)**: Available for maximum security when key material is abundant

The `derive_key()` function uses context-specific info strings (e.g., `b'email-encryption'`) to ensure keys are domain-separated.

### Celery Task Processing

Celery is configured in `qutemail/celery.py` and uses Redis as both broker and result backend. Tasks are defined in `apps/mail/tasks.py`:

- `send_encrypted_email` - Asynchronous email sending with QKD encryption
- `fetch_and_decrypt_emails` - Asynchronous email retrieval and decryption
- `process_incoming_mail` - Periodic task placeholder for scheduled mail processing

To add scheduled tasks, configure Celery Beat schedules in `qutemail/settings.py`.

### Settings Configuration

The project uses `python-decouple` for environment-based configuration. Key settings in `qutemail/settings.py`:

- `sys.path.insert(0, str(BASE_DIR / 'apps'))` - Apps are importable directly (e.g., `from qkd.services import QKDService`)
- Apps use DRF with session authentication by default
- CORS is configured for `localhost:3000` (frontend development)
- Database defaults to SQLite but uses PostgreSQL via `DATABASE_URL` in Docker

## Important Implementation Details

### QKD Key Management
- Each QKD key should ideally be used only once (one-time pad principle)
- Keys are identified by unique `key_id` strings
- In simulator mode, keys are stored in `BB84Simulator.key_store` dict
- In production, keys come from external KM and should be confirmed/deleted after use

### ETSI GS QKD 014 Compliance
- SAE (Secure Application Entity) ID identifies the application to the KM
- Key requests specify size in bits (typically 256)
- The standard defines REST endpoints for enc_keys (encryption) and dec_keys (decryption)
- See `docs/ETSI_QKD_014_integration.md` for complete protocol documentation

### Email Format
Encrypted emails use a structured text format in the body:
```
[ENCRYPTED MESSAGE]
Key ID: <key_id>
Ciphertext: <hex_encoded_ciphertext>
Nonce: <hex_encoded_nonce>
Tag: <hex_encoded_auth_tag>
```

This format is parsed in `fetch_and_decrypt_emails` to extract decryption parameters.

## Configuration Files

- `.env` - Local environment variables (copy from `.env.example`)
- `requirements.txt` - Python dependencies
- `docker-compose.yml` - Infrastructure services (PostgreSQL, Redis, Celery)
- `Dockerfile` - Application container definition

## Database Schema

The project uses Django ORM. Model definitions are in each app's `models.py` file. After modifying models, always run `python manage.py makemigrations` then `python manage.py migrate`.
