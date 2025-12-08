# bb84_otp_demo.py
import sys
from pathlib import Path

# Ensure the backend package is importable when running this script directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from km.simulator import BB84Simulator

# ---------- helpers ----------
def str_to_bits(s, one_bit_per_char=False):
    if one_bit_per_char:
        # map each char to a single bit using parity of ord (example)
        return [(ord(c) & 1) for c in s]
    # else ASCII 8-bit per char
    bits = []
    for c in s:
        b = format(ord(c), '08b')
        bits.extend(int(x) for x in b)
    return bits

def bits_to_str(bits, one_bit_per_char=False):
    if one_bit_per_char:
        return ''.join(chr(b) for b in bits)  # not practical; adjust mapping if used
    chars = []
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) < 8:
            break
        chars.append(chr(int(''.join(str(b) for b in byte), 2)))
    return ''.join(chars)

def xor_bits(a, b):
    return [x ^ y for x, y in zip(a, b)]

def bytes_to_bits(data, limit=None):
    """Convert bytes to a list of bits; optionally truncate to limit bits."""
    bits = []
    for byte in data:
        for i in range(8):
            bits.append((byte >> (7 - i)) & 1)
            if limit is not None and len(bits) >= limit:
                return bits[:limit]
    return bits if limit is None else bits[:limit]


# ---------- BB84 simulation (via shared backend simulator) ----------
def bb84_generate_key(target_key_length, noise_rate=0.0):
    """
    Generate a shared key using the backend BB84 simulator.

    Returns a dict with alice_key, bob_key (bit lists) and key_id.
    """
    simulator = BB84Simulator(error_rate=noise_rate)
    alice_key_obj, bob_key_obj = simulator.generate_key_pair(key_size=target_key_length)

    alice_bits = bytes_to_bits(alice_key_obj.key_material, limit=target_key_length)
    bob_bits = bytes_to_bits(bob_key_obj.key_material, limit=target_key_length)

    return {
        "alice_key": alice_bits,
        "bob_key": bob_bits,
        "key_id": alice_key_obj.key_id,
    }

# ---------- OTP encryption ----------
def otp_encrypt(plaintext, key_bits, one_bit_per_char=False):
    msg_bits = str_to_bits(plaintext, one_bit_per_char=one_bit_per_char)
    if len(key_bits) < len(msg_bits):
        raise ValueError("Key shorter than message bits")
    cipher_bits = xor_bits(msg_bits, key_bits[:len(msg_bits)])
    return cipher_bits

def otp_decrypt(cipher_bits, key_bits, one_bit_per_char=False):
    plain_bits = xor_bits(cipher_bits, key_bits[:len(cipher_bits)])
    return bits_to_str(plain_bits, one_bit_per_char=one_bit_per_char)

# ---------- demo ----------
if __name__ == "__main__":
    message = "Hello"  # example
    # choose encoding: set one_bit_per_char=True if you truly want 5 bits for 5 chars (custom mapping).
    one_bit_per_char = False   # use ASCII by default (5 chars -> 40 bits)
    msg_bits = str_to_bits(message, one_bit_per_char=one_bit_per_char)
    L = len(msg_bits)
    print(f"Message '{message}' -> {L} bits")

    # 1) Generate QKD key of length L
    result = bb84_generate_key(L, noise_rate=0.0)
    print("BB84 simulator key_id:", result["key_id"])
    alice_key = result["alice_key"]
    bob_key   = result["bob_key"]
    print("Alice key:", alice_key)
    print("Bob key:", bob_key)

    # 2) Alice encrypts
    cipher = otp_encrypt(message, alice_key, one_bit_per_char=one_bit_per_char)
    print("Cipher bits:", cipher)

    # 3) Bob decrypts
    recovered = otp_decrypt(cipher, bob_key, one_bit_per_char=one_bit_per_char)
    print("Recovered message:", recovered)
