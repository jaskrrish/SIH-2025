"""
Key Manager client for QKD key management
Wraps BB84 simulator and provides key lifecycle management
"""
import uuid
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict
from .simulator import BB84Simulator


# In-memory key store for demo (replace with DB in production)
_key_store: Dict[str, dict] = {}


def generate_key(requester_sae: str, recipient_sae: str, key_size: int = 256, 
                 ttl_seconds: int = 3600) -> dict:
    """
    Generate new QKD key using BB84 simulator
    
    Args:
        requester_sae: Sender SAE identity
        recipient_sae: Recipient SAE identity  
        key_size: Key size in bits (default 256)
        ttl_seconds: Time-to-live in seconds
    
    Returns:
        dict: {
            'key_id': '<uuid>',
            'key_material': '<base64>',
            'expiry': <unix_timestamp>,
            'algorithm': 'BB84'
        }
    """
    # Generate key using BB84 simulator
    simulator = BB84Simulator()
    alice_key, bob_key = simulator.generate_key_pair(key_size=key_size)
    
    # In real QKD, alice_key stays with sender, bob_key with receiver
    # For demo, we store bob_key (receiver's key) in KM
    # Extract actual key material bytes from QKDKey objects
    alice_key_bytes = alice_key.key_material
    bob_key_bytes = bob_key.key_material
    
    # Generate unique key ID
    key_id = str(uuid.uuid4())
    
    # Calculate expiry
    expiry_ts = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    
    # Store key metadata
    _key_store[key_id] = {
        'key_id': key_id,
        'key_material_b64': base64.b64encode(bob_key_bytes).decode('utf-8'),
        'key_material': bob_key_bytes,
        'requester_sae': requester_sae,
        'recipient_sae': recipient_sae,
        'created_at': datetime.utcnow(),
        'expiry': expiry_ts,
        'consumed': False,
        'algorithm': 'BB84'
    }
    
    print(f"[KM] Generated key {key_id} for {requester_sae} -> {recipient_sae}")
    
    return {
        'key_id': key_id,
        'key_material': base64.b64encode(alice_key_bytes).decode('utf-8'),  # Return sender's key
        'expiry': int(expiry_ts.timestamp()),
        'algorithm': 'BB84'
    }


def get_key_by_id(key_id: str, requester_sae: str, mark_consumed: bool = False) -> Optional[dict]:
    """
    Retrieve key by ID with authentication and expiry checks
    
    Args:
        key_id: Key identifier
        requester_sae: SAE identity requesting the key
        mark_consumed: Mark key as consumed (OTP semantics)
    
    Returns:
        dict or None: {
            'key_id': '<uuid>',
            'key_material': '<base64>',
            'algorithm': 'BB84'
        }
    
    Raises:
        ValueError: If key not found, expired, consumed, or unauthorized
    """
    if key_id not in _key_store:
        raise ValueError(f"Key {key_id} not found")
    
    key_entry = _key_store[key_id]
    
    # Check expiry
    if datetime.utcnow() > key_entry['expiry']:
        raise ValueError(f"Key {key_id} has expired")
    
    # Check if already consumed
    if key_entry['consumed']:
        raise ValueError(f"Key {key_id} has already been consumed")
    
    # Check authorization - requester must be recipient
    if requester_sae != key_entry['recipient_sae']:
        print(f"[KM] Unauthorized access attempt: {requester_sae} != {key_entry['recipient_sae']}")
        raise ValueError(f"Unauthorized: Key {key_id} not intended for {requester_sae}")
    
    print(f"[KM] Key {key_id} retrieved by {requester_sae}")
    
    # Mark as consumed if requested
    if mark_consumed:
        key_entry['consumed'] = True
        print(f"[KM] Key {key_id} marked as consumed")
    
    return {
        'key_id': key_id,
        'key_material': key_entry['key_material_b64'],
        'algorithm': key_entry['algorithm']
    }


def cleanup_expired_keys():
    """Remove expired keys from store"""
    now = datetime.utcnow()
    expired = [kid for kid, entry in _key_store.items() if now > entry['expiry']]
    for kid in expired:
        del _key_store[kid]
    if expired:
        print(f"[KM] Cleaned up {len(expired)} expired keys")


def get_key_stats() -> dict:
    """Get statistics about key store (for debugging)"""
    now = datetime.utcnow()
    active = sum(1 for e in _key_store.values() if not e['consumed'] and now <= e['expiry'])
    expired = sum(1 for e in _key_store.values() if now > e['expiry'])
    consumed = sum(1 for e in _key_store.values() if e['consumed'])
    
    return {
        'total': len(_key_store),
        'active': active,
        'expired': expired,
        'consumed': consumed
    }
