# QuteMail Backend - Quantum-Safe Email System

A Django backend for QuteMail quantum-safe email system with integrated encryption, QKD key management, and external email provider support (Gmail, Outlook, Yahoo).

## 🎯 Project Overview

QuteMail is a complete email system featuring:
- **Multi-level Encryption**: Regular, AES-256-GCM, QKD+AES, QRNG+PQC
- **BB84 QKD Simulator**: Quantum key distribution for secure communication
- **External Email Integration**: Connect Gmail/Outlook via IMAP/SMTP
- **JWT Authentication**: Secure user authentication
- **Real-time Email Sync**: Fetch and decrypt emails automatically

## 📁 Project Structure

```
backend/
├── accounts/             # User authentication (JWT)
│   ├── models.py        # Custom User model
│   ├── views.py         # Register, login, user info
│   └── urls.py          # /api/auth/* endpoints
├── email_accounts/       # External email connections
│   ├── models.py        # EmailAccount model (Gmail, etc.)
│   ├── views.py         # Connect, list, delete accounts
│   └── urls.py          # /api/email-accounts/* endpoints
├── mail/                 # Email operations (IMAP/SMTP)
│   ├── models.py        # Email, Attachment models
│   ├── views.py         # Sync, send, list emails
│   ├── imap_client.py   # IMAP fetching with auto-decryption
│   ├── smtp_client.py   # SMTP sending with encryption headers
│   └── urls.py          # /api/mail/* endpoints
├── crypto/               # Encryption modules
│   ├── router.py        # Security level dispatcher
│   ├── level_regular.py # No encryption (passthrough)
│   ├── level_aes.py     # AES-256-GCM encryption
│   ├── level_qkd.py     # QKD+AES encryption
│   └── level_qrng_pqc.py # QRNG+PQC (stub)
├── km/                   # Key Management
│   ├── client.py        # KM client wrapper
│   ├── simulator.py     # BB84 QKD simulator
│   ├── views.py         # KM API endpoints
│   └── urls.py          # /api/km/* endpoints
├── qutemail_core/        # Django project settings
│   ├── settings.py      # Configuration
│   └── urls.py          # Main URL routing
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

### Authentication (`/api/auth/`)

#### Register
```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "surya",
  "name": "Jeyasurya",
  "password": "password123",
  "confirm_password": "password123"
}
```

#### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "surya",
  "password": "password123"
}

Response: { "user": {...}, "tokens": { "access": "...", "refresh": "..." } }
```

#### Get Current User
```http
GET /api/auth/me
Authorization: Bearer <access_token>
```

---

### Email Accounts (`/api/email-accounts/`)

#### Connect External Account
```http
POST /api/email-accounts/connect
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "provider": "gmail",
  "email": "your-email@gmail.com",
  "app_password": "your-16-char-app-password"
}
```

**Note**: For Gmail app passwords: https://myaccount.google.com/apppasswords

#### List Accounts
```http
GET /api/email-accounts/
Authorization: Bearer <access_token>
```

#### Delete Account
```http
DELETE /api/email-accounts/{id}
Authorization: Bearer <access_token>
```

---

### Mail Operations (`/api/mail/`)

#### Sync Emails (IMAP Fetch)
```http
GET /api/mail/sync/{account_id}
Authorization: Bearer <access_token>
```
Fetches emails from external provider and automatically decrypts encrypted messages.

#### List Emails
```http
GET /api/mail/?account_id={id}&limit=50
Authorization: Bearer <access_token>
```

#### Get Single Email
```http
GET /api/mail/{email_id}
Authorization: Bearer <access_token>
```

#### Send Email
```http
POST /api/mail/send
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "account_id": 1,
  "to_emails": ["recipient@gmail.com"],
  "subject": "Test Email",
  "body_text": "Hello, this is a test email",
  "body_html": "<p>Hello, this is a test email</p>",
  "security_level": "qkd"
}
```

**Security Levels:**
- `regular` - No encryption
- `aes` - AES-256-GCM encryption (key in headers)
- `qkd` - QKD+AES encryption (BB84 key distribution)
- `qrng_pqc` - QRNG+PQC (not yet implemented)

---

### Key Management (`/api/km/`)

#### Service Status
```http
GET /api/km/status/
```

