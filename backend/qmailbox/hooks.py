"""
Pluggable hooks for encryption/decryption integration.

These hooks allow the crypto team to integrate their encryption implementation
without modifying the core API logic. Replace these functions with actual
implementations when ready.

Integration options:
1. Direct replacement: Import and replace these functions in your code
2. Environment-based: Use environment variables to point to implementation modules
3. HTTP endpoints: Make these hooks call HTTP endpoints provided by crypto service
"""

def encrypt_and_send_hook(plaintext_bytes, subject, meta=None):
    """
    Hook for encrypting email content before sending.
    
    Args:
        plaintext_bytes (bytes): The email body as bytes
        subject (str): Email subject
        meta (dict): Optional metadata (recipient info, security level, etc.)
    
    Returns:
        tuple: (cipher_bytes, headers_dict) if encryption is applied
        None: if plaintext should be sent (no encryption)
    
    Example implementation by crypto team:
        # Get key from KM service
        key_response = requests.post('http://localhost:8000/api/km/get_key/')
        key_data = key_response.json()
        
        # Encrypt using your crypto module
        cipher_bytes = your_crypto.encrypt(plaintext_bytes, key_data['key'])
        
        # Return cipher and custom headers
        headers = {
            'X-QuteMail-Encrypted': 'true',
            'X-QuteMail-Key-ID': key_data['keyId'],
            'X-QuteMail-Algorithm': 'AES-256-GCM'
        }
        return (cipher_bytes, headers)
    """
    # Default: no encryption, send plaintext
    return None


def decrypt_and_deliver_hook(cipher_bytes, headers):
    """
    Hook for decrypting received email content.
    
    Args:
        cipher_bytes (bytes): The encrypted email body
        headers (dict): Email headers (may contain X-QuteMail-* fields)
    
    Returns:
        dict: {"subject": str, "body": str} if decryption is successful
        None: if no decryption needed or headers indicate plaintext
    
    Example implementation by crypto team:
        # Check if encrypted
        if headers.get('X-QuteMail-Encrypted') != 'true':
            return None
        
        # Get key from KM service using key ID
        key_id = headers.get('X-QuteMail-Key-ID')
        key_response = requests.post('http://localhost:8000/api/km/get_key_with_id/',
                                     json={'keyId': key_id})
        key_data = key_response.json()
        
        # Decrypt using your crypto module
        plaintext_bytes = your_crypto.decrypt(cipher_bytes, key_data['key'])
        
        # Parse and return
        return {
            'subject': 'Decrypted: ' + headers.get('Subject', ''),
            'body': plaintext_bytes.decode('utf-8')
        }
    """
    # Default: no decryption
    return None
