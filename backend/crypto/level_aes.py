import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


def _derive_aes_key(qkd_key: bytes, salt: bytes) -> bytes:
    """
    Derive final AES-256 key from QKD material using HKDF
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,  # AES-256
        salt=salt,
        info=b"qutemail-aes"
    )
    return hkdf.derive(qkd_key)


def encrypt(
    plaintext: bytes,
    aes_key: bytes,
    associated_data: bytes = None,
    *,
    key_id: str,
    message_id: str
) -> dict:
    """
    AES-256-GCM encryption using pre-derived AES key
    """

    # GCM nonce
    nonce = os.urandom(12)

    # ✅ AAD authenticates key-id only
    aad = f"key-id:{key_id}".encode()

    if associated_data:
        aad += b"|" + associated_data

    aesgcm = AESGCM(aes_key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, aad)

    return {
        "ciphertext": base64.b64encode(nonce + ciphertext_with_tag).decode(),
        "metadata": {
            "nonce_size": 12,
            "tag_size": 16
        }
    }


def decrypt(
    ciphertext: str,
    aes_key: bytes,
    associated_data: bytes = None,
    *,
    key_id: str,
    message_id: str
) -> bytes:
    """
    AES-256-GCM decryption with header verification
    """

    raw = base64.b64decode(ciphertext)
    nonce, ciphertext_with_tag = raw[:12], raw[12:]

    aad = f"key-id:{key_id}".encode()

    if associated_data:
        aad += b"|" + associated_data

    aesgcm = AESGCM(aes_key)
    return aesgcm.decrypt(nonce, ciphertext_with_tag, aad)
