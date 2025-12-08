"""
KM Service REST Client
Replaces old km/client.py with REST API calls
"""
import os
import requests
from django.conf import settings


class KMServiceClient:
    """Client for interacting with KM REST API"""
    
    def __init__(self, base_url=None):
        """Initialize with KM service URL"""
        self.base_url = base_url or getattr(
            settings, 
            'KM_SERVICE_URL', 
            os.getenv('KM_SERVICE_URL', 'http://localhost:5001')
        )
    
    def request_key(self, requester_sae: str, recipient_sae: str, 
                   key_size: int = 256, ttl: int = 3600) -> dict:
        """
        Request a new quantum key from KM (Alice/Sender)
        
        Args:
            requester_sae: Sender SAE identity (email)
            recipient_sae: Recipient SAE identity (email)
            key_size: Key size in bits
            ttl: Time-to-live in seconds
        
        Returns:
            dict: {
                'key_id': '<uuid>-alice',
                'key': '<base64>',
                'size': 256,
                'algorithm': 'BB84',
                'expires_at': '<iso8601>'
            }
        
        Raises:
            Exception: If KM request fails
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/keys/request",
                json={
                    "requester_sae": requester_sae,
                    "recipient_sae": recipient_sae,
                    "key_size": key_size,
                    "ttl": ttl
                },
                timeout=10
            )
            
            if response.status_code != 200:
                error_data = response.json()
                raise Exception(f"KM request failed: {error_data.get('error', 'Unknown error')}")
            
            data = response.json()
            
            if data['status'] != 'success':
                raise Exception(f"KM request failed: {data.get('error', 'Unknown error')}")
            
            print(f"[KM-Client] ✅ Key requested: {data['key_id']}")
            
            return {
                'key_id': data['key_id'],
                'key_material': data['key'],  # base64 encoded
                'size': data['size'],
                'algorithm': data['algorithm'],
                'expires_at': data['expires_at']
            }
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"KM service connection failed: {str(e)}")
    
    def get_key_by_id(self, key_id: str, requester_sae: str) -> dict:
        """
        Retrieve a key by ID from KM (Bob/Receiver)
        
        Args:
            key_id: Key identifier (should be bob's key ID)
            requester_sae: SAE identity requesting the key (email)
        
        Returns:
            dict: {
                'key_id': '<uuid>-bob',
                'key_material': '<base64>',
                'size': 256,
                'algorithm': 'BB84'
            }
        
        Raises:
            Exception: If key not found or unauthorized
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/keys/{key_id}",
                params={"requester_sae": requester_sae},
                timeout=10
            )
            
            if response.status_code == 404:
                raise Exception(f"Key {key_id} not found")
            elif response.status_code == 403:
                raise Exception(f"Unauthorized: Key not intended for {requester_sae}")
            elif response.status_code == 410:
                raise Exception(f"Key {key_id} has expired or been consumed")
            elif response.status_code != 200:
                error_data = response.json()
                raise Exception(f"KM retrieval failed: {error_data.get('error', 'Unknown error')}")
            
            data = response.json()
            
            if data['status'] != 'success':
                raise Exception(f"KM retrieval failed: {data.get('error', 'Unknown error')}")
            
            print(f"[KM-Client] ✅ Key retrieved: {data['key_id']}")
            
            return {
                'key_id': data['key_id'],
                'key_material': data['key'],  # base64 encoded
                'size': data['size'],
                'algorithm': data['algorithm']
            }
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"KM service connection failed: {str(e)}")
    
    def consume_key(self, key_id: str, requester_sae: str) -> bool:
        """
        Mark a key as consumed (one-time use)
        
        Args:
            key_id: Key identifier
            requester_sae: SAE identity
        
        Returns:
            bool: True if successful
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/keys/consume",
                json={
                    "key_id": key_id,
                    "requester_sae": requester_sae
                },
                timeout=10
            )
            
            return response.status_code == 200
        
        except requests.exceptions.RequestException:
            return False
    
    def check_health(self) -> dict:
        """
        Check KM service health
        
        Returns:
            dict: Status information
        """
        try:
            response = requests.get(f"{self.base_url}/api/v1/status", timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "error": "KM service unavailable"}
        
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": str(e)}


# Global instance
km_client = KMServiceClient()
