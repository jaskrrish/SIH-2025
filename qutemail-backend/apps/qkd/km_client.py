"""
ETSI GS QKD 014 Key Management Interface Client
Implements the standard interface for QKD key management
"""
import requests
from typing import Dict, Optional
from django.conf import settings


class QKDKeyManagementClient:
    """Client for interacting with QKD Key Management (KM) service"""
    
    def __init__(self, km_url: str = None):
        self.km_url = km_url or settings.QKD_KM_URL
        self.session = requests.Session()
    
    def get_key(self, key_size: int = 256, sae_id: str = None) -> Dict:
        """
        Request a key from the QKD KM
        
        Args:
            key_size: Size of key in bits (default 256)
            sae_id: SAE (Secure Application Entity) identifier
            
        Returns:
            Dict containing key_id and key material
        """
        endpoint = f"{self.km_url}/api/v1/keys/{sae_id}/enc_keys"
        
        payload = {
            "number": 1,
            "size": key_size
        }
        
        try:
            response = self.session.post(endpoint, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Failed to get key from KM: {str(e)}")
    
    def get_key_with_id(self, key_id: str, sae_id: str = None) -> Dict:
        """
        Retrieve a specific key by ID
        
        Args:
            key_id: Unique key identifier
            sae_id: SAE identifier
            
        Returns:
            Dict containing key material
        """
        endpoint = f"{self.km_url}/api/v1/keys/{sae_id}/dec_keys"
        
        payload = {"key_IDs": [{"key_ID": key_id}]}
        
        try:
            response = self.session.post(endpoint, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Failed to retrieve key {key_id}: {str(e)}")
    
    def get_status(self, sae_id: str = None) -> Dict:
        """
        Get status of the QKD connection
        
        Args:
            sae_id: SAE identifier
            
        Returns:
            Dict containing status information
        """
        endpoint = f"{self.km_url}/api/v1/keys/{sae_id}/status"
        
        try:
            response = self.session.get(endpoint, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Failed to get KM status: {str(e)}")
