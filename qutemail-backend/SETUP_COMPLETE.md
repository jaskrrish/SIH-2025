# QtEmail Backend - Setup Complete! 🎉

Your quantum-secured email backend project has been successfully initialized.

## Project Structure

```
qutemail-backend/
├── docker-compose.yml       # Docker services (PostgreSQL, Redis, Celery)
├── Dockerfile              # Docker image for Django app
├── manage.py               # Django management script
├── requirements.txt        # Python dependencies
├── README.md              # Project documentation
├── .env                   # Environment variables (DO NOT COMMIT)
├── .env.example           # Example environment file
├── .gitignore            # Git ignore rules
│
├── qutemail/             # Django project configuration
│   ├── settings.py       # ✓ Configured with PostgreSQL, Redis, Celery
│   ├── urls.py          # URL routing
│   ├── wsgi.py          # WSGI application
│   ├── celery.py        # ✓ Celery configuration
│   └── __init__.py      # ✓ Celery app initialization
│
├── apps/                # Django applications
│   ├── accounts/        # ✓ User authentication & profiles
│   ├── mail/           # ✓ Email operations with Celery tasks
│   │   └── tasks.py    # ✓ Async email sending/receiving
│   ├── qkd/            # ✓ QKD integration
│   │   ├── km_client.py    # ✓ ETSI GS QKD 014 client
│   │   ├── simulator.py    # ✓ BB84 simulator
│   │   └── services.py     # ✓ High-level QKD operations
│   ├── crypto/         # ✓ Cryptographic utilities
│   │   └── utils.py    # ✓ HKDF, AES-GCM, OTP encryption
│   └── infra/          # ✓ Infrastructure clients
│       ├── smtp_client.py  # ✓ SMTP email sending
│       ├── imap_client.py  # ✓ IMAP email fetching
│       └── storage.py      # ✓ Storage adapters
│
├── docs/               # Documentation
│   └── ETSI_QKD_014_integration.md  # ✓ QKD standard docs
│
├── scripts/            # Utility scripts
│   ├── setup.sh               # ✓ Initial setup script
│   └── bootstrap_mailserver.sh # ✓ Dev mail server setup
│
└── tests/              # Test suite
    ├── __init__.py
    └── test_qkd.py     # ✓ QKD and crypto tests
```

## What's Been Configured

### ✅ Core Django Setup
- Django 5.0.1 with Django REST Framework
- PostgreSQL database configuration
- CORS headers for frontend integration
- Environment-based configuration with python-decouple

### ✅ Celery & Redis
- Celery 5.3.4 for asynchronous tasks
- Redis as message broker and result backend
- Celery tasks for encrypted email sending/receiving

### ✅ QKD Implementation
- ETSI GS QKD 014 standard client
- BB84 simulator for development
- High-level QKD service API
- Switchable simulator/production mode

### ✅ Cryptography
- HKDF key derivation
- AES-256-GCM encryption
- One-Time Pad (OTP) support
- Hybrid encryption combining QKD + AES

### ✅ Email Infrastructure
- SMTP client for sending
- IMAP client for receiving
- Encrypted email format
- Storage adapters

### ✅ Docker Infrastructure
- PostgreSQL 15
- Redis 7
- Celery worker & beat containers
- Health checks configured

## Next Steps

### 1. Start Docker Services

First, make sure Docker Desktop is running, then:

```bash
cd qutemail-backend
docker compose up -d db redis
```

This will start PostgreSQL and Redis in Docker containers.

### 2. Run Initial Setup

```bash
./scripts/setup.sh
```

This script will:
- Install Python dependencies
- Run database migrations
- Optionally create a superuser

### 3. Start Development Server

**Option A: Local Development**

Terminal 1 - Django:
```bash
source venv/bin/activate
python manage.py runserver
```

Terminal 2 - Celery Worker:
```bash
source venv/bin/activate
celery -A qutemail worker -l info
```

Terminal 3 - Celery Beat (optional):
```bash
source venv/bin/activate
celery -A qutemail beat -l info
```

**Option B: Full Docker Stack**

```bash
docker compose up --build
```

### 4. Optional: Setup Development Mail Server

For testing email functionality locally:

```bash
./scripts/bootstrap_mailserver.sh
```

This starts MailHog (SMTP server + web UI at http://localhost:8025)

### 5. Access the Application

- Django Admin: http://localhost:8000/admin
- API Root: http://localhost:8000/api/
- MailHog UI: http://localhost:8025 (if running)

## Testing

Run the test suite:

```bash
python manage.py test
```

## Environment Variables

Key settings in `.env`:

```bash
# Django
DEBUG=True
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://qutemail_user:qutemail_pass@localhost:5432/qutemail_db

# QKD
QKD_SIMULATOR_MODE=True  # Set to False for production QKD
QKD_KM_URL=http://localhost:8080

# Email
SMTP_HOST=localhost
SMTP_PORT=1025
```

## Development Workflow

1. **Create models** in respective apps (accounts, mail)
2. **Create serializers** for REST API
3. **Create views/viewsets** for API endpoints
4. **Update urls.py** to route to your views
5. **Write tests** in `tests/`
6. **Run migrations** after model changes

## Key Features to Implement

### Accounts App
- [ ] User registration/login
- [ ] User profile management
- [ ] Email account credentials storage

### Mail App
- [ ] Email composition API
- [ ] Inbox/folder management
- [ ] Email encryption metadata storage
- [ ] Search functionality

### Integration
- [ ] Connect frontend to API
- [ ] Implement real-time notifications
- [ ] Add email attachment support
- [ ] Implement key rotation

## Useful Commands

```bash
# Create new Django app
python manage.py startapp myapp apps/myapp

# Make migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run shell
python manage.py shell

# Collect static files
python manage.py collectstatic

# Run tests
python manage.py test

# Check for issues
python manage.py check
```

## Documentation

- [README.md](README.md) - Project overview
- [ETSI QKD 014 Integration](docs/ETSI_QKD_014_integration.md) - QKD standard docs

## Support

If you encounter issues:

1. Check that Docker is running
2. Verify `.env` file is configured correctly
3. Check logs: `docker compose logs`
4. Ensure all migrations are applied
5. Check Python virtual environment is activated

## Project Status

✅ **Project structure created**  
✅ **Django configured**  
✅ **QKD implementation complete**  
✅ **Crypto utilities ready**  
✅ **Email infrastructure ready**  
✅ **Docker setup complete**  
✅ **Tests created**  

🚀 **Ready for development!**

---

**Happy Coding!** 🔐⚛️📧
