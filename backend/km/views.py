"""
Key Management (KM) simulator for development and testing.

This is a minimal in-memory implementation for development purposes only.
In production, this should be replaced with a real KM service that interfaces
with actual QKD hardware or the ETSI QKD 014 API.

Endpoints:
- GET /api/km/status/ - Check KM service status
- POST /api/km/get_key/ - Generate and retrieve a new key
- POST /api/km/get_key_with_id/ - Retrieve an existing key by ID
"""

import json
import secrets
import base64
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import uuid


# In-memory key storage (for development only)
# Format: {keyId: {"key": base64_key, "created": datetime, "expires": datetime}}
KEY_STORE = {}


@require_http_methods(["GET"])
def status(request):
    """
    Get KM service status.
    
    GET /api/km/status/
    
    Response:
    {
        "status": "OK",
        "service": "qute-km-sim",
        "version": "1.0.0-dev",
        "keys_in_store": 5
    }
    """
    return JsonResponse({
        "status": "OK",
        "service": "qute-km-sim",
        "version": "1.0.0-dev",
        "keys_in_store": len(KEY_STORE),
        "note": "This is a development simulator. Replace with real KM service in production."
    })


@csrf_exempt
@require_http_methods(["POST"])
def get_key(request):
    """
    Generate and retrieve a new 256-bit encryption key.
    
    POST /api/km/get_key/
    Request body (JSON, optional):
    {
        "size": 32,  // key size in bytes (default: 32 for 256-bit)
        "purpose": "email-encryption",  // optional metadata
        "ttl": 3600  // time-to-live in seconds (default: 1 hour)
    }
    
    Response:
    {
        "status": "success",
        "keyId": "uuid-string",
        "key": "base64-encoded-key",
        "size": 32,
        "created": "2025-12-04T10:30:00Z",
        "expires": "2025-12-04T11:30:00Z"
    }
    
    Note: In a real implementation, this would:
    1. Request a key from QKD hardware via ETSI QKD 014 API
    2. Use proper key derivation functions (KDF)
    3. Implement key rotation and lifecycle management
    4. Provide key usage tracking and audit logs
    """
    try:
        # Parse optional parameters
        data = {}
        if request.body:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                pass
        
        key_size = data.get('size', 32)  # 32 bytes = 256 bits
        purpose = data.get('purpose', 'encryption')
        ttl = data.get('ttl', 3600)  # 1 hour default
        
        # Generate random key (simulating QKD output)
        key_bytes = secrets.token_bytes(key_size)
        key_b64 = base64.b64encode(key_bytes).decode('utf-8')
        
        # Generate unique key ID
        key_id = str(uuid.uuid4())
        
        # Calculate expiry
        created = datetime.utcnow()
        expires = created + timedelta(seconds=ttl)
        
        # Store in memory
        KEY_STORE[key_id] = {
            "key": key_b64,
            "size": key_size,
            "purpose": purpose,
            "created": created.isoformat() + 'Z',
            "expires": expires.isoformat() + 'Z'
        }
        
        return JsonResponse({
            "status": "success",
            "keyId": key_id,
            "key": key_b64,
            "size": key_size,
            "created": KEY_STORE[key_id]["created"],
            "expires": KEY_STORE[key_id]["expires"],
            "note": "Simulated key - not from real QKD hardware"
        })
        
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def get_key_with_id(request):
    """
    Retrieve an existing key by its ID.
    
    POST /api/km/get_key_with_id/
    Request body (JSON):
    {
        "keyId": "uuid-string"
    }
    
    Response (success):
    {
        "status": "success",
        "keyId": "uuid-string",
        "key": "base64-encoded-key",
        "size": 32,
        "created": "2025-12-04T10:30:00Z",
        "expires": "2025-12-04T11:30:00Z"
    }
    
    Response (not found):
    {
        "status": "error",
        "message": "Key not found or expired"
    }
    """
    try:
        data = json.loads(request.body)
        key_id = data.get('keyId')
        
        if not key_id:
            return JsonResponse({
                "status": "error",
                "message": "Missing 'keyId' field"
            }, status=400)
        
        # Look up key in store
        if key_id not in KEY_STORE:
            return JsonResponse({
                "status": "error",
                "message": "Key not found"
            }, status=404)
        
        key_data = KEY_STORE[key_id]
        
        # Check if key has expired
        expires = datetime.fromisoformat(key_data["expires"].rstrip('Z'))
        if datetime.utcnow() > expires:
            # Clean up expired key
            del KEY_STORE[key_id]
            return JsonResponse({
                "status": "error",
                "message": "Key has expired"
            }, status=410)
        
        return JsonResponse({
            "status": "success",
            "keyId": key_id,
            "key": key_data["key"],
            "size": key_data["size"],
            "created": key_data["created"],
            "expires": key_data["expires"]
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            "status": "error",
            "message": "Invalid JSON in request body"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)
