# QtEmail API Reference

Complete REST API documentation for the QtEmail backend system.

## Base URL

```
http://localhost:8000/api/v1/
```

## Authentication

All API endpoints require authentication using Django session authentication.

```bash
# Login via Django admin
http://localhost:8000/admin/

# Or via browsable API
http://localhost:8000/api-auth/login/
```

## API Endpoints Overview

| Resource | Endpoint | Methods | Description |
|----------|----------|---------|-------------|
| Emails | `/emails/` | GET, POST | List and compose emails |
| Email Detail | `/emails/{id}/` | GET, PATCH, DELETE | View and update email |
| Email Actions | `/emails/{id}/mark_read/` | POST | Mark as read |
| Email Reply | `/emails/{id}/reply/` | POST | Reply to email |
| Email Forward | `/emails/{id}/forward/` | POST | Forward email |
| Bulk Actions | `/emails/bulk_action/` | POST | Bulk operations |
| Sync | `/emails/sync/` | POST | Manual IMAP sync |
| Attachments | `/attachments/` | GET | List attachments |
| Attachment Detail | `/attachments/{id}/` | GET | View attachment |
| Attachment Download | `/attachments/{id}/download/` | GET | Download file |
| Attachment Upload | `/attachments/upload/` | POST | Upload file |
| Settings | `/settings/` | GET, PATCH | User email settings |
| Labels | `/labels/` | GET, POST | List and create labels |
| Label Detail | `/labels/{id}/` | GET, PATCH, DELETE | Manage label |
| Apply Label | `/labels/{id}/apply/` | POST | Apply to emails |

---

## Emails API

### List Emails

**`GET /api/v1/emails/`**

List all emails for the authenticated user.

**Query Parameters**:
- `folder` (string): Filter by folder (inbox, sent, drafts, trash, spam, archive)
- `is_read` (boolean): Filter by read status
- `is_starred` (boolean): Filter by starred status
- `is_encrypted` (boolean): Filter by encryption status
- `status` (string): Filter by status (draft, queued, sending, sent, failed, received)
- `search` (string): Search in subject, from_address, body_text
- `ordering` (string): Sort by date, created_at, size (prefix with `-` for descending)
- `page` (integer): Page number (default: 1)
- `page_size` (integer): Items per page (default: 50)

**Example Request**:
```bash
curl -X GET \
  'http://localhost:8000/api/v1/emails/?folder=inbox&is_read=false&ordering=-date' \
  -H 'Cookie: sessionid=your-session-id'
```

**Example Response** (200 OK):
```json
{
  "count": 42,
  "next": "http://localhost:8000/api/v1/emails/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "message_id": "<abc123@qutemail.local>",
      "folder": "inbox",
      "subject": "[QKD-ENCRYPTED] Secure Message",
      "from_address": "sender@qutemail.local",
      "from_name": "sender@qutemail.local",
      "to_addresses": ["user@qutemail.local"],
      "to_count": 1,
      "date": "2025-01-29T10:30:00Z",
      "is_read": false,
      "is_starred": false,
      "has_attachments": false,
      "is_encrypted": true,
      "status": "received",
      "size": 1024,
      "created_at": "2025-01-29T10:30:05Z",
      "labels": []
    }
  ]
}
```

---

### Get Email Detail

**`GET /api/v1/emails/{id}/`**

Retrieve full email details including body and attachments.

**Example Request**:
```bash
curl -X GET \
  'http://localhost:8000/api/v1/emails/1/' \
  -H 'Cookie: sessionid=your-session-id'
```

**Example Response** (200 OK):
```json
{
  "id": 1,
  "message_id": "<abc123@qutemail.local>",
  "folder": "inbox",
  "subject": "Secure Message",
  "from_address": "sender@qutemail.local",
  "from_name": "sender@qutemail.local",
  "to_addresses": ["user@qutemail.local"],
  "cc_addresses": [],
  "bcc_addresses": [],
  "date": "2025-01-29T10:30:00Z",
  "body_text": "This is the decrypted email content.",
  "body_html": "",
  "is_read": false,
  "is_starred": false,
  "has_attachments": false,
  "is_encrypted": true,
  "qkd_key_id": "key-abc-123-xyz",
  "in_reply_to": null,
  "references": null,
  "status": "received",
  "size": 1024,
  "sent_at": null,
  "created_at": "2025-01-29T10:30:05Z",
  "updated_at": "2025-01-29T10:30:05Z",
  "attachments": [],
  "labels": []
}
```

