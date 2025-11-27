# QtEmail Backend

Quantum-secured email backend using QKD (Quantum Key Distribution) based on ETSI GS QKD 014 standard.

## Features

- Django REST API for quantum-secured email
- QKD Key Management integration
- BB84 simulator for development
- Celery for asynchronous email processing
- Docker-based infrastructure

## Architecture

```
qutemail-backend/
├── apps/
│   ├── accounts/     # User authentication & profiles
│   ├── mail/         # Email composition, inbox, encryption
│   ├── qkd/          # QKD integration & simulator
│   ├── crypto/       # Cryptographic utilities
│   └── infra/        # SMTP/IMAP clients & storage
```

## Setup

### 1. Clone and Setup Environment

```bash
cd qutemail-backend
cp .env.example .env
# Edit .env with your configuration
```

### 2. Start Infrastructure (Docker)

```bash
docker-compose up -d db redis
```

### 3. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Run Migrations

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Start Development Server

```bash
python manage.py runserver
```

### 6. Start Celery Workers (in separate terminals)

```bash
celery -A qutemail worker -l info
celery -A qutemail beat -l info
```

## Docker Setup (Full Stack)

```bash
docker-compose up --build
```

## Testing

```bash
python manage.py test
```

## Documentation

- [ETSI QKD 014 Integration](docs/ETSI_QKD_014_integration.md)

## API Endpoints

- `/api/accounts/` - User management
- `/api/mail/` - Email operations
- `/api/qkd/` - QKD key operations

## License

MIT
