"""
SMTP email sending helper.

Provides a minimal interface for sending emails via SMTP. Supports both
app passwords and OAuth2 (commented out for now).
"""

import smtplib
from email.message import EmailMessage
from typing import List, Dict, Optional


def send_via_smtp(
    smtp_conf: Dict[str, str],
    from_addr: str,
    to_addrs: List[str],
    subject: str,
    body_bytes: bytes,
    extra_headers: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """
    Send an email via SMTP.
    
    Args:
        smtp_conf: SMTP configuration dict with keys:
            - 'host': SMTP server hostname (e.g., 'smtp.gmail.com')
            - 'port': SMTP server port (e.g., 587 for TLS)
            - 'username': SMTP username/email
            - 'password': SMTP password (app password for Gmail)
            - 'use_tls': True/False
        from_addr: Sender email address
        to_addrs: List of recipient email addresses
        subject: Email subject
        body_bytes: Email body as bytes (could be plaintext or encrypted)
        extra_headers: Optional dict of additional headers (e.g., X-QuteMail-*)
    
    Returns:
        Dict with status information:
            {"status": "sent", "message_id": "...", "recipients": [...]}
    
    Raises:
        smtplib.SMTPException: On SMTP errors
        
    Note for OAuth2:
        For Gmail OAuth2, you would:
        1. Use google-auth-oauthlib to get access token
        2. Use `smtp.auth('XOAUTH2', lambda: oauth_string)`
        3. See: https://developers.google.com/gmail/imap/xoauth2-protocol
    """
    # Create email message
    msg = EmailMessage()
    msg['From'] = from_addr
    msg['To'] = ', '.join(to_addrs)
    msg['Subject'] = subject
    
    # Add custom headers if provided (e.g., X-QuteMail-Encrypted, X-QuteMail-Key-ID)
    if extra_headers:
        for key, value in extra_headers.items():
            msg[key] = value
    
    # Set body content
    # If body_bytes is encrypted, it will be sent as-is
    # If plaintext, it will be sent as text/plain
    try:
        # Try to decode as UTF-8 for plaintext
        msg.set_content(body_bytes.decode('utf-8'))
    except UnicodeDecodeError:
        # If decode fails, it's likely encrypted binary data
        # Send as application/octet-stream
        msg.set_content(body_bytes, maintype='application', subtype='octet-stream')
    
    # Connect and send
    try:
        smtp_host = smtp_conf.get('host', 'smtp.gmail.com')
        smtp_port = int(smtp_conf.get('port', 587))
        use_tls = smtp_conf.get('use_tls', True)
        
        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            if use_tls:
                smtp.starttls()
            
            # Login if credentials provided
            username = smtp_conf.get('username')
            password = smtp_conf.get('password')
            if username and password:
                smtp.login(username, password)
            
            # Send email
            smtp.send_message(msg)
            
        return {
            "status": "sent",
            "message_id": msg.get('Message-ID', 'unknown'),
            "recipients": to_addrs
        }
        
    except smtplib.SMTPException as e:
        raise Exception(f"SMTP Error: {str(e)}")


# Example configuration for development/testing
EXAMPLE_SMTP_CONFIG = {
    'host': 'smtp.gmail.com',
    'port': 587,
    'username': 'techchesssurya@gmail.com',
    'password': 'your-app-password',  # Use app password, not regular password
    'use_tls': True
}

# For testing without real SMTP (prints instead of sending):
def send_via_smtp_mock(from_addr, to_addrs, subject, body_bytes, extra_headers=None):
    """Mock SMTP sender for testing without real email server."""
    print(f"[MOCK SMTP] From: {from_addr}")
    print(f"[MOCK SMTP] To: {to_addrs}")
    print(f"[MOCK SMTP] Subject: {subject}")
    print(f"[MOCK SMTP] Body length: {len(body_bytes)} bytes")
    if extra_headers:
        print(f"[MOCK SMTP] Extra headers: {extra_headers}")
    return {
        "status": "sent_mock",
        "message_id": "mock-message-id",
        "recipients": to_addrs
    }
