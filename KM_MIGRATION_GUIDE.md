# 🚀 New Flow Setup - KM Service Migration

## ✅ What Was Done

### 1. Created KM Service (`km-service/`)
- **ETSI GS QKD 014 compliant** REST API
- **Flask-based** microservice (separate from Django)
- **Database persistence** (SQLite dev, PostgreSQL ready)
- **Encrypted key storage** at rest
- **QKD Orchestrator** with BB84 simulator
- **Full test suite** included

### 2. Updated Django Backend
- Created **`crypto/km_client.py`** - REST client wrapper
- Updated **`crypto/level_qkd.py`** - Uses KM REST API
- Added **`KM_SERVICE_URL`** to settings

### 3. Key Features
- ✅ SAE-A (Alice) requests key → KM orchestrates QKD → Returns alice_key
- ✅ SAE-B (Bob) retrieves matching bob_key by key_id
- ✅ Authorization checks (requester must match recipient)
- ✅ Key lifecycle management (STORED → SERVED → CONSUMED)
- ✅ Key pool reuse
- ✅ Automatic expiry cleanup

---

## 📦 Commands to Run

### 1. Install KM Service Dependencies

```powershell
# In km-service directory
cd km-service
pip install -r requirements.txt
```

**What this installs:**
- `flask` - REST API framework
- `flask-cors` - CORS support
- `flask-sqlalchemy` - Database ORM
- `cryptography` - Key encryption
- `psycopg2-binary` - PostgreSQL driver (for future)
- `python-dotenv` - Environment variables

### 2. Start KM Service

```powershell
# In km-service directory
python app.py
```

**Expected output:**
```
============================================================
🔐 QuteMail Key Management Service - ETSI GS QKD 014
============================================================
Host: 0.0.0.0:5001
Debug: True
Database: sqlite:///km_keys.db
============================================================
✅ Database initialized: sqlite:///km_keys.db
 * Running on http://0.0.0.0:5001
```

**Leave this running!**

### 3. Test KM Service (New Terminal)

```powershell
# In km-service directory
python test_km.py
```

**Expected output:**
```
============================================================
🧪 QuteMail KM Service - Test Suite
============================================================

TEST 1: Health Check
✅ Health check passed

TEST 2: Key Request and Retrieval Flow
✅ Alice received key
✅ Bob received key
✅ Keys match! Alice and Bob have the same key material.

... more tests ...

============================================================
✅ ALL TESTS PASSED!
============================================================
```

### 4. Start Django Backend (New Terminal)

```powershell
# In backend directory
cd backend
python manage.py runserver
```

**Django will now use KM REST API for QKD operations!**

### 5. Start Frontend (New Terminal)

```powershell
# In client directory
cd client
npm run dev
```

---

## 🧪 Testing the Full Flow

### Test 1: Health Check

```powershell
curl http://localhost:5001/api/v1/status
```

### Test 2: Request Key (Alice)

```powershell
curl -X POST http://localhost:5001/api/v1/keys/request `
  -H "Content-Type: application/json" `
  -d '{
    \"requester_sae\": \"jeyasurya0207@gmail.com\",
    \"recipient_sae\": \"aalan@qutemail.tech\"
  }'
```

**Copy the `key_id` from response (e.g., `abc123-alice`)**

### Test 3: Retrieve Key (Bob)

```powershell
# Replace KEY_ID with the ID from step 2, change -alice to -bob
curl "http://localhost:5001/api/v1/keys/KEY_ID-bob?requester_sae=aalan@qutemail.tech"
```

---

## 🔄 Full Email Flow

### Sending (SAE-A → SAE-B)

1. **User composes email** in QuteMail frontend
2. **Frontend** calls Django API: `POST /api/mail/send`
3. **Django** calls `crypto/router.py` with `security_level='qkd'`
4. **`level_qkd.py`** calls **KM REST API**: `POST /api/v1/keys/request`
   ```json
   {
     "requester_sae": "jeyasurya0207@gmail.com",
     "recipient_sae": "aalan@qutemail.tech"
   }
   ```
5. **KM Service**:
   - Checks key pool for unused keys
   - If none, orchestrates **QKD session** (BB84 simulator)
   - Creates **key pair** (alice_key + bob_key)
   - Stores both in database (KM1 + KM2 simulation)
   - Returns `alice_key` to sender
