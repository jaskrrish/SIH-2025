"""
Regular security level - no encryption (passthrough)
"""


def encrypt(plaintext: bytes, **kwargs) -> dict:
    """
    No encryption - passthrough
    
    Returns:
        dict: {
            'ciphertext': plaintext (unchanged),
            'metadata': {}
        }
    """
    return {
        'ciphertext': plaintext,
        'metadata': {}
    }


def decrypt(ciphertext: bytes, **kwargs) -> bytes:
    """
    No decryption - passthrough
    
    Returns:
        bytes: plaintext (unchanged)
    """
    return ciphertext
