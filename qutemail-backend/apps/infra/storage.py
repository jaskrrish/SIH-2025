"""
Storage adapters for file and object storage
"""
import os
from pathlib import Path
from django.conf import settings


class LocalStorageAdapter:
    """Local filesystem storage adapter"""
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or os.path.join(settings.BASE_DIR, 'storage')
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
    
    def save(self, key: str, data: bytes) -> bool:
        """
        Save data to local storage
        
        Args:
            key: Storage key/path
            data: Data to save
            
        Returns:
            True if successful
        """
        try:
            file_path = os.path.join(self.base_path, key)
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(data)
            
            return True
        except Exception as e:
            print(f"Failed to save to storage: {str(e)}")
            return False
    
    def load(self, key: str) -> bytes:
        """
        Load data from local storage
        
        Args:
            key: Storage key/path
            
        Returns:
            Data as bytes
        """
        file_path = os.path.join(self.base_path, key)
        
        with open(file_path, 'rb') as f:
            return f.read()
    
    def exists(self, key: str) -> bool:
        """Check if key exists in storage"""
        file_path = os.path.join(self.base_path, key)
        return os.path.exists(file_path)
    
    def delete(self, key: str) -> bool:
        """Delete data from storage"""
        try:
            file_path = os.path.join(self.base_path, key)
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception as e:
            print(f"Failed to delete from storage: {str(e)}")
            return False
