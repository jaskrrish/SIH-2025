"""
API endpoints for sending and receiving emails.

These endpoints provide the main interface for QuteMail operations:
- /api/send/ - Send an email (with optional encryption via hooks)
- /api/receive/ - Receive and parse an email (with optional decryption via hooks)
"""

import json
import base64
from email import message_from_string
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Import pluggable hooks from qmailbox
from qmailbox import hooks
from qmailbox import smtp


@csrf_exempt
@require_http_methods(["POST"])
def send_email(request):
    """
    Send an email via SMTP with optional encryption.
    
    POST /api/send/
    Request body (JSON):
    {
        "from": "sender@example.com",
        "to": ["recipient1@example.com", "recipient2@example.com"],
        "subject": "Email subject",
        "body": "Email body text",
        "meta": {  // optional
            "security_level": "high",
            "priority": "urgent"
        },
        "smtp_config": {  // optional, for testing
            "host": "smtp.gmail.com",
            "port": 587,
            "username": "your-email@gmail.com",
            "password": "your-app-password",
            "use_tls": true
        }
    }
    
    Response (JSON):
    {
        "status": "sent",
        "encrypted": true,
        "info": {...}
    }
    """
    try:
        data = json.loads(request.body)
        
        # Extract required fields
        from_addr = data.get('from')
        to_addrs = data.get('to', [])
        subject = data.get('subject', '')
        body = data.get('body', '')
        meta = data.get('meta', {})
        smtp_config = data.get('smtp_config')
        
        # Validate required fields
        if not from_addr or not to_addrs:
            return JsonResponse({
                "status": "error",
                "message": "Missing required fields: 'from' and 'to'"
            }, status=400)
        
        # Convert body to bytes
        plaintext_bytes = body.encode('utf-8')
        
        # Call encryption hook (pluggable by crypto team)
        hook_result = hooks.encrypt_and_send_hook(plaintext_bytes, subject, meta)
        
        encrypted = False
        extra_headers = {}
        body_to_send = plaintext_bytes
        
        if hook_result is not None:
            # Hook returned encrypted content
            cipher_bytes, headers_dict = hook_result
            body_to_send = cipher_bytes
            extra_headers = headers_dict
            encrypted = True
        
        # Send via SMTP
        if smtp_config:
            # Use provided SMTP config (for testing)
            send_result = smtp.send_via_smtp(
                smtp_config,
                from_addr,
                to_addrs,
                subject,
                body_to_send,
                extra_headers
            )
        else:
            # Use mock sender for development (no real SMTP server needed)
            send_result = smtp.send_via_smtp_mock(
                from_addr,
                to_addrs,
                subject,
                body_to_send,
                extra_headers
            )
        
        return JsonResponse({
            "status": "sent",
            "encrypted": encrypted,
            "info": send_result
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            "status": "error",
            "message": "Invalid JSON in request body"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def receive_email(request):
    """
    Receive and parse an email with optional decryption.
    
    POST /api/receive/
    Request body (JSON):
    {
        "raw_mime": "From: sender@example.com\\nTo: recipient@example.com\\n...",
        // OR
        "raw_mime_base64": "base64-encoded-mime-message",
        "meta": {  // optional
            "source": "imap",
            "mailbox": "INBOX"
        }
    }
    
    Response (JSON):
    {
        "status": "ok",
        "subject": "Email subject",
        "body": "Email body (decrypted if applicable)",
        "from": "sender@example.com",
        "to": ["recipient@example.com"],
        "encrypted": true,
        "headers": {...}
    }
    """
    try:
        data = json.loads(request.body)
        
        # Get raw MIME message (plain or base64-encoded)
        raw_mime = data.get('raw_mime')
        raw_mime_base64 = data.get('raw_mime_base64')
        meta = data.get('meta', {})
        
        if raw_mime_base64:
            # Decode base64
            raw_mime = base64.b64decode(raw_mime_base64).decode('utf-8')
        
        if not raw_mime:
            return JsonResponse({
                "status": "error",
                "message": "Missing 'raw_mime' or 'raw_mime_base64' field"
            }, status=400)
        
        # Parse MIME message
        msg = message_from_string(raw_mime)
        
        # Extract headers
        headers = {}
        for key, value in msg.items():
            headers[key] = value
        
        subject = msg.get('Subject', '')
        from_addr = msg.get('From', '')
        to_addr = msg.get('To', '')
        
        # Extract body
        body_bytes = None
        if msg.is_multipart():
            # Get first text part
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    body_bytes = part.get_payload(decode=True)
                    break
        else:
            body_bytes = msg.get_payload(decode=True)
        
        if body_bytes is None:
            body_bytes = b''
        
        # Check for QuteMail encryption headers
        encrypted = headers.get('X-QuteMail-Encrypted', '').lower() == 'true'
        
        # Call decryption hook (pluggable by crypto team)
        hook_result = hooks.decrypt_and_deliver_hook(body_bytes, headers)
        
        if hook_result is not None:
            # Hook returned decrypted content
            subject = hook_result.get('subject', subject)
            body = hook_result.get('body', '')
        else:
            # No decryption, use plaintext
            try:
                body = body_bytes.decode('utf-8')
            except UnicodeDecodeError:
                body = base64.b64encode(body_bytes).decode('utf-8')
                body = f"[Binary content, base64 encoded]: {body}"
        
        return JsonResponse({
            "status": "ok",
            "subject": subject,
            "body": body,
            "from": from_addr,
            "to": to_addr.split(',') if to_addr else [],
            "encrypted": encrypted,
            "headers": headers
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            "status": "error",
            "message": "Invalid JSON in request body"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)
