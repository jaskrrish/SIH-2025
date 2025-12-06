# Crypto Module - Multi-Level Encryption System

The crypto module provides pluggable encryption/decryption with 4 security levels:
- **Regular** - No encryption (passthrough)
- **Standard AES** - AES-256-GCM encryption
- **QKD+AES** - Quantum Key Distribution with AES-256-GCM
- **QRNG+PQC** - Quantum Random Number Generator with Post-Quantum Cryptography (stub)

## 📁 Module Structure

```
crypto/
├── __init__.py           # Module initialization
├── router.py             # Security level dispatcher
├── level_regular.py      # No encryption
├── level_aes.py          # AES-256-GCM implementation
├── level_qkd.py          # QKD+AES implementation
└── level_qrng_pqc.py     # QRNG+PQC stub
```

## 🔌 Router Interface

### Encrypt
```python
from crypto import router

result = router.encrypt(
    security_level='qkd',
    plaintext=b'Hello, World!',
    requester_sae='alice@example.com',
    recipient_sae='bob@example.com'
)

# Returns:
# {
#     'ciphertext': 'base64...',
#     'metadata': {
#         'security_level': 'qkd',
#         'algorithm': 'QKD+AES-256-GCM',
#         'key_id': 'uuid',
#         'nonce_size': 12,
#         'tag_size': 16,
#         'expiry': 1701791400
#     }
# }
```

### Decrypt
```python
plaintext = router.decrypt(
    security_level='qkd',
    ciphertext='base64...',
    key_id='uuid',
    requester_sae='bob@example.com'
)

# Returns: b'Hello, World!'
```

---

## 🔐 Security Levels

### 1. Regular (No Encryption)
**Module:** `level_regular.py`

Simple passthrough - no encryption applied.

```python
encrypt(plaintext) -> {'ciphertext': plaintext, 'metadata': {}}
decrypt(ciphertext) -> ciphertext
```

---

### 2. Standard AES (AES-256-GCM)
**Module:** `level_aes.py`

Uses AES-256-GCM with randomly generated keys.

**Encryption:**
```python
result = level_aes.encrypt(
    plaintext=b'Secret message',
    # Optional: key_material (32 bytes)
    # Optional: passphrase (will derive key with PBKDF2)
)

# If neither key_material nor passphrase provided:
# - Generates random 32-byte key
# - Stores key in metadata['key'] (base64)
# - Generates 12-byte nonce
# - Returns: base64(nonce || ciphertext || tag)
```

**Key Storage:**
- Key transmitted in `X-QuteMail-AES-Key` email header
- For production: use key exchange or encrypt the key

**Decryption:**
```python
plaintext = level_aes.decrypt(
    ciphertext='base64...',
    key_material=base64.b64decode(key_b64)
)
```

---

### 3. QKD+AES (Quantum Key Distribution)
**Module:** `level_qkd.py`

Uses BB84 QKD simulator to generate key pairs, then encrypts with AES-256-GCM.

**Encryption Flow:**
```python
result = level_qkd.encrypt(
    plaintext=b'Secret message',
    requester_sae='alice@example.com',
    recipient_sae='bob@example.com'
)

# 1. Calls km_client.generate_key() -> BB84 simulator
# 2. Gets alice_key (sender) and stores bob_key (recipient)
# 3. Encrypts with AES-256-GCM using alice_key
# 4. Returns ciphertext + metadata with key_id
```

**Key Management:**
- **Alice Key**: Used by sender for encryption
- **Bob Key**: Stored in KM, used by recipient for decryption
- **Key ID**: UUID linking sender/recipient keys
- **Authorization**: Only recipient can retrieve bob_key
- **OTP Semantics**: Key consumed after first use

**Decryption Flow:**
```python
plaintext = level_qkd.decrypt(
    ciphertext='base64...',
    key_id='uuid',
    requester_sae='bob@example.com',
    mark_consumed=True
)

# 1. Calls km_client.get_key_by_id() with authorization check
# 2. Retrieves bob_key (must be recipient)
# 3. Decrypts with AES-256-GCM
# 4. Marks key as consumed
```

---

### 4. QRNG+PQC (Post-Quantum Cryptography)
**Module:** `level_qrng_pqc.py`

Placeholder for future implementation.

```python
encrypt() -> raises NotImplementedError("Coming soon")
decrypt() -> raises NotImplementedError("Coming soon")
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
