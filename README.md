# QuteMail - Quantum-Safe Email System

A complete email system with multi-level encryption including Quantum Key Distribution (QKD) using BB84 protocol simulation.

## 🎯 Overview

QuteMail is a full-stack email application featuring:
- **4 Security Levels**: Regular, AES-256-GCM, QKD+AES, QRNG+PQC
- **BB84 QKD Simulator**: Quantum key distribution for secure communication
- **External Email Integration**: Connect Gmail, Outlook, Yahoo via IMAP/SMTP
- **Real-time Sync**: Automatic encryption/decryption on send/receive
- **JWT Authentication**: Secure user management
- **Modern UI**: React 19 with Tailwind CSS

## 📁 Project Structure

```
SIH-2025/
├── backend/                    # Django REST API
│   ├── accounts/              # User authentication (JWT)
│   ├── email_accounts/        # External email connections
│   ├── mail/                  # Email operations (IMAP/SMTP)
│   ├── crypto/                # Encryption modules
│   │   ├── router.py         # Security level dispatcher
│   │   ├── level_regular.py  # No encryption
│   │   ├── level_aes.py      # AES-256-GCM
│   │   ├── level_qkd.py      # QKD+AES
│   │   └── level_qrng_pqc.py # PQC stub
│   ├── km/                    # Key Management
│   │   ├── client.py         # KM client wrapper
│   │   ├── simulator.py      # BB84 simulator
│   │   └── views.py          # KM API endpoints
│   └── qutemail_core/         # Django settings
│
└── client/                     # React frontend
    ├── src/
    │   ├── pages/
    │   │   ├── Auth.tsx       # Login/Register
    │   │   ├── Home.tsx       # Account management
    │   │   └── Mailbox.tsx    # Email interface
    │   └── lib/
    │       └── api.ts         # API client
    └── public/
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Gmail account (for testing)

### Backend Setup

```powershell
# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Start server
python manage.py runserver
```

Server runs at: `http://127.0.0.1:8000`

### Frontend Setup

```powershell
# 1. Navigate to client
cd client

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```

Client runs at: `http://localhost:5173`

---

## 🔐 Security Levels

### 1. Regular
- No encryption applied
- Standard SMTP transmission
- Use for non-sensitive content

### 2. Standard AES
- **Algorithm**: AES-256-GCM
- **Key Generation**: Random 32-byte key
- **Key Distribution**: Via email header (`X-QuteMail-AES-Key`)
- **Use Case**: Basic encryption for moderate security

### 3. QKD + AES (Recommended)
- **Algorithm**: BB84 + AES-256-GCM
- **Key Distribution**: Quantum key distribution simulation
- **Key Management**: 
  - Sender gets `alice_key` for encryption
  - Recipient gets `bob_key` for decryption
  - Keys linked by UUID
  - One-time-use (consumed after decryption)
- **Authorization**: Only intended recipient can decrypt
- **Use Case**: High security, quantum-resistant

### 4. QRNG + PQC (Coming Soon)
- Quantum Random Number Generator
- Post-Quantum Cryptography algorithms
- Future-proof against quantum computing attacks

---

## 🔑 Encryption Flow (QKD+AES)

### Sending Encrypted Email

```
1. User composes email → selects QKD+AES security level
2. Frontend sends to /api/mail/send with security_level='qkd'
3. Backend: mail/views.py receives request
4. crypto/router.py dispatches to level_qkd.encrypt()
5. level_qkd.py calls km_client.generate_key()
6. km/client.py uses BB84Simulator:
   ├─ Generates alice_key (sender)
   └─ Generates bob_key (recipient, stored with UUID)
7. level_qkd.py encrypts with level_aes.encrypt(plaintext, alice_key)
8. level_aes.py performs AES-256-GCM encryption
9. smtp_client.py adds custom headers:
   ├─ X-QuteMail-Security-Level: qkd
   ├─ X-QuteMail-Key-ID: <uuid>
   └─ X-QuteMail-Encrypted: true
10. Email sent via Gmail SMTP with encrypted body
```

### Receiving Encrypted Email

```
1. User clicks "Sync" → /api/mail/sync/{account_id}
2. imap_client.py fetches emails via IMAP
3. _parse_email() detects X-QuteMail-Encrypted header
4. Extracts key_id from X-QuteMail-Key-ID header
5. crypto/router.py dispatches to level_qkd.decrypt()
6. level_qkd.py calls km_client.get_key_by_id(key_id, requester_sae)
7. km/client.py:
   ├─ Validates requester is recipient
   ├─ Checks key not expired/consumed
   └─ Returns bob_key
8. level_qkd.py decrypts with level_aes.decrypt(ciphertext, bob_key)
9. level_aes.py performs AES-256-GCM decryption + tag verification
10. Plaintext stored in database
11. Frontend displays original message
```

---

## 🔬 BB84 QKD Simulator

Located in `backend/km/simulator.py`

```python
class BB84Simulator:
    def generate_key_pair(key_size=256) -> (QKDKey, QKDKey):
        """
        Simulates BB84 quantum key distribution protocol
        
        Steps:
        1. Alice prepares qubits with random bits and bases
        2. Bob measures with random bases
        3. Bases are compared (classical channel)
        4. Keep bits where bases matched
        5. Return matching key pairs
        
        Returns:
            alice_key: QKDKey for sender
            bob_key: QKDKey for recipient
        """
```

