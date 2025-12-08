# qkd_pqc_hybrid.py
import base64
import os
import hmac
import hashlib
from typing import Optional, Dict, Any

from .km_client import km_client

# Try to import a Kyber (PQC KEM) binding. Adjust if your binding has a different name.
try:
    import kyber_py as pqc_kem  # common name you used before
except Exception:
    pqc_kem = None

# AES-GCM
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except Exception:
    AESGCM = None


# ---- Helpers: HKDF (RFC5869) -------------------------------------------------
def hkdf_extract(salt: bytes, ikm: bytes, hash_alg=hashlib.sha256) -> bytes:
    if salt is None or len(salt) == 0:
        salt = bytes([0] * hash_alg().digest_size)
    return hmac.new(salt, ikm, hash_alg).digest()


def hkdf_expand(prk: bytes, info: bytes, length: int, hash_alg=hashlib.sha256) -> bytes:
    hash_len = hash_alg().digest_size
    n = (length + hash_len - 1) // hash_len
    if n > 255:
        raise ValueError("Cannot expand to more than 255 * HashLen bytes")
    okm = b""
    t = b""
    for i in range(1, n + 1):
        t = hmac.new(prk, t + info + bytes([i]), hash_alg).digest()
        okm += t
    return okm[:length]


def hkdf(salt: bytes, ikm: bytes, info: bytes, length: int, hash_alg=hashlib.sha256) -> bytes:
    prk = hkdf_extract(salt, ikm, hash_alg=hash_alg)
    return hkdf_expand(prk, info, length, hash_alg=hash_alg)


# ---- Utilities ---------------------------------------------------------------
def b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def ub64(s: str) -> bytes:
    return base64.b64decode(s)


# ---- Errors for missing deps -------------------------------------------------
def _require_pqc():
    if pqc_kem is None:
        raise ImportError(
            "No PQC KEM library found (tried importing 'kyber_py'). "
            "Install a Kyber binding (e.g. `kyber_py`) or adapt the code to your library."
        )


def _require_crypto():
    if AESGCM is None:
        raise ImportError(
            "cryptography library is required for AES-GCM. Install with `pip install cryptography`."
        )


# ---- Public API: encrypt / decrypt -------------------------------------------
def encrypt(
    plaintext: bytes,
    requester_sae: str,
    recipient_sae: str,
    recipient_pqc_public_key: bytes | str,
    pqc_name: str = "kyber",
    qkd_ttl: int = 3600,
    aes_key_len: int = 32,  # 256-bit AES key
    hkdf_info: bytes = b"qkd+pqc hybrid key derivation",
) -> Dict[str, Any]:
    """
    Hybrid encrypt: PQC-KEM (encapsulate) + QKD key material mixed via HKDF -> AES-GCM.

    Returns a dict with:
      - ciphertext: base64(AES-GCM ciphertext || tag) (AESGCM returns ciphertext that already contains tag)
      - metadata: {
            algorithm: "QKD+PQC",
            kem: pqc_name,
            encapsulated: base64(encapsulated_bytes),
            key_id: <qkd key id> (base64 string from km_client),
            iv: base64(iv),
            hkdf_info: base64(info)
        }

    Arguments:
      - recipient_pqc_public_key: bytes or base64 string of recipient's PQC public key
      - requester_sae / recipient_sae: identities passed to km_client
      - qkd_ttl: TTL for the QKD key request
      - aes_key_len: length of derived AES key in bytes (16/24/32)
    """
    _require_pqc()
    _require_crypto()

    if isinstance(recipient_pqc_public_key, str):
        # accept base64-encoded or raw string
        try:
            recipient_pk = base64.b64decode(recipient_pqc_public_key)
        except Exception:
            recipient_pk = recipient_pqc_public_key.encode("utf-8")
    else:
        recipient_pk = recipient_pqc_public_key

    # 1) PQC KEM encapsulation using recipient's public key
    # The exact API differs between pqc libs; attempt a few common patterns.
    encapsulated = None
    kem_shared_secret = None
    # Common kyber_py API assumption: pqc_kem.encapsulate(public_key) -> (ciphertext, shared_secret)
    try:
        result = pqc_kem.encapsulate(recipient_pk)
        if isinstance(result, tuple) and len(result) >= 2:
            encapsulated, kem_shared_secret = result[0], result[1]
        else:
            raise AttributeError("Unexpected return from pqc_kem.encapsulate")
    except AttributeError:
        # try alternative names
        try:
            # kyber_py.keypair and then encapsulate_by_pk
            if hasattr(pqc_kem, "encapsulate_by_pk"):
                encapsulated, kem_shared_secret = pqc_kem.encapsulate_by_pk(recipient_pk)
            else:
                raise
        except Exception as e:
            raise RuntimeError(
                "Unable to call PQC KEM encapsulation. Check your pqc_kem API. "
                "Tried `encapsulate(pk)` and `encapsulate_by_pk(pk)`. Error: " + str(e)
            )

    if not (encapsulated and kem_shared_secret):
        raise RuntimeError("PQC KEM encapsulation did not return expected values")

    # 2) Request QKD key material from KM: choose key size appropriate for HKDF mixing
    # We'll request at least `aes_key_len` bytes (but allow more); km_client in your OTP code used bit-length.
    # Here we request bytes length; if your km_client expects bits, adapt accordingly.
    # To stay compatible with your km_client earlier (which used key_size in bits), we request bytes*8.
    requested_key_size_bits = aes_key_len * 8
    key_response = km_client.request_key(
        requester_sae=requester_sae,
        recipient_sae=recipient_sae,
        key_size=requested_key_size_bits,
        ttl=qkd_ttl,
    )
    # Expect key_response to include 'key_material' (base64) and 'key_id'
    if "key_material" not in key_response or "key_id" not in key_response:
        raise RuntimeError("km_client.request_key returned unexpected structure: " + str(key_response))

    qkd_key_material = base64.b64decode(key_response["key_material"])
    qkd_key_id = key_response["key_id"]

    # 3) Derive final AES key via HKDF over (kem_shared_secret || qkd_key_material)
    ikm = kem_shared_secret + qkd_key_material
    # optional salt could be empty or derived; use empty salt so HKDF still works
    final_key = hkdf(salt=b"", ikm=ikm, info=hkdf_info, length=aes_key_len, hash_alg=hashlib.sha256)

    # 4) AES-GCM encrypt
    iv = os.urandom(12)  # 96-bit nonce recommended for AES-GCM
    aesgcm = AESGCM(final_key)
    ciphertext = aesgcm.encrypt(iv, plaintext, associated_data=None)  # returns ciphertext||tag

    return {
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        "metadata": {
            "algorithm": "QKD+PQC",
            "kem": pqc_name,
            "encapsulated": base64.b64encode(encapsulated).decode("ascii"),
            "key_id": qkd_key_id,
            "iv": base64.b64encode(iv).decode("ascii"),
            "hkdf_info": base64.b64encode(hkdf_info).decode("ascii"),
            "aes_key_len": aes_key_len,
        },
    }


