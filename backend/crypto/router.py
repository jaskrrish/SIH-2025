"""
Crypto router - dispatches to appropriate security level
"""
from typing import Optional
from . import level_regular, level_aes, level_qkd, level_qrng_pqc


SECURITY_LEVELS = {
    'regular': level_regular,
    'aes': level_aes,
    'qkd': level_qkd,
    'qrng_pqc': level_qrng_pqc
}


def encrypt(security_level: str, plaintext: bytes, **kwargs) -> dict:
    """
    Encrypt data using specified security level
    
    Args:
        security_level: One of ['regular', 'aes', 'qkd', 'qrng_pqc']
        plaintext: Data to encrypt
        **kwargs: Additional parameters for specific levels
    
    Returns:
        dict: {
            'ciphertext': encrypted data (format varies by level),
            'metadata': {
                'security_level': str,
                'algorithm': str,
                ... level-specific metadata
            }
        }
    
    Raises:
        ValueError: If security level unknown
        NotImplementedError: If level not yet implemented
    """
    if security_level not in SECURITY_LEVELS:
        raise ValueError(f"Unknown security level: {security_level}")
    
    module = SECURITY_LEVELS[security_level]
    result = module.encrypt(plaintext, **kwargs)
    
    # Add security level to metadata
    if 'metadata' not in result:
        result['metadata'] = {}
    result['metadata']['security_level'] = security_level
    
    return result


def decrypt(security_level: str, ciphertext, **kwargs) -> bytes:
    """
    Decrypt data using specified security level
    
    Args:
        security_level: One of ['regular', 'aes', 'qkd', 'qrng_pqc']
        ciphertext: Encrypted data
        **kwargs: Additional parameters for specific levels
    
    Returns:
        bytes: Decrypted plaintext
    
    Raises:
        ValueError: If security level unknown or decryption fails
        NotImplementedError: If level not yet implemented
    """
    if security_level not in SECURITY_LEVELS:
        raise ValueError(f"Unknown security level: {security_level}")
    
    module = SECURITY_LEVELS[security_level]
    return module.decrypt(ciphertext, **kwargs)


def get_available_levels() -> list:
    """Get list of available security levels"""
    return list(SECURITY_LEVELS.keys())
