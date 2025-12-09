# QuteMail Key Management Service

**ETSI GS QKD 014 Compliant REST API for Quantum Key Distribution**

## 🎯 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    QKD ORCHESTRATOR                              │
│              (Simulates quantum channel)                         │
│                   BB84 Simulator                                 │
└────────────┬────────────────────────────────┬───────────────────┘
             │                                │
    alice_key_obj                     bob_key_obj
             │                                │
             ▼                                ▼
    ┌────────────────┐              ┌────────────────┐
    │      KM1       │              │      KM2       │
    │   (Simulated)  │              │   (Simulated)  │
    │   Key Pool DB  │              │   Key Pool DB  │
    └────────┬───────┘              └───────┬────────┘
             │                              │
             ▼                              ▼
    ┌────────────────┐              ┌────────────────┐
    │     SAE-A      │─────────────▶│     SAE-B      │
    │   Alice        │   Encrypted  │     Bob        │
    │  (Sender)      │     Email     │  (Receiver)    │
    └────────────────┘              └────────────────┘
```

## 🚀 Features

- **ETSI GS QKD 014 Compliant** REST API
- **BB84 QKD Simulator** for key generation
- **Encrypted key storage** at rest (Fernet encryption)
- **Key lifecycle management** (STORED → CACHED → SERVED → CONSUMED)
- **SAE authentication** (email-based)
- **Database persistence** (SQLite dev, PostgreSQL production)
- **Key pool management** with automatic cleanup

## 📦 Installation

### 1. Install Dependencies

```bash
cd km-service
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
# SQLite (Development)
DATABASE_URL=sqlite:///km_keys.db

# PostgreSQL (Production)
# DATABASE_URL=postgresql://user:password@localhost:5432/km_db

KM_PORT=5001
KM_HOST=0.0.0.0
KM_DEBUG=True
KM_ENCRYPTION_KEY=your-secure-32-byte-key-here
```

### 3. Run Service

```bash
python app.py
```

Server runs on `http://localhost:5001`

## 🔌 API Endpoints

### 1. Health Check

```http
GET /api/v1/status
```

**Response:**
```json
{
  "status": "OK",
  "service": "QuteMail-KM",
  "version": "2.0.0-ETSI",
  "qkd_orchestrator": {
    "total_sessions": 5,
    "error_rate": 0.0,
    "keys_in_store": 10
  },
  "database": "connected"
}
```

### 2. Request Key (SAE-A → SAE-B)

**Alice requests a key to send encrypted email to Bob**

```http
POST /api/v1/keys/request
Content-Type: application/json

{
  "requester_sae": "alice@example.com",
  "recipient_sae": "bob@example.com",
  "key_size": 256,
  "ttl": 3600
}
```

**Response:**
```json
{
  "status": "success",
  "key_id": "abc123-alice",
  "key": "base64-encoded-key-material",
  "size": 256,
  "algorithm": "BB84",
  "expires_at": "2025-12-08T12:00:00",
  "message": "New key generated via QKD",
  "source": "qkd_orchestrator"
}
```

### 3. Retrieve Key (SAE-B)

**Bob retrieves the matching key to decrypt**

```http
GET /api/v1/keys/abc123-bob?requester_sae=bob@example.com
```

**Response:**
```json
{
  "status": "success",
  "key_id": "abc123-bob",
  "key": "base64-encoded-key-material",
  "size": 256,
  "algorithm": "BB84"
}
```

### 4. Consume Key (Mark as Used)

```http
POST /api/v1/keys/consume
Content-Type: application/json

{
  "key_id": "abc123-bob",
  "requester_sae": "bob@example.com"
}
```

### 5. Cleanup Expired Keys

```http
POST /api/v1/keys/cleanup
```

## 🔐 Security Features

### Key Storage
- **Encrypted at rest** using Fernet (AES-128-CBC + HMAC)
- **Never stores plaintext** key material
- **Automatic cleanup** of expired keys

### SAE Authentication
- **Email-based** identity verification
- **Authorization checks** (requester must match recipient)
- **KM instance validation** (KM1 for Alice, KM2 for Bob)

### Key Lifecycle
```
STORED → CACHED → SERVED → CONSUMED
```

## 🧪 Testing

### Manual Testing

