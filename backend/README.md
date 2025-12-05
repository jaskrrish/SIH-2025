# QuteMail Backend - Development Scaffold

A minimal Django backend for QuteMail quantum-safe email system. This scaffold provides the basic structure for frontend development and team collaboration without implementing actual encryption/key management internals.

## 🎯 Project Goals

- **Minimal & Flexible**: Basic structure that doesn't lock in implementation details
- **Team Independence**: Frontend, crypto, and KM teams can work in parallel
- **Pluggable Architecture**: Easy integration of crypto/KM modules later
- **Development-Ready**: Works out of the box for local development

## 📁 Project Structure

```
backend/
├── api/                  # Main API endpoints (/api/send/, /api/receive/)
├── qmailbox/             # Email helpers (SMTP, hooks)
│   ├── smtp.py          # SMTP sending functionality
│   └── hooks.py         # Pluggable encryption/decryption hooks
├── crypto/               # Crypto module (interface only)
│   └── README.md        # Expected interface documentation
├── km/                   # Key Management simulator
│   └── views.py         # KM API endpoints
├── qutemail_core/        # Django project settings
└── manage.py
```

## 🚀 Quick Start

### 1. Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you get execution policy error, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Run Database Migrations

```powershell
cd backend
python manage.py migrate
```

### 4. Start Development Server

```powershell
python manage.py runserver
```

Server will start at `http://localhost:8000`

## 📡 API Endpoints

### 1. Send Email - `POST /api/send/`

Send an email with optional encryption via pluggable hooks.

**Request:**
```json
{
  "from": "sender@example.com",
  "to": ["recipient@example.com"],
  "subject": "Test Email",
  "body": "This is a test email body.",
  "meta": {
    "security_level": "high",
    "priority": "urgent"
  }
}
```

**Response:**
```json
{
  "status": "sent",
  "encrypted": false,
  "info": {
    "status": "sent_mock",
    "message_id": "mock-message-id",
    "recipients": ["recipient@example.com"]
  }
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/api/send/ \
  -H "Content-Type: application/json" \
  -d '{
    "from": "sender@example.com",
    "to": ["recipient@example.com"],
    "subject": "Test Email",
    "body": "Hello, World!"
  }'
```

**PowerShell Example:**
```powershell
$body = @{
    from = "sender@example.com"
    to = @("recipient@example.com")
    subject = "Test Email"
    body = "Hello, World!"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/send/" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

### 2. Receive Email - `POST /api/receive/`

Parse and optionally decrypt a received email.

**Request:**
```json
{
  "raw_mime": "From: sender@example.com\nTo: recipient@example.com\nSubject: Test\n\nEmail body here",
  "meta": {
    "source": "imap",
    "mailbox": "INBOX"
  }
}
```

**Response:**
```json
{
  "status": "ok",
  "subject": "Test",
  "body": "Email body here",
  "from": "sender@example.com",
  "to": ["recipient@example.com"],
  "encrypted": false,
  "headers": {
    "From": "sender@example.com",
    "To": "recipient@example.com",
    "Subject": "Test"
  }
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/api/receive/ \
  -H "Content-Type: application/json" \
  -d '{
    "raw_mime": "From: sender@example.com\nTo: recipient@example.com\nSubject: Test\n\nEmail body"
  }'
