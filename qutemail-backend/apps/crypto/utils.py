"""
Cryptographic utilities for QKD-based email encryption
Includes HKDF, AES, and One-Time Pad implementations
"""
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from typing import Tuple


def derive_key(master_key: bytes, info: bytes = b'', salt: bytes = None, length: int = 32) -> bytes:
    """
    Derive a key using HKDF (HMAC-based Key Derivation Function)
    
    Args:
        master_key: Master key material (from QKD)
        info: Application-specific context information
        salt: Optional salt value
        length: Desired output key length in bytes
        
    Returns:
        Derived key material
    """
    if salt is None:
        salt = os.urandom(16)
    
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        info=info,
        backend=default_backend()
    )
    
    return hkdf.derive(master_key)


def aes_gcm_encrypt(plaintext: bytes, key: bytes) -> Tuple[bytes, bytes, bytes]:
    """
    Encrypt data using AES-256-GCM
    
    Args:
        plaintext: Data to encrypt
        key: 256-bit encryption key
        
    Returns:
        Tuple of (ciphertext, nonce, tag)
    """
    # Generate random nonce
    nonce = os.urandom(12)
    
    # Create cipher
    cipher = Cipher(
        algorithms.AES(key),
        modes.GCM(nonce),
        backend=default_backend()
    )
    
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    
    return ciphertext, nonce, encryptor.tag


def aes_gcm_decrypt(ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes) -> bytes:
    """
    Decrypt data using AES-256-GCM
    
    Args:
        ciphertext: Encrypted data
        key: 256-bit decryption key
        nonce: Nonce used during encryption
        tag: Authentication tag
        
    Returns:
        Decrypted plaintext
    """
    cipher = Cipher(
        algorithms.AES(key),
        modes.GCM(nonce, tag),
        backend=default_backend()
    )
    
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    
    return plaintext


def otp_encrypt(plaintext: bytes, key: bytes) -> bytes:
    """
    Encrypt using One-Time Pad (XOR cipher)
    Note: Key must be at least as long as plaintext and truly random (e.g., from QKD)
    
    Args:
        plaintext: Data to encrypt
        key: One-time pad key (must be >= len(plaintext))
        
    Returns:
        Ciphertext
    """
    if len(key) < len(plaintext):
        raise ValueError("Key must be at least as long as plaintext for OTP")
    
    # XOR plaintext with key
    ciphertext = bytes(p ^ k for p, k in zip(plaintext, key))
    return ciphertext


def otp_decrypt(ciphertext: bytes, key: bytes) -> bytes:
    """
    Decrypt using One-Time Pad (XOR cipher)
    
    Args:
        ciphertext: Encrypted data
        key: One-time pad key
        
    Returns:
        Plaintext
    """
    if len(key) < len(ciphertext):
        raise ValueError("Key must be at least as long as ciphertext for OTP")
    
    # XOR ciphertext with key (same operation as encryption)
    plaintext = bytes(c ^ k for c, k in zip(ciphertext, key))
    return plaintext


def hybrid_encrypt(plaintext: bytes, qkd_key: bytes) -> dict:
    """
    Hybrid encryption: Use QKD key with AES-GCM
    
    Args:
        plaintext: Data to encrypt
        qkd_key: Quantum-generated key material
        
    Returns:
        Dict containing ciphertext, nonce, tag, and metadata
    """
    # Derive encryption key from QKD key
    encryption_key = derive_key(qkd_key, info=b'email-encryption', length=32)
    
    # Encrypt with AES-GCM
    ciphertext, nonce, tag = aes_gcm_encrypt(plaintext, encryption_key)
    
    return {
        'ciphertext': ciphertext.hex(),
        'nonce': nonce.hex(),
        'tag': tag.hex(),
        'algorithm': 'AES-256-GCM',
        'kdf': 'HKDF-SHA256'
    }


def hybrid_decrypt(encrypted_data: dict, qkd_key: bytes) -> bytes:
    """
    Hybrid decryption: Use QKD key with AES-GCM
    
    Args:
        encrypted_data: Dict with ciphertext, nonce, tag
        qkd_key: Quantum-generated key material
        
    Returns:
        Decrypted plaintext
    """
    # Derive encryption key from QKD key
    encryption_key = derive_key(qkd_key, info=b'email-encryption', length=32)
    
    # Convert hex strings back to bytes
    ciphertext = bytes.fromhex(encrypted_data['ciphertext'])
    nonce = bytes.fromhex(encrypted_data['nonce'])
    tag = bytes.fromhex(encrypted_data['tag'])
    
    # Decrypt with AES-GCM
    plaintext = aes_gcm_decrypt(ciphertext, encryption_key, nonce, tag)
    
    return plaintext
