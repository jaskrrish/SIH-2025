"""
QKD+PQC (Post-Quantum Cryptography) security level
Uses Kyber KEM for post-quantum key encapsulation + AES-256-GCM encryption

Flow:
1. SETUP: Receiver generates PQC keypair (public/private) via KM service
2. SENDER: Fetches receiver's public key
3. SENDER: Performs Kyber encapsulation -> (encapsulated_blob, shared_secret)
4. SENDER: Derives AES key from shared_secret using HKDF
5. SENDER: Encrypts email with AES-256-GCM
6. SENDER: Sends encapsulated_blob in email headers (X-QuteMail-KEM)
7. RECEIVER: Uses private key to decapsulate -> recovers shared_secret
8. RECEIVER: Derives same AES key via HKDF
9. RECEIVER: Decrypts email

Security: Protected against both classical and quantum attacks
"""
import base64
from typing import Optional
from kyber import Kyber768  # ML-KEM-768 (NIST Level 3)
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from . import level_aes
from .km_client import km_client


def derive_aes_key_from_shared_secret(shared_secret: bytes, info: bytes = b'QKD+PQC AES Key') -> bytes:
    """
    Derive AES-256 key from PQC shared secret using HKDF
    
    Args:
        shared_secret: Shared secret from Kyber encapsulation/decapsulation
        info: Context information for key derivation
    
    Returns:
        bytes: 32-byte AES-256 key
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bits for AES-256
        salt=None,  # Kyber output is already high entropy
        info=info,
        backend=default_backend()
    )
    return hkdf.derive(shared_secret)


def encrypt(plaintext: bytes, requester_sae: str, recipient_sae: str,
            associated_data: bytes = None, **kwargs) -> dict:
    """
    Encrypt using PQC KEM + AES-256-GCM
    
    Flow:
        1. Fetch receiver's PQC public key from KM service
        2. Perform Kyber encapsulation to get (encapsulated_blob, shared_secret)
        3. Derive AES-256 key from shared_secret via HKDF
        4. Encrypt plaintext with AES-256-GCM
        5. Return ciphertext + metadata (including encapsulated_blob)
    
    Args:
        plaintext: Data to encrypt
        requester_sae: Sender SAE identity (email address)
        recipient_sae: Recipient SAE identity (email address)
        associated_data: Additional authenticated data (AAD) for GCM
    
    Returns:
        dict: {
            'ciphertext': base64(nonce || ciphertext || tag),
            'metadata': {
                'algorithm': 'Kyber768+AES-256-GCM',
                'kem_algorithm': 'ML-KEM-768',
                'encapsulated_blob': base64(encapsulated_key),
                'nonce_size': 12,
                'tag_size': 16,
                'recipient_sae': recipient_sae
            }
        }
    
    Raises:
        Exception: If recipient's public key not found
    """
    # Step 1: Fetch receiver's PQC public key from KM service
    try:
        public_key_response = km_client.get_pqc_public_key(recipient_sae=recipient_sae)
        public_key_base64 = public_key_response['public_key']
        public_key_bytes = base64.b64decode(public_key_base64)
    except Exception as e:
        raise Exception(f"Failed to fetch PQC public key for {recipient_sae}: {str(e)}")
    
    # Step 2: Perform Kyber encapsulation
    # Returns: (encapsulated_key, shared_secret)
    encapsulated_key, shared_secret = Kyber768.enc(public_key_bytes)
    
    # Step 3: Derive AES-256 key from shared secret
    final_aes_key = derive_aes_key_from_shared_secret(shared_secret)
    
    # Step 4: Encrypt with AES-256-GCM (delegate to level_aes)
    aes_result = level_aes.encrypt(
        plaintext=plaintext,
        key_material=final_aes_key,
        associated_data=associated_data
    )
    
    # Step 5: Return ciphertext with PQC-specific metadata
    return {
        'ciphertext': aes_result['ciphertext'],
        'metadata': {
            'algorithm': 'Kyber768+AES-256-GCM',
            'kem_algorithm': 'ML-KEM-768',
            'encapsulated_blob': base64.b64encode(encapsulated_key).decode('utf-8'),
            'nonce_size': aes_result['metadata']['nonce_size'],
            'tag_size': aes_result['metadata']['tag_size'],
            'recipient_sae': recipient_sae
        }
    }


def decrypt(ciphertext: str, encapsulated_blob: str, requester_sae: str,
            associated_data: bytes = None, **kwargs) -> bytes:
    """
    Decrypt using PQC KEM + AES-256-GCM
    
    Flow:
        1. Fetch requester's PQC private key from KM service
        2. Perform Kyber decapsulation to recover shared_secret
        3. Derive AES-256 key from shared_secret via HKDF (same as sender)
        4. Decrypt ciphertext with AES-256-GCM
        5. Return plaintext
    
    Args:
        ciphertext: Base64-encoded encrypted data (nonce || ciphertext || tag)
        encapsulated_blob: Base64-encoded Kyber encapsulated key
        requester_sae: Decryptor SAE identity (must be recipient)
        associated_data: Additional authenticated data (AAD) for GCM
    
    Returns:
        bytes: Decrypted plaintext
    
    Raises:
        Exception: If private key not found or decryption fails
    """
    # Step 1: Fetch requester's PQC private key from KM service
    try:
        private_key_response = km_client.get_pqc_private_key(user_sae=requester_sae)
        private_key_base64 = private_key_response['private_key']
        private_key_bytes = base64.b64decode(private_key_base64)
    except Exception as e:
        raise Exception(f"Failed to fetch PQC private key for {requester_sae}: {str(e)}")
    
    # Step 2: Decode encapsulated blob
    encapsulated_key = base64.b64decode(encapsulated_blob)
    
    # Step 3: Perform Kyber decapsulation to recover shared secret
    shared_secret = Kyber768.dec(encapsulated_key, private_key_bytes)
    
    # Step 4: Derive AES-256 key (same derivation as sender)
    final_aes_key = derive_aes_key_from_shared_secret(shared_secret)
    
    # Step 5: Decrypt with AES-256-GCM (delegate to level_aes)
    plaintext = level_aes.decrypt(
        ciphertext=ciphertext,
        key_material=final_aes_key,
        associated_data=associated_data
    )
    
    return plaintext