#### Generate QKD Key
```http
POST /api/km/get_key/
Content-Type: application/json

{
  "requester_sae": "alice@example.com",
  "recipient_sae": "bob@example.com",
  "key_size": 256,
  "ttl": 3600
}
```

#### Retrieve Key by ID
```http
POST /api/km/get_key_with_id/
Content-Type: application/json

{
  "key_id": "uuid",
  "requester_sae": "bob@example.com",
  "mark_consumed": true
}
```

---

## 🔐 Encryption Flow

### **Sending Encrypted Email (QKD+AES)**

1. **Frontend** → User composes email, selects `qkd` security level
2. **`mail/views.py`** → Calls `crypto.router.encrypt(security_level='qkd', plaintext=body_bytes)`
3. **`crypto/router.py`** → Routes to `level_qkd.encrypt()`
4. **`crypto/level_qkd.py`** → Calls `km_client.generate_key()` to get QKD key
5. **`km/client.py`** → Uses `BB84Simulator` to generate alice_key and bob_key
   - Returns alice_key to sender (for encryption)
   - Stores bob_key in key store with UUID
6. **`crypto/level_qkd.py`** → Calls `level_aes.encrypt()` with alice_key
7. **`crypto/level_aes.py`** → Encrypts using AES-256-GCM, returns base64(nonce||ciphertext||tag)
8. **`mail/smtp_client.py`** → Adds custom headers:
   - `X-QuteMail-Security-Level: qkd`
   - `X-QuteMail-Key-ID: <uuid>`
   - `X-QuteMail-Encrypted: true`
9. **SMTP** → Sends encrypted email via Gmail

### **Receiving Encrypted Email (QKD+AES)**

1. **Frontend** → User clicks "Sync"
2. **`mail/views.py`** → Calls `IMAPClient.fetch_emails()`
3. **`mail/imap_client.py`** → Fetches emails via IMAP
4. **`_parse_email()`** → Detects `X-QuteMail-Encrypted: true` header
5. **Decryption** → Calls `crypto.router.decrypt(security_level='qkd', ciphertext=body, key_id=uuid)`
6. **`crypto/level_qkd.py`** → Calls `km_client.get_key_by_id(key_id, requester_sae=recipient)`
7. **`km/client.py`** → Retrieves bob_key from store, validates authorization
8. **`crypto/level_qkd.py`** → Calls `level_aes.decrypt()` with bob_key
9. **`crypto/level_aes.py`** → Decrypts AES-256-GCM, verifies GCM tag
10. **Database** → Stores decrypted plaintext
11. **Frontend** → Displays original message

---

## 🔬 BB84 QKD Simulator

The `km/simulator.py` implements a simplified BB84 protocol:

```python
class BB84Simulator:
    def generate_key_pair(key_size=256) -> Tuple[QKDKey, QKDKey]:
        # 1. Alice generates random bits and bases
        # 2. Bob randomly chooses measurement bases
        # 3. After measurement, they compare bases
        # 4. Keep bits where bases matched
        # 5. Return matching key material for both parties
```

**Key Features:**
- Generates matching key pairs (alice_key, bob_key)
- Simulates quantum channel with configurable error rate
- Returns QKDKey objects with `key_material` (bytes)
- Used for demo/testing (replace with real QKD hardware in production)

---

## 🧪 Testing Examples

### Test 1: Register & Login

```bash
# Register
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"surya","name":"Jeyasurya","password":"test123","confirm_password":"test123"}'

# Login
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"surya","password":"test123"}'
```

### Test 2: Connect Gmail

```bash
curl -X POST http://127.0.0.1:8000/api/email-accounts/connect \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"provider":"gmail","email":"your@gmail.com","app_password":"abcd efgh ijkl mnop"}'
```

### Test 3: Send QKD-Encrypted Email

```bash
curl -X POST http://127.0.0.1:8000/api/mail/send \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"account_id":1,"to_emails":["recipient@gmail.com"],"subject":"Secret","body_text":"This is encrypted with QKD","security_level":"qkd"}'
```

### Test 4: Sync and Decrypt Emails

```bash
curl http://127.0.0.1:8000/api/mail/sync/1 \
  -H "Authorization: Bearer <token>"

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
