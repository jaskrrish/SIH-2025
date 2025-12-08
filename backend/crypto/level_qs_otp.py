"""
QKD-backed One-Time Pad (OTP) encryption level
Uses KM-provided QKD key bits to XOR plaintext bits.
"""
import base64
from typing import List
from .km_client import km_client


def str_to_bits(s: str, one_bit_per_char: bool = False) -> List[int]:
    if one_bit_per_char:
        return [(ord(c) & 1) for c in s]
    bits = []
    for c in s:
        b = format(ord(c), "08b")
        bits.extend(int(x) for x in b)
    return bits


def bits_to_str(bits: List[int], one_bit_per_char: bool = False) -> str:
    if one_bit_per_char:
        return "".join(chr(b) for b in bits)
    chars = []
    for i in range(0, len(bits), 8):
        byte = bits[i : i + 8]
        if len(byte) < 8:
            break
        chars.append(chr(int("".join(str(b) for b in byte), 2)))
    return "".join(chars)


def xor_bits(a: List[int], b: List[int]) -> List[int]:
    return [x ^ y for x, y in zip(a, b)]


def bytes_to_bits(data: bytes, limit: int | None = None) -> List[int]:
    bits = []
    for byte in data:
        for i in range(8):
            bits.append((byte >> (7 - i)) & 1)
            if limit is not None and len(bits) >= limit:
                return bits[:limit]
    return bits if limit is None else bits[:limit]


def encrypt(
    plaintext: bytes,
    requester_sae: str,
    recipient_sae: str,
    one_bit_per_char: bool = False,
    ttl: int = 3600,
    **kwargs,
) -> dict:
    """
    Encrypt using QKD-derived OTP (bitwise XOR).

    Args:
        plaintext: Data to encrypt (utf-8 decoded).
        requester_sae: Sender SAE identity.
        recipient_sae: Recipient SAE identity.
        one_bit_per_char: Use 1 bit per char (parity) instead of 8-bit ASCII.
        ttl: Key TTL seconds for KM.
    """
    message_str = plaintext.decode("utf-8")
    msg_bits = str_to_bits(message_str, one_bit_per_char=one_bit_per_char)
    bit_len = len(msg_bits)
    if bit_len == 0:
        return {
            "ciphertext": [],
            "metadata": {
                "algorithm": "QKD+OTP",
                "key_size": 0,
                "qkd_algorithm": None,
                "key_id": None,
                "encoding": "utf-8",
                "one_bit_per_char": one_bit_per_char,
            },
        }

    key_response = km_client.request_key(
        requester_sae=requester_sae,
        recipient_sae=recipient_sae,
        key_size=bit_len,
        ttl=ttl,
    )

    key_material = base64.b64decode(key_response["key_material"])
    key_bits = bytes_to_bits(key_material, limit=bit_len)
    if len(key_bits) < bit_len:
        raise ValueError("Key shorter than message bits")

    cipher_bits = xor_bits(msg_bits, key_bits[:bit_len])

    return {
        "ciphertext": cipher_bits,
        "metadata": {
            "algorithm": "QKD+OTP",
            "key_id": key_response["key_id"],
            "key_size": bit_len,
            "qkd_algorithm": key_response["algorithm"],
            "expires_at": key_response.get("expires_at"),
            "encoding": "utf-8",
            "one_bit_per_char": one_bit_per_char,
        },
    }


def decrypt(
    ciphertext,
    key_id: str,
    requester_sae: str,
    one_bit_per_char: bool = False,
    mark_consumed: bool = True,
    **kwargs,
) -> bytes:
    """
    Decrypt QKD-backed OTP ciphertext (bit list).

    Args:
        ciphertext: List of bits (ints 0/1) representing XORed plaintext.
        key_id: Key identifier from encryption metadata.
        requester_sae: SAE identity retrieving the key.
        one_bit_per_char: Encoding flag used during encryption.
        mark_consumed: Whether to consume the key on success.
    """
    if isinstance(ciphertext, str):
        cipher_bits = [int(b) for b in ciphertext if b in ("0", "1")]
    else:
        cipher_bits = [int(b) for b in ciphertext]

    key_response = km_client.get_key_by_id(
        key_id=key_id,
        requester_sae=requester_sae,
    )

    key_material = base64.b64decode(key_response["key_material"])
    key_bits = bytes_to_bits(key_material, limit=len(cipher_bits))
    if len(key_bits) < len(cipher_bits):
        raise ValueError("Key shorter than ciphertext bits")

    plain_bits = xor_bits(cipher_bits, key_bits[: len(cipher_bits)])
    message = bits_to_str(plain_bits, one_bit_per_char=one_bit_per_char)
    plaintext = message.encode("utf-8")

    if mark_consumed:
        km_client.consume_key(key_id=key_id, requester_sae=requester_sae)

    return plaintext
