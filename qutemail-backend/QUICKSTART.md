# Quick Start Guide

Get your QtEmail backend up and running in 5 minutes!

## Prerequisites

- Python 3.11+
- Docker Desktop (running)
- Git

## Setup Steps

### 1. Navigate to Project

```bash
cd qutemail-backend
```

### 2. Start Docker Services

```bash
# Start PostgreSQL and Redis
docker compose up -d db redis

# Verify services are running
docker compose ps
```

### 3. Setup Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment

The `.env` file is already created with defaults. No changes needed for local development!

### 5. Initialize Database

```bash
# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser
```

### 6. Start Development Server

**Terminal 1** - Django Server:
```bash
python manage.py runserver
```

**Terminal 2** - Celery Worker:
```bash
celery -A qutemail worker -l info
```

### 7. Access the Application

- Admin Panel: http://localhost:8000/admin
- API Root: http://localhost:8000/api/

## Test the Setup

Run tests to verify everything works:

```bash
python manage.py test
```

Expected output: All tests pass ✅

## Quick Test: QKD Key Generation

Open Django shell:

```bash
python manage.py shell
```

Try generating a quantum key:

```python
from apps.qkd.services import QKDService

# Create QKD service (simulator mode)
qkd = QKDService()

# Request a quantum key
key_data = qkd.request_key(key_size=256)
print(f"Key ID: {key_data['key_id']}")
print(f"Key Size: {key_data['key_size']} bits")
print(f"Source: {key_data['source']}")

# Test encryption
from apps.crypto.utils import hybrid_encrypt, hybrid_decrypt

plaintext = b"Hello Quantum World!"
qkd_key = bytes.fromhex(key_data['key_material'])

encrypted = hybrid_encrypt(plaintext, qkd_key)
decrypted = hybrid_decrypt(encrypted, qkd_key)

print(f"Original: {plaintext}")
print(f"Decrypted: {decrypted}")
assert plaintext == decrypted
print("✅ Encryption/Decryption works!")
```

## Optional: Mail Server for Testing

```bash
./scripts/bootstrap_mailserver.sh
```

Access MailHog UI at: http://localhost:8025

Update `.env`:
```bash
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USE_TLS=False
```

## Troubleshooting

**Docker not starting?**
- Make sure Docker Desktop is running
- Check: `docker ps`

**Database connection error?**
- Wait a few seconds for PostgreSQL to initialize
- Check: `docker compose logs db`

**Import errors?**
- Make sure virtual environment is activated
- Reinstall: `pip install -r requirements.txt`

**Port already in use?**
- Change port: `python manage.py runserver 8001`
- Or stop conflicting service

## Next Steps

1. Read [SETUP_COMPLETE.md](SETUP_COMPLETE.md) for detailed documentation
2. Explore [docs/ETSI_QKD_014_integration.md](docs/ETSI_QKD_014_integration.md)
3. Start building your email models and APIs!

## Useful Commands

```bash
# Django
python manage.py makemigrations    # Create migrations
python manage.py migrate           # Apply migrations
python manage.py createsuperuser   # Create admin user
python manage.py shell             # Interactive shell
python manage.py test              # Run tests

# Docker
docker compose up -d               # Start all services
docker compose down                # Stop all services
docker compose logs -f             # View logs
docker compose ps                  # List services

# Celery
celery -A qutemail worker -l info  # Start worker
celery -A qutemail beat -l info    # Start scheduler
celery -A qutemail inspect active  # View active tasks
```

---

**You're all set! Happy coding! 🚀**