6. **Django** encrypts email with `alice_key` (AES-256-GCM)
7. **SMTP** sends email with headers:
   ```
   X-QuteMail-Encrypted: true
   X-QuteMail-Key-ID: abc123-alice
   X-QuteMail-Algorithm: QKD+AES-256-GCM
   ```

### Receiving (SAE-B)

1. **User clicks sync** in QuteMail
2. **Frontend** calls Django API: `POST /api/mail/sync/{account_id}`
3. **Django IMAP** fetches emails
4. **Detects** `X-QuteMail-Encrypted: true` header
5. **Extracts** `key_id` (changes `-alice` to `-bob`)
6. **Calls KM REST API**: `GET /api/v1/keys/abc123-bob?requester_sae=aalan@qutemail.tech`
7. **KM Service**:
   - Finds `bob_key` in database
   - **Verifies authorization** (requester matches recipient)
   - Returns `bob_key`
8. **Django** decrypts email with `bob_key`
9. **Stores** decrypted email in database
10. **Frontend** displays decrypted email

---

## 📁 What Changed

### New Files Created
```
km-service/
├── app.py                   # Flask REST API
├── database.py              # Database configuration
├── models.py                # QKDKey model with encryption
├── qkd_orchestrator.py      # BB84 simulator wrapper
├── requirements.txt         # Dependencies
├── .env                     # Configuration
├── .env.example             # Template
├── README.md                # Documentation
└── test_km.py               # Test suite

backend/
└── crypto/
    └── km_client.py         # REST client wrapper
```

### Modified Files
```
backend/
├── crypto/level_qkd.py      # Now uses km_client REST API
└── qutemail_core/settings.py # Added KM_SERVICE_URL
```

### Kept as Fallback
```
backend/km/                  # Old implementation (can delete after testing)
```

---

## 🔧 PostgreSQL Migration (Future)

When ready for production:

### 1. Create PostgreSQL Database

```sql
CREATE DATABASE km_database;
```

### 2. Update km-service/.env

```env
DATABASE_URL=postgresql://username:password@localhost:5432/km_database
```

### 3. Restart KM Service

```powershell
python app.py
```

Flask-SQLAlchemy will **automatically create tables**!

---

## 🎯 Architecture Benefits

### Before (Old Flow)
```
Django ──> km/client.py (in-memory dict) ──> BB84 Simulator
```
❌ Keys lost on restart
❌ No persistence
❌ Not distributed

### After (New Flow)
```
Django ──> KM REST API ──> Database ──> BB84 Simulator
                   │
                   └──> QKD Orchestrator
                           │
                   ┌───────┴────────┐
                  KM1             KM2
                (alice)          (bob)
```
✅ Persistent keys
✅ ETSI compliant
✅ Distributed-ready
✅ Encrypted storage
✅ Authorization checks
✅ Key lifecycle management

---

## 🐛 Troubleshooting

### KM Service won't start

**Error:** `ModuleNotFoundError: No module named 'flask'`

**Fix:**
```powershell
cd km-service
pip install -r requirements.txt
```

### Django can't connect to KM

**Error:** `KM service connection failed`

**Fix:** Make sure KM service is running on port 5001
```powershell
# Check if running
curl http://localhost:5001/api/v1/status
```

### Database locked error

**Error:** `database is locked`

**Fix:** Only one process can write to SQLite at a time. Use PostgreSQL for production.

### Keys don't match

**Error:** `Keys don't match! Alice and Bob have different keys`

**Fix:** This shouldn't happen with BB84 simulator. Check `qkd_orchestrator.py` - alice_key and bob_key should have same `key_material`.

---

## ✅ Next Steps

1. ✅ **Run all commands** above
2. ✅ **Test KM service** with `test_km.py`
3. ✅ **Send encrypted email** from jeyasurya@gmail.com to aalan@qutemail.tech
4. ✅ **Verify decryption** works
5. ✅ **Delete old `backend/km/`** if everything works
6. 🚀 **Deploy to production** with PostgreSQL

---

## 📚 Documentation

- **KM Service**: See `km-service/README.md`
- **ETSI Compliance**: See `ETSI_QKD_COMPLIANCE.md`
- **API Reference**: See `km-service/README.md` API Endpoints section
- **Email Setup**: See `EMAIL_PROVIDER_SETUP.md`

---

## 🎉 Summary

You now have a **proper distributed QKD architecture** with:
- Separate KM service (ETSI compliant)
- REST API communication
- Database persistence
- Encrypted key storage
- Authorization checks
- Full test coverage

**The flow is exactly what you described!** 🚀