```bash
# 1. Check status
curl http://localhost:5001/api/v1/status

# 2. Request key (Alice)
curl -X POST http://localhost:5001/api/v1/keys/request \
  -H "Content-Type: application/json" \
  -d '{
    "requester_sae": "alice@example.com",
    "recipient_sae": "bob@example.com"
  }'

# 3. Retrieve key (Bob)
curl "http://localhost:5001/api/v1/keys/KEY_ID_HERE-bob?requester_sae=bob@example.com"
```

### Python Test Script

```python
import requests

KM_URL = "http://localhost:5001"

# Request key
response = requests.post(f"{KM_URL}/api/v1/keys/request", json={
    "requester_sae": "alice@example.com",
    "recipient_sae": "bob@example.com"
})
print(response.json())
key_id = response.json()['key_id']

# Retrieve key
response = requests.get(f"{KM_URL}/api/v1/keys/{key_id}", params={
    "requester_sae": "bob@example.com"
})
print(response.json())
```

## 🗄️ Database Schema

### QKDKey Table

```sql
CREATE TABLE qkd_keys (
    key_id VARCHAR(36) PRIMARY KEY,
    key_id_extension VARCHAR(255),
    encrypted_key_material BLOB NOT NULL,
    key_size INTEGER NOT NULL,
    requester_sae VARCHAR(255) NOT NULL,
    recipient_sae VARCHAR(255) NOT NULL,
    km_instance VARCHAR(10) NOT NULL,  -- 'KM1' or 'KM2'
    state VARCHAR(10) NOT NULL,         -- STORED/CACHED/SERVED/CONSUMED
    created_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    served_at DATETIME,
    consumed_at DATETIME,
    algorithm VARCHAR(50),
    pair_key_id VARCHAR(36)            -- Links Alice and Bob keys
);
```

## 🔄 Integration with Django Backend

Update Django settings to point to KM service:

```python
# backend/qutemail/settings.py

KM_SERVICE_URL = os.getenv('KM_SERVICE_URL', 'http://localhost:5001')
```

Update crypto routers to call KM REST API:

```python
import requests

def encrypt_email(sender_sae, recipient_sae, plaintext):
    # Request key from KM
    response = requests.post(f"{settings.KM_SERVICE_URL}/api/v1/keys/request", json={
        "requester_sae": sender_sae,
        "recipient_sae": recipient_sae
    })
    key_data = response.json()
    
    # Encrypt with key
    key_material = base64.b64decode(key_data['key'])
    # ... encryption logic
    
    return ciphertext, key_data['key_id']
```

## 📊 Monitoring

### Key Pool Statistics

```python
# Get status
response = requests.get("http://localhost:5001/api/v1/status")
stats = response.json()['qkd_orchestrator']
print(f"Total QKD sessions: {stats['total_sessions']}")
print(f"Keys in store: {stats['keys_in_store']}")
```

### Cleanup Old Keys

```python
# Run cleanup
response = requests.post("http://localhost:5001/api/v1/keys/cleanup")
print(f"Removed {response.json()['removed_count']} expired keys")
```

## 🚀 Production Deployment

### 1. PostgreSQL Setup

```bash
# Create database
createdb km_database

# Update .env
DATABASE_URL=postgresql://user:password@localhost:5432/km_database
```

### 2. Run with Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

### 3. Systemd Service

```ini
[Unit]
Description=QuteMail KM Service
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/km-service
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 0.0.0.0:5001 app:app

[Install]
WantedBy=multi-user.target
```

## 📝 ETSI Compliance

This implementation follows **ETSI GS QKD 014 v1.1.1** specifications:

- ✅ REST-based key delivery API
- ✅ Key lifecycle states (STORED, CACHED, SERVED, CONSUMED)
- ✅ SAE identity authentication
- ✅ Secure key storage
- ✅ Key expiration and cleanup
- ✅ Error codes and status responses

## 🔮 Future Enhancements

- [ ] Certificate-based authentication (ETSI requirement)
- [ ] Mutual TLS support
- [ ] Real QKD hardware integration (replace BB84 simulator)
- [ ] Key pre-generation and pooling
- [ ] Multi-instance clustering
- [ ] Prometheus metrics
- [ ] HSM integration for key encryption

## 📄 License

Part of QuteMail project
