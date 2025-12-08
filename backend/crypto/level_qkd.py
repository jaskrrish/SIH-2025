"""
QKD + AES security level
Obtains key via BB84 simulator (KM), then uses AES-256-GCM for encryption
"""

import base64
from . import level_aes
from km import client as km_client


def encrypt(
    plaintext: bytes,
    requester_sae: str,
    recipient_sae: str,
    associated_data: bytes = None,
    key_size: int = 256,
    **kwargs
) -> dict:
    """
    Encrypt using QKD-derived key + AES-256-GCM
    """

    message_id = kwargs.get("message_id")
    if not message_id:
        raise ValueError("message_id is required for QKD+AES encryption")

    # --- Request QKD key from Key Manager ---
    key_response = km_client.generate_key(
        requester_sae=requester_sae,
        recipient_sae=recipient_sae,
        key_size=key_size
    )

    key_id = key_response["key_id"]

    # Decode QKD key material
    key_material = base64.b64decode(key_response["key_material"])

    # Ensure 32 bytes for AES-256
    if len(key_material) != 32:
        key_material = (
            key_material[:32]
            if len(key_material) > 32
            else key_material.ljust(32, b"\x00")
        )

    # --- Derive AES key from QKD material using HKDF ---
    salt = f"{message_id}:{requester_sae}:{recipient_sae}".encode()
    aes_key = level_aes._derive_aes_key(key_material, salt)

    # --- AES encryption ---
    result = level_aes.encrypt(
        plaintext=plaintext,
        aes_key=aes_key,
        associated_data=associated_data,
        key_id=key_id,
        message_id=message_id
    )

    # --- Metadata ---
    result["metadata"]["algorithm"] = "QKD+AES-256-GCM"
    result["metadata"]["key_id"] = key_id
    result["metadata"]["qkd_algorithm"] = key_response["algorithm"]
    result["metadata"]["expiry"] = key_response["expiry"]

    return result


def decrypt(
    ciphertext: str,
    key_id: str,
    requester_sae: str,
    associated_data: bytes = None,
    mark_consumed: bool = True,
    **kwargs
) -> bytes:
    """
    Decrypt QKD+AES encrypted data
    """

    message_id = kwargs.get("message_id")
    if not message_id:
        raise ValueError("message_id is required for QKD+AES decryption")

    # --- Retrieve key from KM ---
    try:
        key_response = km_client.get_key_by_id(
            key_id=key_id,
            requester_sae=requester_sae,
            mark_consumed=mark_consumed
        )
    except ValueError as e:
        raise ValueError(f"Key retrieval failed: {str(e)}")

    key_material = base64.b64decode(key_response["key_material"])

    if len(key_material) != 32:
        key_material = (
            key_material[:32]
            if len(key_material) > 32
            else key_material.ljust(32, b"\x00")
        )

    # --- Derive AES key from QKD material using HKDF ---
    # Note: recipient_sae is in decrypt kwargs
    recipient_sae = kwargs.get("recipient_sae")
    if not recipient_sae:
        raise ValueError("recipient_sae is required for QKD+AES decryption")
    
    salt = f"{message_id}:{requester_sae}:{recipient_sae}".encode()
    aes_key = level_aes._derive_aes_key(key_material, salt)

    # --- AES decryption ---
    try:
        return level_aes.decrypt(
            ciphertext=ciphertext,
            aes_key=aes_key,
            associated_data=associated_data,
            key_id=key_id,
            message_id=message_id
        )
    except Exception as e:
        raise ValueError(f"Decryption failed: {str(e)}")