---

### Compose Email

**`POST /api/v1/emails/`**

Create and send a new email.

**Request Body**:
```json
{
  "to_addresses": ["recipient@qutemail.local"],
  "cc_addresses": [],
  "bcc_addresses": [],
  "subject": "Test Email",
  "body_text": "This is a test email with QKD encryption.",
  "body_html": "",
  "encrypt": true,
  "save_draft": false,
  "in_reply_to": null,
  "references": null,
  "attachment_ids": []
}
```

**Field Descriptions**:
- `to_addresses` (array, required): List of recipient email addresses
- `cc_addresses` (array, optional): CC recipients
- `bcc_addresses` (array, optional): BCC recipients
- `subject` (string, required): Email subject (max 998 chars)
- `body_text` (string, required): Plain text body
- `body_html` (string, optional): HTML body
- `encrypt` (boolean, optional): Enable QKD encryption (defaults to user setting)
- `save_draft` (boolean, optional): Save as draft instead of sending
- `in_reply_to` (string, optional): Message-ID of email being replied to
- `references` (string, optional): Space-separated list of Message-IDs
- `attachment_ids` (array, optional): List of pre-uploaded attachment IDs

**Example Request**:
```bash
curl -X POST \
  'http://localhost:8000/api/v1/emails/' \
  -H 'Content-Type: application/json' \
  -H 'Cookie: sessionid=your-session-id' \
  -d '{
    "to_addresses": ["recipient@qutemail.local"],
    "subject": "Test Email",
    "body_text": "Hello, this is a test!",
    "encrypt": true
  }'
```

**Example Response** (201 Created):
```json
{
  "id": 42,
  "message_id": "<generated-uuid@qutemail.local>",
  "folder": "sent",
  "subject": "[QKD-ENCRYPTED] Test Email",
  "from_address": "user@qutemail.local",
  "to_addresses": ["recipient@qutemail.local"],
  "status": "queued",
  "is_encrypted": true,
  "qkd_key_id": "key-def-456-uvw",
  "created_at": "2025-01-29T11:00:00Z"
}
```

---

### Mark Email as Read

**`POST /api/v1/emails/{id}/mark_read/`**

Mark an email as read.

**Example Request**:
```bash
curl -X POST \
  'http://localhost:8000/api/v1/emails/1/mark_read/' \
  -H 'Cookie: sessionid=your-session-id'
```

**Example Response** (200 OK):
```json
{
  "status": "marked as read"
}
```

---

### Mark Email as Unread

**`POST /api/v1/emails/{id}/mark_unread/`**

Mark an email as unread.

**Example Response** (200 OK):
```json
{
  "status": "marked as unread"
}
```

---

### Star/Unstar Email

**`POST /api/v1/emails/{id}/star/`**

Toggle starred status.

**Example Response** (200 OK):
```json
{
  "status": "starred",
  "is_starred": true
}
```

---

### Move Email

**`POST /api/v1/emails/{id}/move/`**

Move email to different folder.

**Request Body**:
```json
{
  "folder": "archive"
}
```

**Valid Folders**:
- `inbox`
- `sent`
- `drafts`
- `trash`
- `spam`
- `archive`

**Example Response** (200 OK):
```json
{
  "status": "moved",
  "folder": "archive"
}
```

---

### Reply to Email

**`POST /api/v1/emails/{id}/reply/`**

Reply to an email.

**Request Body**:
```json
{
  "body_text": "Thank you for your message!",
  "body_html": "",
  "encrypt": true
}
```

**Example Response** (201 Created):
```json
{
  "id": 43,
  "subject": "Re: Original Subject",
  "from_address": "user@qutemail.local",
  "to_addresses": ["original-sender@qutemail.local"],
  "in_reply_to": "<original-message-id@qutemail.local>",
  "references": "<original-message-id@qutemail.local>",
  "status": "queued"
}
```

