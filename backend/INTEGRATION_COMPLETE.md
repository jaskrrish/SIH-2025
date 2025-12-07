# Backend Integration Complete! 🎉

## What's Been Implemented

### Apps Created:
1. **accounts** - User authentication with JWT
2. **email_accounts** - External email connections (Gmail, Outlook, etc.)
3. **mail** - Email storage, IMAP fetch, SMTP send

### API Endpoints:

#### Authentication (`/api/auth/`)
- `POST /api/auth/register` - Create @qutemail.com account
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

#### Email Accounts (`/api/email-accounts/`)
- `POST /api/email-accounts/connect` - Connect Gmail/Outlook/Yahoo
- `GET /api/email-accounts/` - List connected accounts
- `DELETE /api/email-accounts/{id}` - Remove account

#### Mail (`/api/mail/`)
- `GET /api/mail/sync/{account_id}` - Fetch emails from provider via IMAP
- `GET /api/mail/` - List all emails (query: account_id, limit)
- `GET /api/mail/{email_id}` - Get single email
- `POST /api/mail/send` - Send email via SMTP

---

## Commands to Run

### 1. Install new dependencies (JWT support):
```powershell
cd backend
pip install djangorestframework-simplejwt PyJWT
```

### 2. Create database migrations:
```powershell
python manage.py makemigrations accounts
python manage.py makemigrations email_accounts
python manage.py makemigrations mail
```

### 3. Apply migrations:
```powershell
python manage.py migrate
```

### 4. Create superuser (optional, for admin panel):
```powershell
python manage.py createsuperuser
```

### 5. Run the server:
```powershell
python manage.py runserver
```

---

## Testing the APIs

### 1. Register a user:
```bash
POST http://127.0.0.1:8000/api/auth/register
Body: {
  "username": "surya",
  "name": "Jeyasurya",
  "password": "password123",
  "confirm_password": "password123"
}
```

Response: `{ user: {...}, tokens: { access: "...", refresh: "..." } }`

### 2. Login:
```bash
POST http://127.0.0.1:8000/api/auth/login
Body: {
  "username": "surya",
  "password": "password123"
}
```

### 3. Connect Gmail (requires JWT token):
```bash
POST http://127.0.0.1:8000/api/email-accounts/connect
Headers: Authorization: Bearer <access_token>
Body: {
  "provider": "gmail",
  "email": "your-email@gmail.com",
  "app_password": "your-16-char-app-password"
}
```

**Note**: For Gmail app passwords, go to:
https://myaccount.google.com/apppasswords

### 4. Sync emails:
```bash
GET http://127.0.0.1:8000/api/mail/sync/1
Headers: Authorization: Bearer <access_token>
```

### 5. List emails:
```bash
GET http://127.0.0.1:8000/api/mail/?account_id=1&limit=20
Headers: Authorization: Bearer <access_token>
```

### 6. Send email:
```bash
POST http://127.0.0.1:8000/api/mail/send
Headers: Authorization: Bearer <access_token>
Body: {
  "account_id": 1,
  "to_emails": ["recipient@example.com"],
  "subject": "Test Email",
  "body_text": "Hello from QuteMail!",
  "use_quantum": false
}
```

---

## Features

✅ User registration with auto-generated @qutemail.com emails
✅ JWT authentication
✅ Encrypted storage of app passwords
✅ IMAP email fetching from Gmail/Outlook/Yahoo
✅ SMTP email sending
✅ Email storage in database
✅ Support for "Normal" and "Quantum Secure" modes (quantum is placeholder)

---

## Next Steps

1. Run the commands above to set up the database
2. Test the APIs with Postman/Thunder Client
3. Integrate frontend with these endpoints
4. Later: Implement QKD encryption in `use_quantum` mode

---

## Notes

- App passwords are encrypted using Fernet before storage
- JWT tokens expire after 1 day (configurable in settings)
- @qutemail.com addresses are user accounts only (no mail server yet)
- The `use_quantum` flag in send_email is ready for future QKD integration
