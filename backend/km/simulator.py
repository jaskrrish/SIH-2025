"""
BB84 QKD Protocol Simulator for Development
Simulates quantum key distribution for testing purposes
"""
import secrets
import hashlib
from typing import Tuple, List
from dataclasses import dataclass


@dataclass
class QKDKey:
    """Represents a QKD-generated key"""
    key_id: str
    key_material: bytes
    key_size: int


class BB84Simulator:
    """Simple BB84 protocol simulator for development/testing"""
    
    def __init__(self, error_rate: float = 0.0):
        """
        Initialize BB84 simulator
        
        Args:
            error_rate: Simulated quantum channel error rate (0.0 - 1.0)
        """
        self.error_rate = error_rate
        self.key_store = {}
    
    def generate_key_pair(self, key_size: int = 256) -> Tuple[QKDKey, QKDKey]:
        """
        Simulate BB84 key generation for two parties (Alice and Bob)
        
        Args:
            key_size: Desired key size in bits
            
        Returns:
            Tuple of (alice_key, bob_key)
        """
        # Generate random bits for Alice
        alice_bits = [secrets.randbelow(2) for _ in range(key_size * 2)]
        alice_bases = [secrets.randbelow(2) for _ in range(key_size * 2)]
        
        # Bob randomly chooses measurement bases
        bob_bases = [secrets.randbelow(2) for _ in range(key_size * 2)]
        
        # Measure bits (with possible errors)
        bob_bits = []
        for i, (bit, alice_base, bob_base) in enumerate(zip(alice_bits, alice_bases, bob_bases)):
            if alice_base == bob_base:
                # Matching bases - bit preserved (with error rate)
                if secrets.randbelow(100) < self.error_rate * 100:
                    bob_bits.append(1 - bit)  # Flip bit (error)
                else:
                    bob_bits.append(bit)
            else:
                # Non-matching bases - random result
                bob_bits.append(secrets.randbelow(2))
        
        # Sift keys - keep only bits where bases matched
        sifted_key = []
        for i in range(len(alice_bits)):
            if alice_bases[i] == bob_bases[i]:
                sifted_key.append(alice_bits[i])
                if len(sifted_key) >= key_size:
                    break
        
        # Convert bits to bytes
        key_bytes = self._bits_to_bytes(sifted_key[:key_size])
        
        # Generate unique key ID
        key_id = hashlib.sha256(key_bytes + secrets.token_bytes(16)).hexdigest()[:32]
        
        # Create key objects
        alice_key = QKDKey(
            key_id=key_id,
            key_material=key_bytes,
            key_size=key_size
        )
        
        bob_key = QKDKey(
            key_id=key_id,
            key_material=key_bytes,
            key_size=key_size
        )
        
        # Store in key store
        self.key_store[key_id] = key_bytes
        
        return alice_key, bob_key
    
    def get_key(self, key_id: str) -> bytes:
        """
        Retrieve a key from the key store
        
        Args:
            key_id: Key identifier
            
        Returns:
            Key material as bytes
        """
        if key_id not in self.key_store:
            raise ValueError(f"Key {key_id} not found")
        return self.key_store[key_id]
    
    @staticmethod
    def _bits_to_bytes(bits: List[int]) -> bytes:
        """Convert list of bits to bytes"""
        byte_array = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                if i + j < len(bits):
                    byte |= bits[i + j] << (7 - j)
            byte_array.append(byte)
        return bytes(byte_array)