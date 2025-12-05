# Crypto App - Expected Interface

This directory is reserved for the cryptography implementation team. The crypto app should provide encryption and decryption functions that can be integrated with the QuteMail system.

## Expected Interface

The crypto team should implement the following functions:

```python
def encrypt(plaintext_bytes: bytes, level: str, key_material: dict) -> bytes:
    """
    Encrypt plaintext data using quantum-safe cryptography.
    
    Args:
        plaintext_bytes: The data to encrypt (email body, attachments, etc.)
        level: Security level ('standard', 'high', 'quantum-safe')
        key_material: Dictionary containing:
            - 'key': Base64-encoded encryption key (from KM service)
            - 'keyId': Key identifier for later retrieval
            - 'algorithm': Preferred algorithm (e.g., 'AES-256-GCM', 'ChaCha20-Poly1305')
    
    Returns:
        Encrypted data as bytes
    
    Example:
        key_response = requests.post('http://localhost:8000/api/km/get_key/')
        key_data = key_response.json()
        
        cipher_bytes = encrypt(
            plaintext_bytes=b"Secret email content",
            level="quantum-safe",
            key_material={
                'key': key_data['key'],
                'keyId': key_data['keyId'],
                'algorithm': 'AES-256-GCM'
            }
        )
    """
    pass


def decrypt(cipher_bytes: bytes, level: str, key_material: dict) -> bytes:
    """
    Decrypt ciphertext data.
    
    Args:
        cipher_bytes: The encrypted data to decrypt
        level: Security level used during encryption
        key_material: Dictionary containing:
            - 'key': Base64-encoded decryption key (from KM service)
            - 'keyId': Key identifier
            - 'algorithm': Algorithm used for encryption
    
    Returns:
        Decrypted plaintext as bytes
    
    Example:
        key_response = requests.post('http://localhost:8000/api/km/get_key_with_id/',
                                     json={'keyId': key_id})
        key_data = key_response.json()
        
        plaintext_bytes = decrypt(
            cipher_bytes=encrypted_data,
            level="quantum-safe",
            key_material={
                'key': key_data['key'],
                'keyId': key_data['keyId'],
                'algorithm': 'AES-256-GCM'
            }
        )
    """
    pass
```

## Integration with QuteMail

To integrate your crypto implementation with QuteMail, you need to modify the hooks in `qmailbox/hooks.py`:

```python
# In qmailbox/hooks.py
from crypto import encrypt, decrypt
import requests
import base64

def encrypt_and_send_hook(plaintext_bytes, subject, meta=None):
    """Replace this function with your encryption logic."""
    # Get key from KM service
    key_response = requests.post('http://localhost:8000/api/km/get_key/')
    key_data = key_response.json()
    
    # Encrypt using your crypto module
    from crypto import encrypt
    cipher_bytes = encrypt(
        plaintext_bytes=plaintext_bytes,
        level=meta.get('security_level', 'standard'),
        key_material={
            'key': key_data['key'],
            'keyId': key_data['keyId'],
            'algorithm': 'AES-256-GCM'
        }
    )
    
    # Return cipher and custom headers
    headers = {
        'X-QuteMail-Encrypted': 'true',
        'X-QuteMail-Key-ID': key_data['keyId'],
        'X-QuteMail-Algorithm': 'AES-256-GCM',
        'X-QuteMail-Level': meta.get('security_level', 'standard')
    }
    return (cipher_bytes, headers)


def decrypt_and_deliver_hook(cipher_bytes, headers):
    """Replace this function with your decryption logic."""
    # Check if encrypted
    if headers.get('X-QuteMail-Encrypted') != 'true':
        return None
    
    # Get key from KM service using key ID
    key_id = headers.get('X-QuteMail-Key-ID')
    key_response = requests.post('http://localhost:8000/api/km/get_key_with_id/',
                                 json={'keyId': key_id})
    key_data = key_response.json()
    
    # Decrypt using your crypto module
    from crypto import decrypt
    plaintext_bytes = decrypt(
        cipher_bytes=cipher_bytes,
        level=headers.get('X-QuteMail-Level', 'standard'),
        key_material={
            'key': key_data['key'],
            'keyId': key_data['keyId'],
            'algorithm': headers.get('X-QuteMail-Algorithm', 'AES-256-GCM')
        }
    )
    
    # Parse and return
    return {
        'subject': headers.get('Subject', ''),
        'body': plaintext_bytes.decode('utf-8')
    }
```

## Recommended Cryptographic Approaches

### Option 1: Hybrid Classical + Quantum-Safe
- Use AES-256-GCM for fast symmetric encryption
- Use key material from QKD for symmetric keys
- Consider post-quantum algorithms for key exchange (e.g., Kyber, Dilithium)

### Option 2: Direct QKD Key Usage
- Use keys directly from QKD hardware
- Implement one-time pad or stream cipher
- Ensure proper key consumption and tracking

### Option 3: Layered Security
- Multiple encryption passes with different algorithms
- Defense in depth approach
- Support for legacy compatibility

## Dependencies

Consider using these libraries:
- `cryptography` - Modern cryptographic recipes and primitives
- `pqcrypto` - Post-quantum cryptography
- `etsi-qkd-014-client` - Already installed for KM integration

## Testing

Create unit tests in `crypto/tests.py`:
```python
import unittest
from .crypto_module import encrypt, decrypt

class CryptoTests(unittest.TestCase):
    def test_encrypt_decrypt_roundtrip(self):
        plaintext = b"Hello, Quantum World!"
        key_material = {
            'key': 'base64encodedkey...',
            'keyId': 'test-key-id',
            'algorithm': 'AES-256-GCM'
        }
        
        cipher = encrypt(plaintext, 'standard', key_material)
        decrypted = decrypt(cipher, 'standard', key_material)
        
        self.assertEqual(plaintext, decrypted)
```

## Questions?

Contact the QuteMail integration team or refer to:
- `qmailbox/hooks.py` - Hook integration points
- `api/views.py` - How hooks are called
- `km/views.py` - Key management simulator