---

### Forward Email

**`POST /api/v1/emails/{id}/forward/`**

Forward an email.

**Request Body**:
```json
{
  "to_addresses": ["forwardto@example.com"],
  "body_html": "",
  "encrypt": false,
  "include_attachments": true
}
```

**Example Response** (201 Created):
```json
{
  "id": 44,
  "subject": "Fwd: Original Subject",
  "to_addresses": ["forwardto@example.com"],
  "status": "queued"
}
```

---

### Bulk Actions

**`POST /api/v1/emails/bulk_action/`**

Perform actions on multiple emails.

**Request Body**:
```json
{
  "email_ids": [1, 2, 3, 4, 5],
  "action": "mark_read",
  "folder": "archive"
}
```

**Actions**:
- `mark_read`
- `mark_unread`
- `star`
- `unstar`
- `move` (requires `folder` field)
- `delete` (moves to trash)

**Example Response** (200 OK):
```json
{
  "status": "success",
  "action": "mark_read",
  "count": 5
}
```

---

### Sync Emails

**`POST /api/v1/emails/sync/`**

Manually trigger email sync from IMAP server.

**Request Body** (optional):
```json
{
  "folder": "INBOX"
}
```

**Example Response** (200 OK):
```json
{
  "status": "syncing",
  "task_id": "abc-123-def-456",
  "folder": "INBOX"
}
```

---

### Get Email Logs

**`GET /api/v1/emails/{id}/logs/`**

Get event logs for a specific email.

**Example Response** (200 OK):
```json
[
  {
    "id": 1,
    "event_type": "queued",
    "message": "Email queued for sending",
    "metadata": {},
    "error_message": null,
    "traceback": null,
    "created_at": "2025-01-29T11:00:00Z"
  },
  {
    "id": 2,
    "event_type": "encrypted",
    "message": "Email encrypted with QKD key key-def-456-uvw",
    "metadata": {
      "qkd_key_id": "key-def-456-uvw",
      "algorithm": "AES-256-GCM"
    },
    "error_message": null,
    "traceback": null,
    "created_at": "2025-01-29T11:00:01Z"
  },
  {
    "id": 3,
    "event_type": "sent",
    "message": "Email sent successfully",
    "metadata": {},
    "error_message": null,
    "traceback": null,
    "created_at": "2025-01-29T11:00:30Z"
  }
]
```

---

## Attachments API

### List Attachments

**`GET /api/v1/attachments/`**

List all attachments for user's emails.

**Example Response** (200 OK):
```json
{
  "count": 10,
  "results": [
    {
      "id": 1,
      "filename": "document.pdf",
      "content_type": "application/pdf",
      "size": 102400,
      "size_kb": 100.0,
      "checksum": "sha256-abc123...",
      "content_id": null,
      "is_inline": false,
      "created_at": "2025-01-29T10:00:00Z",
      "data": null
    }
  ]
}
```

**Note**: `data` field is null in list view for performance.

---

### Get Attachment Detail

**`GET /api/v1/attachments/{id}/`**

Get attachment details with base64-encoded data.

**Example Response** (200 OK):
```json
{
  "id": 1,
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "size": 102400,
  "size_kb": 100.0,
  "checksum": "sha256-abc123...",
  "content_id": null,
  "is_inline": false,
  "created_at": "2025-01-29T10:00:00Z",
  "data": "JVBERi0xLjQKJeLjz9MKMSAwIG9iag..."
}
```

---

### Download Attachment

**`GET /api/v1/attachments/{id}/download/`**

Download attachment as binary file.

**Example Request**:
```bash
curl -X GET \
  'http://localhost:8000/api/v1/attachments/1/download/' \
  -H 'Cookie: sessionid=your-session-id' \
  -o document.pdf
```

**Response Headers**:
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="document.pdf"
Content-Length: 102400
```

---

### Upload Attachment

**`POST /api/v1/attachments/upload/`**

Upload an attachment before composing email.

**Request** (multipart/form-data):
```bash
curl -X POST \
  'http://localhost:8000/api/v1/attachments/upload/' \
  -H 'Cookie: sessionid=your-session-id' \
  -F 'file=@document.pdf' \
  -F 'is_inline=false'
