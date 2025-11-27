"""
Celery tasks for asynchronous email processing
"""
from celery import shared_task
from apps.qkd.services import QKDService
from apps.crypto.utils import hybrid_encrypt, hybrid_decrypt
from apps.infra.smtp_client import SMTPClient
from apps.infra.imap_client import IMAPClient


@shared_task
def send_encrypted_email(from_addr, to_addrs, subject, body, username=None, password=None):
    """
    Asynchronously send an encrypted email
    
    Args:
        from_addr: Sender email
        to_addrs: List of recipients
        subject: Email subject
        body: Email body
        username: SMTP username
        password: SMTP password
    """
    try:
        # Request QKD key
        qkd_service = QKDService()
        key_data = qkd_service.request_key(key_size=256)
        qkd_key = bytes.fromhex(key_data['key_material'])
        
        # Encrypt body
        encrypted_data = hybrid_encrypt(body.encode(), qkd_key)
        
        # Prepare encrypted email body
        encrypted_body = f"[ENCRYPTED MESSAGE]\nKey ID: {key_data['key_id']}\nCiphertext: {encrypted_data['ciphertext']}\nNonce: {encrypted_data['nonce']}\nTag: {encrypted_data['tag']}"
        
        # Send email
        smtp_client = SMTPClient()
        success = smtp_client.send_email(
            from_addr=from_addr,
            to_addrs=to_addrs,
            subject=f"[QKD-ENCRYPTED] {subject}",
            body=encrypted_body,
            username=username,
            password=password
        )
        
        return {
            'success': success,
            'key_id': key_data['key_id'],
            'message': 'Email sent successfully' if success else 'Failed to send email'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def fetch_and_decrypt_emails(username, password, folder='INBOX', limit=10):
    """
    Asynchronously fetch and decrypt emails
    
    Args:
        username: IMAP username
        password: IMAP password
        folder: Mailbox folder
        limit: Max emails to fetch
    """
    try:
        imap_client = IMAPClient()
        emails = imap_client.fetch_emails(username, password, folder, limit)
        
        qkd_service = QKDService()
        decrypted_emails = []
        
        for email_data in emails:
            # Check if email is encrypted
            if '[QKD-ENCRYPTED]' in email_data.get('subject', ''):
                try:
                    # Parse encrypted data from body
                    body = email_data['body']
                    
                    # Extract key_id, ciphertext, nonce, tag
                    lines = body.split('\n')
                    key_id = lines[1].split(': ')[1]
                    ciphertext = lines[2].split(': ')[1]
                    nonce = lines[3].split(': ')[1]
                    tag = lines[4].split(': ')[1]
                    
                    # Get QKD key
                    key_data = qkd_service.get_key_by_id(key_id)
                    qkd_key = bytes.fromhex(key_data['key_material'])
                    
                    # Decrypt
                    encrypted_data = {
                        'ciphertext': ciphertext,
                        'nonce': nonce,
                        'tag': tag
                    }
                    
                    plaintext = hybrid_decrypt(encrypted_data, qkd_key)
                    email_data['decrypted_body'] = plaintext.decode()
                    email_data['encrypted'] = True
                    
                except Exception as e:
                    email_data['decryption_error'] = str(e)
                    email_data['encrypted'] = True
            else:
                email_data['encrypted'] = False
            
            decrypted_emails.append(email_data)
        
        return {
            'success': True,
            'emails': decrypted_emails
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def process_incoming_mail():
    """
    Periodic task to process incoming mail
    Can be scheduled with Celery Beat
    """
    # TODO: Implement periodic mail processing
    pass
