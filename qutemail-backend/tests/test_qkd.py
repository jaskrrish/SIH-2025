"""
Tests for QKD simulator and services
"""
from django.test import TestCase
from apps.qkd.simulator import BB84Simulator
from apps.qkd.services import QKDService
from apps.crypto.utils import hybrid_encrypt, hybrid_decrypt


class BB84SimulatorTest(TestCase):
    """Test BB84 quantum key distribution simulator"""
    
    def test_key_generation(self):
        """Test basic key generation"""
        simulator = BB84Simulator()
        alice_key, bob_key = simulator.generate_key_pair(key_size=256)
        
        self.assertEqual(alice_key.key_id, bob_key.key_id)
        self.assertEqual(alice_key.key_material, bob_key.key_material)
        self.assertEqual(len(alice_key.key_material) * 8, 256)
    
    def test_key_storage(self):
        """Test key storage and retrieval"""
        simulator = BB84Simulator()
        alice_key, _ = simulator.generate_key_pair(key_size=256)
        
        retrieved_key = simulator.get_key(alice_key.key_id)
        self.assertEqual(retrieved_key, alice_key.key_material)


class QKDServiceTest(TestCase):
    """Test QKD service"""
    
    def test_request_key_simulator_mode(self):
        """Test key request in simulator mode"""
        service = QKDService()
        key_data = service.request_key(key_size=256)
        
        self.assertIn('key_id', key_data)
        self.assertIn('key_material', key_data)
        self.assertEqual(key_data['source'], 'simulator')


class CryptoUtilsTest(TestCase):
    """Test cryptographic utilities"""
    
    def test_hybrid_encryption(self):
        """Test hybrid encryption and decryption"""
        qkd_key = b'0' * 32  # 32-byte key
        plaintext = b"Hello, Quantum World!"
        
        encrypted_data = hybrid_encrypt(plaintext, qkd_key)
        decrypted = hybrid_decrypt(encrypted_data, qkd_key)
        
        self.assertEqual(plaintext, decrypted)
