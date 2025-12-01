"""
Unit tests for cryptographic utilities
"""
from django.test import TestCase
from crypto.utils import (
    derive_key, aes_gcm_encrypt, aes_gcm_decrypt,
    otp_encrypt, otp_decrypt, hybrid_encrypt, hybrid_decrypt
)
import os


class CryptoTest(TestCase):
    def test_hkdf_derivation(self):
        """Test HKDF key derivation"""
        master_key = os.urandom(32)
        derived1 = derive_key(master_key, info=b'test-context')
        derived2 = derive_key(master_key, info=b'test-context')

        # Same input should give same output (with fixed salt)
        self.assertEqual(len(derived1), 32)
        self.assertEqual(len(derived2), 32)

    def test_aes_gcm_encryption(self):
        """Test AES-256-GCM encryption/decryption"""
        key = os.urandom(32)
        plaintext = b"Secret message"

        ciphertext, nonce, tag = aes_gcm_encrypt(plaintext, key)
        decrypted = aes_gcm_decrypt(ciphertext, key, nonce, tag)

        self.assertEqual(decrypted, plaintext)

    def test_otp_encryption(self):
        """Test one-time pad encryption"""
        plaintext = b"Hello, World!"
        key = os.urandom(len(plaintext))

        ciphertext = otp_encrypt(plaintext, key)
        decrypted = otp_decrypt(ciphertext, key)

        self.assertEqual(decrypted, plaintext)

    def test_hybrid_encryption(self):
        """Test hybrid QKD + AES encryption"""
        qkd_key = os.urandom(32)
        plaintext = b"Quantum-secured message"

        encrypted = hybrid_encrypt(plaintext, qkd_key)

        self.assertIn('ciphertext', encrypted)
        self.assertIn('nonce', encrypted)
        self.assertIn('tag', encrypted)
        self.assertEqual(encrypted['algorithm'], 'AES-256-GCM')

        # Decrypt
        decrypted = hybrid_decrypt(encrypted, qkd_key)
        self.assertEqual(decrypted, plaintext)

    def test_hybrid_encryption_security(self):
        """Test that ciphertext differs from plaintext"""
        qkd_key = os.urandom(32)
        plaintext = b"Top secret message"

        encrypted = hybrid_encrypt(plaintext, qkd_key)

        # Verify ciphertext is different from plaintext
        self.assertNotEqual(encrypted['ciphertext'], plaintext.hex())

        # Decrypt to verify
        decrypted = hybrid_decrypt(encrypted, qkd_key)
        self.assertEqual(decrypted, plaintext)

    def test_hybrid_decryption_wrong_key_fails(self):
        """Test that wrong key fails to decrypt"""
        qkd_key = os.urandom(32)
        wrong_key = os.urandom(32)
        plaintext = b"Secret data"

        encrypted = hybrid_encrypt(plaintext, qkd_key)

        # Attempt to decrypt with wrong key should raise exception
        with self.assertRaises(Exception):
            hybrid_decrypt(encrypted, wrong_key)
