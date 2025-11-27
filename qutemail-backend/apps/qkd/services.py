"""
High-level QKD services for key request and management
"""
from typing import Dict
from django.conf import settings
from .km_client import QKDKeyManagementClient
from .simulator import BB84Simulator


class QKDService:
    """High-level service for QKD operations"""
    
    def __init__(self):
        self.simulator_mode = settings.QKD_SIMULATOR_MODE
        
        if self.simulator_mode:
            self.simulator = BB84Simulator()
            self.client = None
        else:
            self.client = QKDKeyManagementClient()
            self.simulator = None
    
    def request_key(self, key_size: int = 256, sae_id: str = None) -> Dict:
        """
        Request a quantum key
        
        Args:
            key_size: Size of key in bits
            sae_id: SAE identifier (used in production mode)
            
        Returns:
            Dict with key_id and key_material
        """
        if self.simulator_mode:
            # Use simulator
            alice_key, bob_key = self.simulator.generate_key_pair(key_size)
            return {
                'key_id': alice_key.key_id,
                'key_material': alice_key.key_material.hex(),
                'key_size': alice_key.key_size,
                'source': 'simulator'
            }
        else:
            # Use real KM
            response = self.client.get_key(key_size, sae_id)
            return {
                'key_id': response['keys'][0]['key_ID'],
                'key_material': response['keys'][0]['key'],
                'key_size': key_size,
                'source': 'qkd_km'
            }
    
    def get_key_by_id(self, key_id: str, sae_id: str = None) -> Dict:
        """
        Retrieve a key by its ID
        
        Args:
            key_id: Key identifier
            sae_id: SAE identifier (used in production mode)
            
        Returns:
            Dict with key material
        """
        if self.simulator_mode:
            key_bytes = self.simulator.get_key(key_id)
            return {
                'key_id': key_id,
                'key_material': key_bytes.hex(),
                'source': 'simulator'
            }
        else:
            response = self.client.get_key_with_id(key_id, sae_id)
            return {
                'key_id': key_id,
                'key_material': response['keys'][0]['key'],
                'source': 'qkd_km'
            }
    
    def confirm_key(self, key_id: str) -> bool:
        """
        Confirm key has been used/consumed
        
        Args:
            key_id: Key identifier
            
        Returns:
            True if successful
        """
        # In simulator mode, we could remove the key from store
        if self.simulator_mode:
            if key_id in self.simulator.key_store:
                del self.simulator.key_store[key_id]
            return True
        else:
            # In production, this would call KM confirmation endpoint
            # For now, just return True
            return True
    
    def get_status(self, sae_id: str = None) -> Dict:
        """
        Get QKD system status
        
        Args:
            sae_id: SAE identifier
            
        Returns:
            Dict with status information
        """
        if self.simulator_mode:
            return {
                'status': 'active',
                'mode': 'simulator',
                'keys_available': len(self.simulator.key_store)
            }
        else:
            return self.client.get_status(sae_id)