```

**Example Response** (201 Created):
```json
{
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "size": 102400,
  "checksum": "sha256-abc123..."
}
```

**Validation**:
- Maximum file size: 25 MB
- All file types accepted

---

## Settings API

### Get User Settings

**`GET /api/v1/settings/`**

Get current user's email settings.

**Example Response** (200 OK):
```json
{
  "id": 1,
  "email_address": "user@qutemail.local",
  "display_name": "John Doe",
  "signature": "Best regards,\nJohn Doe",
  "enable_qkd_encryption": true,
  "auto_fetch_interval": 60,
  "storage_quota_mb": 1024,
  "storage_used_mb": 256,
  "storage_usage_mb": 256,
  "storage_usage_percentage": 25.0,
  "last_sync_at": "2025-01-29T11:00:00Z",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-29T11:00:00Z"
}
```

---

### Update Settings

**`PATCH /api/v1/settings/`**

Update user email settings.

**Request Body** (partial update):
```json
{
  "display_name": "John Smith",
  "signature": "Regards,\nJohn",
  "enable_qkd_encryption": false,
  "auto_fetch_interval": 120
}
```

**Editable Fields**:
- `display_name`
- `signature`
- `enable_qkd_encryption`
- `auto_fetch_interval` (seconds, 0 to disable)
- `storage_quota_mb`

**Read-Only Fields**:
- `email_address`
- `storage_used_mb`
- `last_sync_at`

**Example Response** (200 OK):
```json
{
  "id": 1,
  "email_address": "user@qutemail.local",
  "display_name": "John Smith",
  "enable_qkd_encryption": false,
  "auto_fetch_interval": 120
}
```

---

### Update Storage Usage

**`POST /api/v1/settings/update_storage/`**

Manually recalculate storage usage.

**Example Response** (200 OK):
```json
{
  "storage_used_mb": 256,
  "storage_quota_mb": 1024,
  "storage_usage_percentage": 25.0
}
```

---

## Labels API

### List Labels

**`GET /api/v1/labels/`**

List all labels for the authenticated user.

**Example Response** (200 OK):
```json
{
  "count": 3,
  "results": [
    {
      "id": 1,
      "name": "Important",
      "color": "#ff0000",
      "created_at": "2025-01-01T00:00:00Z"
    },
    {
      "id": 2,
      "name": "Work",
      "color": "#0000ff",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

---

### Create Label

**`POST /api/v1/labels/`**

Create a new label.

**Request Body**:
```json
{
  "name": "Personal",
  "color": "#00ff00"
}
```

**Example Response** (201 Created):
```json
{
  "id": 3,
  "name": "Personal",
  "color": "#00ff00",
  "created_at": "2025-01-29T11:00:00Z"
}
```

---

### Update Label

**`PATCH /api/v1/labels/{id}/`**

Update a label.

**Request Body**:
```json
{
  "name": "Personal Projects",
  "color": "#00aa00"
}
```

---

### Delete Label

**`DELETE /api/v1/labels/{id}/`**

Delete a label (removes from all emails).

**Example Response** (204 No Content)

---

### Apply Label to Emails

**`POST /api/v1/labels/{id}/apply/`**

Apply label to multiple emails.

**Request Body**:
```json
{
  "email_ids": [1, 2, 3]
}
```

**Example Response** (200 OK):
```json
{
  "status": "success",
  "label": "Important",
  "applied_to": 3
}
```

---

### Remove Label from Emails

**`POST /api/v1/labels/{id}/remove/`**

Remove label from multiple emails.

**Request Body**:
```json
{
  "email_ids": [1, 2, 3]
}
```

**Example Response** (200 OK):
```json
{
  "status": "success",
  "label": "Important",
  "removed_from": 3
}
```

---

## Error Responses

### 400 Bad Request

Invalid request data.

```json
{
  "to_addresses": ["This field is required."],
  "subject": ["This field may not be blank."]
}
```

### 401 Unauthorized

Not authenticated.

```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden

Not authorized to access resource.

```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found

Resource not found.

```json
{
  "detail": "Not found."
}
```

### 500 Internal Server Error

Server error.

```json
{
  "detail": "Internal server error. Please try again later."
}
```

---

## Rate Limiting

Currently no rate limiting is implemented. For production deployment, consider adding rate limiting using:
- Django REST Framework throttling
- Nginx rate limiting
- API Gateway rate limiting

---

## Pagination

All list endpoints use pagination with the following response format:

```json
{
  "count": 100,
  "next": "http://localhost:8000/api/v1/emails/?page=2",
  "previous": null,
  "results": [...]
}
```

Default page size: 50 items

Control pagination:
- `?page=2` - Get page 2
- `?page_size=100` - Get 100 items per page

---

## Filtering

Emails can be filtered using query parameters:

```bash
# Filter by folder
/api/v1/emails/?folder=inbox

# Filter by read status
/api/v1/emails/?is_read=false

# Filter by starred
/api/v1/emails/?is_starred=true

# Filter by encryption
/api/v1/emails/?is_encrypted=true

# Combine filters
/api/v1/emails/?folder=inbox&is_read=false&is_starred=true
```

---

## Searching

Use the `search` parameter to search across multiple fields:

```bash
# Search in subject, from_address, body_text
/api/v1/emails/?search=meeting

# Combine with filters
/api/v1/emails/?folder=inbox&search=important
```

---

## Ordering

Use the `ordering` parameter to sort results:

```bash
# Sort by date (ascending)
/api/v1/emails/?ordering=date

# Sort by date (descending)
/api/v1/emails/?ordering=-date

# Sort by size
/api/v1/emails/?ordering=size

# Sort by created_at
/api/v1/emails/?ordering=-created_at
```

Available ordering fields:
- `date`
- `created_at`
- `size`

---

## Field Selection

Currently, all fields are returned. For production, consider implementing field selection:

```bash
# Hypothetical field selection (not yet implemented)
/api/v1/emails/?fields=id,subject,from_address,date
```

---

## API Versioning

Current API version: **v1**

Base URL: `/api/v1/`

Future versions will be available at `/api/v2/`, etc.

---

## Webhooks (Future Feature)

Webhooks are not currently implemented but are planned for future releases.

Potential webhook events:
- `email.received`
- `email.sent`
- `email.failed`
- `email.decrypted`

---

## SDKs and Client Libraries

Currently no official SDKs. The API follows REST conventions and can be used with any HTTP client:

**Python**:
```python
import requests

# Login
session = requests.Session()
session.post('http://localhost:8000/api-auth/login/', data={
    'username': 'user',
    'password': 'pass'
})

# List emails
response = session.get('http://localhost:8000/api/v1/emails/')
emails = response.json()['results']

# Compose email
response = session.post('http://localhost:8000/api/v1/emails/', json={
    'to_addresses': ['recipient@qutemail.local'],
    'subject': 'Test',
    'body_text': 'Hello!',
    'encrypt': True
})
```

**JavaScript**:
```javascript
// Using fetch
const response = await fetch('http://localhost:8000/api/v1/emails/', {
  credentials: 'include',
  headers: {
    'Content-Type': 'application/json'
  }
});
const data = await response.json();
```

**cURL**:
```bash
# Login
curl -c cookies.txt -X POST \
  'http://localhost:8000/api-auth/login/' \
  -d 'username=user&password=pass'

# Use session
curl -b cookies.txt \
  'http://localhost:8000/api/v1/emails/'
```

---

## Browsable API

Django REST Framework provides a browsable HTML interface:

Visit `http://localhost:8000/api/v1/emails/` in your browser to:
- View API documentation
- Test API endpoints interactively
- See request/response examples
- Authenticate via web form

---

## OpenAPI/Swagger Documentation

To generate OpenAPI schema (future enhancement):

```python
# Install drf-spectacular
pip install drf-spectacular

# Add to INSTALLED_APPS in settings.py
INSTALLED_APPS = [
    ...
    'drf_spectacular',
]

# Add to urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

Then visit `http://localhost:8000/api/docs/` for interactive Swagger UI.