def decrypt(
    ciphertext_b64: str,
    metadata: Dict[str, Any],
    requester_sae: str,
    recipient_pqc_private_key: bytes | str,
    mark_consumed: bool = True,
) -> bytes:
    """
    Decrypt hybrid QKD+PQC AES-GCM ciphertext.

    Args:
      - ciphertext_b64: base64-encoded AES-GCM ciphertext (ciphertext||tag)
      - metadata: the metadata dict produced by `encrypt` (must include encapsulated, key_id, iv, hkdf_info, aes_key_len)
      - requester_sae: SAE identity used to fetch QKD key from KM
      - recipient_pqc_private_key: recipient's PQC private key (bytes or base64 string)
      - mark_consumed: whether to call km_client.consume_key on success.

    Returns:
      - plaintext bytes
    """
    _require_pqc()
    _require_crypto()

    # validate metadata
    required = ("encapsulated", "key_id", "iv", "hkdf_info", "aes_key_len")
    for k in required:
        if k not in metadata:
            raise ValueError(f"Missing required metadata field: {k}")

    encapsulated = base64.b64decode(metadata["encapsulated"])
    key_id = metadata["key_id"]
    iv = base64.b64decode(metadata["iv"])
    hkdf_info = base64.b64decode(metadata["hkdf_info"])
    aes_key_len = int(metadata.get("aes_key_len", 32))

    # PQC decapsulation: get kem_shared_secret
    if isinstance(recipient_pqc_private_key, str):
        try:
            recipient_sk = base64.b64decode(recipient_pqc_private_key)
        except Exception:
            recipient_sk = recipient_pqc_private_key.encode("utf-8")
    else:
        recipient_sk = recipient_pqc_private_key

    # Try common APIs: pqc_kem.decapsulate(ct, sk) or pqc_kem.decapsulate_by_sk(ct, sk)
    kem_shared_secret = None
    try:
        # common pattern: decapsulate(ciphertext, private_key) -> shared_secret
        kem_shared_secret = pqc_kem.decapsulate(encapsulated, recipient_sk)
    except Exception:
        try:
            if hasattr(pqc_kem, "decapsulate_by_sk"):
                kem_shared_secret = pqc_kem.decapsulate_by_sk(encapsulated, recipient_sk)
        except Exception as e:
            raise RuntimeError(
                "Unable to decapsulate using the loaded PQC KEM library. "
                "Check the library API. Error: " + str(e)
            )
    if kem_shared_secret is None:
        raise RuntimeError("PQC decapsulation produced no shared secret")

    # Fetch QKD key material
    key_response = km_client.get_key_by_id(key_id=key_id, requester_sae=requester_sae)
    if "key_material" not in key_response:
        raise RuntimeError("km_client.get_key_by_id returned unexpected structure: " + str(key_response))
    qkd_key_material = base64.b64decode(key_response["key_material"])

    # Derive final key
    ikm = kem_shared_secret + qkd_key_material
    final_key = hkdf(salt=b"", ikm=ikm, info=hkdf_info, length=aes_key_len, hash_alg=hashlib.sha256)

    # Decrypt AES-GCM
    aesgcm = AESGCM(final_key)
    ciphertext = base64.b64decode(ciphertext_b64)
    plaintext = aesgcm.decrypt(iv, ciphertext, associated_data=None)

    # Consume QKD key if requested
    if mark_consumed:
        try:
            km_client.consume_key(key_id=key_id, requester_sae=requester_sae)
        except Exception:
            # Do not fail decryption if consume fails; surface a warning via exception chain is possible.
            pass

    return plaintext
