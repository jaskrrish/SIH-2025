"""
QKD + AES security level
Obtains key via BB84 simulator (KM), then uses AES-256-GCM for encryption
"""
import base64
from typing import Optional
from . import level_aes
from km import client as km_client


def encrypt(plaintext: bytes, requester_sae: str, recipient_sae: str,
            associated_data: bytes = None, key_size: int = 256, **kwargs) -> dict:
    """
    Encrypt using QKD-derived key + AES-256-GCM
    
    Args:
        plaintext: Data to encrypt
        requester_sae: Sender SAE identity
        recipient_sae: Recipient SAE identity
        associated_data: Additional authenticated data (AAD) for GCM
        key_size: QKD key size in bits
    
    Returns:
        dict: {
            'ciphertext': base64(nonce || ciphertext || tag),
            'metadata': {
                'algorithm': 'QKD+AES-256-GCM',
                'key_id': '<uuid>',
                'qkd_algorithm': 'BB84',
                'nonce_size': 12,
                'tag_size': 16
            }
        }
    """
    # Request QKD key from Key Manager
    key_response = km_client.generate_key(
        requester_sae=requester_sae,
        recipient_sae=recipient_sae,
        key_size=key_size
    )
    
    # Decode key material
    key_material = base64.b64decode(key_response['key_material'])
    
    # Ensure key is 32 bytes (256 bits) for AES-256
    if len(key_material) != 32:
        # Truncate or pad if needed (ideally should always be 32 bytes)
        key_material = key_material[:32] if len(key_material) > 32 else key_material.ljust(32, b'\x00')
    
    # Use AES encryption with QKD-derived key
    result = level_aes.encrypt(
        plaintext=plaintext,
        key_material=key_material,
        associated_data=associated_data
    )
    
    # Update metadata
    result['metadata']['algorithm'] = 'QKD+AES-256-GCM'
    result['metadata']['key_id'] = key_response['key_id']
    result['metadata']['qkd_algorithm'] = key_response['algorithm']
    result['metadata']['expiry'] = key_response['expiry']
    
    return result


def decrypt(ciphertext: str, key_id: str, requester_sae: str,
            associated_data: bytes = None, mark_consumed: bool = True, **kwargs) -> bytes:
    """
    Decrypt QKD+AES encrypted data
    
    Args:
        ciphertext: Base64 encoded (nonce || ciphertext || tag)
        key_id: Key identifier from encryption metadata
        requester_sae: Recipient SAE identity (must match key's intended recipient)
        associated_data: AAD used during encryption
        mark_consumed: Mark key as consumed after use (OTP semantics)
    
    Returns:
        bytes: Decrypted plaintext
    
    Raises:
        ValueError: If key not found, expired, unauthorized, or authentication fails
    """
    # Retrieve key from Key Manager (with authorization check)
    # Don't mark as consumed yet - only mark after successful decryption
    try:
        key_response = km_client.get_key_by_id(
            key_id=key_id,
            requester_sae=requester_sae,
            mark_consumed=False  # Get key first without consuming
        )
    except ValueError as e:
        raise ValueError(f"Key retrieval failed: {str(e)}")
    
    # Decode key material
    key_material = base64.b64decode(key_response['key_material'])
    
    # Ensure key is 32 bytes for AES-256
    if len(key_material) != 32:
        key_material = key_material[:32] if len(key_material) > 32 else key_material.ljust(32, b'\x00')
    
    # Use AES decryption
    try:
        plaintext = level_aes.decrypt(
            ciphertext=ciphertext,
            key_material=key_material,
            associated_data=associated_data
        )
        
        # Only mark key as consumed AFTER successful decryption
        if mark_consumed:
            km_client.get_key_by_id(
                key_id=key_id,
                requester_sae=requester_sae,
                mark_consumed=True  # Now mark as consumed
            )
        
        return plaintext
    except ValueError as e:
        # Decryption failed - don't mark key as consumed so it can be retried
        raise ValueError(f"Decryption failed: {str(e)}")