```

### 3. KM Status - `GET /api/km/status/`

Check Key Management service status.

**Response:**
```json
{
  "status": "OK",
  "service": "qute-km-sim",
  "version": "1.0.0-dev",
  "keys_in_store": 0,
  "note": "This is a development simulator. Replace with real KM service in production."
}
```

**cURL Example:**
```bash
curl http://localhost:8000/api/km/status/
```

### 4. Get Key - `POST /api/km/get_key/`

Generate a new encryption key.

**Request (optional body):**
```json
{
  "size": 32,
  "purpose": "email-encryption",
  "ttl": 3600
}
```

**Response:**
```json
{
  "status": "success",
  "keyId": "550e8400-e29b-41d4-a716-446655440000",
  "key": "base64encodedkey...",
  "size": 32,
  "created": "2025-12-04T10:30:00Z",
  "expires": "2025-12-04T11:30:00Z",
  "note": "Simulated key - not from real QKD hardware"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/api/km/get_key/ \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 5. Get Key By ID - `POST /api/km/get_key_with_id/`

Retrieve an existing key by its ID.

**Request:**
```json
{
  "keyId": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:**
```json
{
  "status": "success",
  "keyId": "550e8400-e29b-41d4-a716-446655440000",
  "key": "base64encodedkey...",
  "size": 32,
  "created": "2025-12-04T10:30:00Z",
  "expires": "2025-12-04T11:30:00Z"
}
```

## 🔌 Integration Guide

### For Crypto Team

1. Implement encryption/decryption functions in `crypto/` app
2. See `crypto/README.md` for expected interface
3. Modify `qmailbox/hooks.py` to call your functions:

```python
# In qmailbox/hooks.py
from crypto import encrypt, decrypt
import requests

def encrypt_and_send_hook(plaintext_bytes, subject, meta=None):
    # Get key from KM
    key_response = requests.post('http://localhost:8000/api/km/get_key/')
    key_data = key_response.json()
    
    # Encrypt
    cipher_bytes = encrypt(plaintext_bytes, 'standard', {
        'key': key_data['key'],
        'keyId': key_data['keyId'],
        'algorithm': 'AES-256-GCM'
    })
    
    # Return encrypted data with headers
    headers = {
        'X-QuteMail-Encrypted': 'true',
        'X-QuteMail-Key-ID': key_data['keyId'],
        'X-QuteMail-Algorithm': 'AES-256-GCM'
    }
    return (cipher_bytes, headers)
```

### For KM Team

Replace the simulator in `km/views.py` with real KM service integration:
- Connect to actual QKD hardware
- Implement ETSI QKD 014 API client
- Add proper key lifecycle management
- Implement audit logging

### For Frontend Team

Use the provided REST API endpoints:
- `POST /api/send/` - Send emails
- `POST /api/receive/` - Parse received emails
- `GET /api/km/status/` - Check KM service health

CORS is enabled for all origins in development mode.

## 🧪 Testing the Full Flow

### Test 1: Send Plaintext Email

```powershell
$body = @{
    from = "alice@example.com"
    to = @("bob@example.com")
    subject = "Hello Bob"
    body = "This is a plaintext message"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/send/" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

### Test 2: Get a Key from KM

```powershell
$keyResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/km/get_key/" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{}'

Write-Host "Key ID: $($keyResponse.keyId)"
Write-Host "Key: $($keyResponse.key)"
```

### Test 3: Retrieve Key by ID

```powershell
$body = @{
    keyId = $keyResponse.keyId
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/km/get_key_with_id/" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

### Test 4: Parse Received Email

```powershell
$body = @{
    raw_mime = "From: alice@example.com`nTo: bob@example.com`nSubject: Test`n`nHello!"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/receive/" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

## 📝 Development Notes

### SMTP Configuration

By default, emails are sent using a mock SMTP function (no real email server needed). To use real SMTP:

1. Provide `smtp_config` in the send request:

```json
{
  "from": "your-email@gmail.com",
  "to": ["recipient@example.com"],
  "subject": "Real Email",
  "body": "This will be sent via real SMTP",
  "smtp_config": {
    "host": "smtp.gmail.com",
    "port": 587,
    "username": "your-email@gmail.com",
    "password": "your-app-password",
    "use_tls": true
  }
}
```

2. **Gmail Users**: Use [App Passwords](https://support.google.com/accounts/answer/185833), not your regular password

### Security Notes

⚠️ **This is a DEVELOPMENT scaffold only:**
- CSRF protection is disabled for API endpoints
- CORS allows all origins
- SQLite database (not for production)
- Mock SMTP sender by default
- In-memory KM simulator
- No actual encryption implemented

**Before production:**
- Enable CSRF protection
- Restrict CORS origins
- Use PostgreSQL/MySQL
- Implement real SMTP with OAuth2
- Replace KM simulator with real QKD integration
- Implement actual cryptography
- Add authentication/authorization
- Add rate limiting
- Add logging and monitoring

## 🛠️ Troubleshooting

### Port Already in Use
```powershell
# Check what's using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F

# Or use a different port
python manage.py runserver 8001
```

### Virtual Environment Not Activating
```powershell
# Allow script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate again
.\venv\Scripts\Activate.ps1
```

### Module Import Errors
```powershell
# Make sure you're in the backend directory
cd backend

# Run migrations
python manage.py migrate

# Check installed apps
python manage.py check
```

## 📚 Next Steps

1. **Frontend Team**: Start building React UI using the API endpoints
2. **Crypto Team**: Implement encryption in `crypto/` app and update hooks
3. **KM Team**: Replace simulator with real QKD integration
4. **DevOps**: Set up proper deployment with PostgreSQL, Nginx, SSL

## 🤝 Contributing

Each team should work in their respective directories:
- Frontend: Use the API as-is
- Crypto: Implement in `crypto/` app
- KM: Replace `km/views.py` with real implementation
- Backend: Extend API endpoints as needed

## 📄 License

[Your License Here]

## 📧 Contact

[Your Contact Information]

---

**Built with ❤️ for quantum-safe communication**