**Features:**
- Simulates quantum channel with configurable error rate
- Generates cryptographically secure matching keys
- Suitable for demo/testing (replace with real QKD in production)

---

## 📡 API Endpoints

### Authentication
```http
POST /api/auth/register     # Create account
POST /api/auth/login        # Get JWT token
GET  /api/auth/me           # User info
```

### Email Accounts
```http
POST   /api/email-accounts/connect  # Connect Gmail/Outlook
GET    /api/email-accounts/         # List accounts
DELETE /api/email-accounts/{id}     # Remove account
```

### Mail Operations
```http
GET  /api/mail/sync/{account_id}    # Fetch via IMAP
GET  /api/mail/                     # List emails
GET  /api/mail/{email_id}           # Get single email
POST /api/mail/send                 # Send with encryption
```

**Send Email Body:**
```json
{
  "account_id": 1,
  "to_emails": ["recipient@gmail.com"],
  "subject": "Secret Message",
  "body_text": "This will be encrypted",
  "security_level": "qkd"
}
```

### Key Management
```http
GET  /api/km/status/              # Service status
POST /api/km/get_key/             # Generate QKD key
POST /api/km/get_key_with_id/     # Retrieve by UUID
```

---

## 🧪 Testing

### 1. Register & Login
```bash
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","name":"Alice","password":"test123","confirm_password":"test123"}'

curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"test123"}'
```

### 2. Connect Gmail
```bash
curl -X POST http://127.0.0.1:8000/api/email-accounts/connect \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"provider":"gmail","email":"your@gmail.com","app_password":"abcd efgh ijkl mnop"}'
```

**Get Gmail App Password:** https://myaccount.google.com/apppasswords

### 3. Send QKD-Encrypted Email
```bash
curl -X POST http://127.0.0.1:8000/api/mail/send \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"account_id":1,"to_emails":["bob@gmail.com"],"subject":"Secret","body_text":"Encrypted with QKD","security_level":"qkd"}'
```

### 4. Sync & Decrypt
```bash
curl http://127.0.0.1:8000/api/mail/sync/1 \
  -H "Authorization: Bearer <token>"
```

---

## 🎨 Frontend Features

### Home Page
- **Account Management**: Add/remove Gmail/Outlook accounts
- **QuteMail Account**: Built-in @qutemail.com address
- **Visual Indicators**: Shows connected providers

### Mailbox
- **4 Security Options**: Visual cards for each level
  - Regular (gray)
  - Standard AES (blue)
  - QKD+AES (green/ISRO blue)
  - QRNG+PQC (purple, disabled)
- **Compose Modal**: Select encryption before sending
- **Auto-Decryption**: Encrypted emails automatically decrypted on sync
- **Accessibility**: Screen reader support, high contrast mode

---

## 🔧 Configuration

### Backend Settings (`backend/qutemail_core/settings.py`)
```python
INSTALLED_APPS = [
    'accounts',        # User auth
    'email_accounts',  # Gmail integration
    'mail',           # IMAP/SMTP
    'crypto',         # Encryption
    'km',             # Key management
]

# CORS for frontend
CORS_ALLOW_ALL_ORIGINS = True  # Dev only

# JWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
}
```

### Frontend Config (`client/src/lib/api.ts`)
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URI || 'http://127.0.0.1:8000/api';

export const API_ENDPOINTS = {
  AUTH: { REGISTER, LOGIN, ME },
  EMAIL_ACCOUNTS: { LIST, CONNECT, DELETE },
  MAIL: { SYNC, LIST, SEND, DETAIL },
  KM: { STATUS, GET_KEY, GET_KEY_WITH_ID }
};
```

---

## 📚 Documentation

- **Backend**: `backend/README.md` - Full API reference
- **Crypto Module**: `backend/crypto/README.md` - Encryption details
- **Frontend**: `client/README.md` - React setup

---

## 🛠️ Technology Stack

### Backend
- **Framework**: Django 6.0, Django REST Framework
- **Auth**: JWT (djangorestframework-simplejwt)
- **Encryption**: `cryptography` library (AES-256-GCM)
- **Email**: `imaplib`, `smtplib` (Python stdlib)
- **Database**: SQLite (dev), PostgreSQL (production)

### Frontend
- **Framework**: React 19.2
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **HTTP**: Fetch API

---

## 🚀 Production Deployment

### Backend
1. Set `DEBUG = False` in settings
2. Configure PostgreSQL database
3. Set secure `SECRET_KEY`
4. Enable HTTPS
5. Configure CORS for specific origin
6. Replace BB84 simulator with real QKD hardware
7. Implement proper key storage (not in-memory)

### Frontend
1. Build: `npm run build`
2. Serve `dist/` via Nginx/Apache
3. Set `VITE_API_URI` to production backend URL
4. Enable CSP headers
5. Configure CDN for static assets

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

---

## 📄 License

This project is part of Smart India Hackathon 2025.

---

## 👥 Team

- **Frontend**: React/TypeScript UI
- **Backend**: Django REST API
- **Crypto**: Multi-level encryption system
- **QKD**: BB84 simulator integration

---

## 📞 Support

For issues or questions:
1. Check documentation in respective README files
2. Review API endpoints in Postman/Bruno
3. Enable debug mode and check Django logs
4. Open GitHub issue with error details

---

**Built with ❤️ for Smart India Hackathon 2025**
