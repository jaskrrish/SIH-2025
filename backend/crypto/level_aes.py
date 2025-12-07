"""
Standard AES-256-GCM encryption/decryption
Uses locally-derived symmetric key
"""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


def derive_key_from_passphrase(passphrase: str, salt: bytes = None) -> tuple:
    """
    Derive AES-256 key from passphrase using PBKDF2
    
    Args:
        passphrase: User passphrase
        salt: Salt for key derivation (generated if None)
    
    Returns:
        tuple: (key_bytes, salt_bytes)
    """
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bits
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = kdf.derive(passphrase.encode('utf-8'))
    return key, salt


def encrypt(plaintext: bytes, key_material: bytes = None, passphrase: str = None, 
            associated_data: bytes = None, **kwargs) -> dict:
    """
    Encrypt using AES-256-GCM
    
    Args:
        plaintext: Data to encrypt
        key_material: 32-byte key (if provided)
        passphrase: Passphrase to derive key (if key_material not provided)
        associated_data: Additional authenticated data (AAD) for GCM
    
    Returns:
        dict: {
            'ciphertext': base64(nonce || ciphertext || tag),
            'metadata': {
                'algorithm': 'AES-256-GCM',
                'salt': base64(salt) if passphrase used,
                'nonce_size': 12,
                'tag_size': 16
            }
        }
    """
    metadata = {
        'algorithm': 'AES-256-GCM',
        'nonce_size': 12,
        'tag_size': 16
    }
    
    # Get or derive key
    if key_material:
        if len(key_material) != 32:
            raise ValueError("key_material must be 32 bytes for AES-256")
        key = key_material
    elif passphrase:
        key, salt = derive_key_from_passphrase(passphrase)
        metadata['salt'] = base64.b64encode(salt).decode('utf-8')
    else:
        # Generate random key
        key = os.urandom(32)
        metadata['key'] = base64.b64encode(key).decode('utf-8')
    
    # Generate nonce (96 bits for GCM)
    nonce = os.urandom(12)
    
    # Create AESGCM cipher
    aesgcm = AESGCM(key)
    
    # Encrypt (returns ciphertext + tag)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, associated_data)
    
    # Package: nonce || ciphertext+tag
    encrypted_blob = nonce + ciphertext_with_tag
    
    return {
        'ciphertext': base64.b64encode(encrypted_blob).decode('utf-8'),
        'metadata': metadata
    }


def decrypt(ciphertext: str, key_material: bytes = None, passphrase: str = None,
            salt: bytes = None, associated_data: bytes = None, **kwargs) -> bytes:
    """
    Decrypt AES-256-GCM encrypted data
    
    Args:
        ciphertext: Base64 encoded (nonce || ciphertext || tag)
        key_material: 32-byte key
        passphrase: Passphrase to derive key
        salt: Salt for key derivation (required if passphrase used)
        associated_data: AAD used during encryption
    
    Returns:
        bytes: Decrypted plaintext
    
    Raises:
        ValueError: If authentication fails or invalid parameters
    """
    # Decode base64
    encrypted_blob = base64.b64decode(ciphertext)
    
    # Extract nonce (first 12 bytes)
    nonce = encrypted_blob[:12]
    ciphertext_with_tag = encrypted_blob[12:]
    
    # Get or derive key
    if key_material:
        if len(key_material) != 32:
            raise ValueError("key_material must be 32 bytes for AES-256")
        key = key_material
    elif passphrase:
        if not salt:
            raise ValueError("salt required for passphrase-based decryption")
        key, _ = derive_key_from_passphrase(passphrase, salt)
    else:
        raise ValueError("Either key_material or passphrase+salt must be provided")
    
    # Create AESGCM cipher
    aesgcm = AESGCM(key)
    
    try:
        # Decrypt and verify tag
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, associated_data)
        return plaintext
    except Exception as e:
        raise ValueError(f"Decryption failed (authentication failed): {str(e)}")
