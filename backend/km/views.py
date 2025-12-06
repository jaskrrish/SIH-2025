"""
Key Management (KM) API endpoints for QKD key management.

Provides authenticated access to QKD key generation and retrieval.
Uses X-SAE-Token header for authentication (demo only - use proper auth in production).

Endpoints:
- GET /api/km/status/ - Check KM service status
- POST /api/km/get_key/ - Generate new QKD key
- POST /api/km/get_key_with_id/ - Retrieve existing key by ID
"""

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from . import client as km_client


def _authenticate_sae(request) -> str:
    """
    Authenticate SAE from X-SAE-Token header
    
    In production, this should validate JWT or proper authentication.
    For demo, we just extract the SAE identity from header.
    
    Returns:
        str: SAE identity
    
    Raises:
        ValueError: If authentication fails
    """
    # Check for dev mode bypass
    if hasattr(settings, 'KM_DEV_MODE') and settings.KM_DEV_MODE:
        dev_allow = request.headers.get('X-DEV-ALLOW')
        if dev_allow:
            return dev_allow
    
    # Get SAE token
    sae_token = request.headers.get('X-SAE-Token')
    if not sae_token:
        raise ValueError("Missing X-SAE-Token header")
    
    # For demo, token format: "sae:<identity>"
    # In production, validate JWT and extract identity
    if sae_token.startswith('sae:'):
        return sae_token[4:]
    
    return sae_token


@require_http_methods(["GET"])
def status(request):
    """
    Get KM service status.
    
    GET /api/km/status/
    
    Response:
    {
        "status": "OK",
        "service": "QuteMail-KM",
        "version": "1.0.0",
        "stats": {...}
    }
    """
    stats = km_client.get_key_stats()
    return JsonResponse({
        "status": "OK",
        "service": "QuteMail-KM",
        "version": "1.0.0",
        "qkd_algorithm": "BB84",
        "stats": stats,
        "note": "Development mode with in-memory key store"
    })


@csrf_exempt
@require_http_methods(["POST"])
def get_key(request):
    """
    Generate new QKD key using BB84 simulator
    
    POST /api/km/get_key/
    Headers:
        X-SAE-Token: <sae_identity>
    Request body (JSON):
    {
        "requester_sae": "alice@domain.com",
        "recipient_sae": "bob@domain.com",
        "key_size": 256,  // bits (default: 256)
        "ttl": 3600  // seconds (default: 3600)
    }
    
    Response:
    {
        "status": "success",
        "key_id": "uuid-string",
        "key_material": "base64-encoded-key",
        "algorithm": "BB84",
        "expiry": 1701791400
    }
    """
    try:
        # Authenticate requester
        try:
            sae_identity = _authenticate_sae(request)
        except ValueError as e:
            return JsonResponse({"status": "error", "error": str(e)}, status=401)
        
        # Parse request
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "error": "Invalid JSON"}, status=400)
        
        requester_sae = data.get('requester_sae')
        recipient_sae = data.get('recipient_sae')
        key_size = data.get('key_size', 256)
        ttl = data.get('ttl', 3600)
        
        if not requester_sae or not recipient_sae:
            return JsonResponse({
                "status": "error",
                "error": "requester_sae and recipient_sae required"
            }, status=400)
        
        # Generate key
        result = km_client.generate_key(
            requester_sae=requester_sae,
            recipient_sae=recipient_sae,
            key_size=key_size,
            ttl_seconds=ttl
        )
        
        return JsonResponse({
            "status": "success",
            **result
        })
    
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def get_key_with_id(request):
    """
    Retrieve existing key by ID with authentication
    
    POST /api/km/get_key_with_id/
    Headers:
        X-SAE-Token: <sae_identity>
    Request body (JSON):
    {
        "key_id": "uuid-string",
        "requester_sae": "bob@domain.com",
        "mark_consumed": true  // optional, default false
    }
    
    Response:
    {
        "status": "success",
        "key_id": "uuid-string",
        "key_material": "base64-encoded-key",
        "algorithm": "BB84"
    }
    """
    try:
        # Authenticate requester
        try:
            sae_identity = _authenticate_sae(request)
        except ValueError as e:
            return JsonResponse({"status": "error", "error": str(e)}, status=401)
        
        # Parse request
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "error": "Invalid JSON"}, status=400)
        
        key_id = data.get('key_id')
        requester_sae = data.get('requester_sae')
        mark_consumed = data.get('mark_consumed', False)
        
        if not key_id or not requester_sae:
            return JsonResponse({
                "status": "error",
                "error": "key_id and requester_sae required"
            }, status=400)
        
        # Retrieve key with authorization check
        try:
            result = km_client.get_key_by_id(
                key_id=key_id,
                requester_sae=requester_sae,
                mark_consumed=mark_consumed
            )
            
            return JsonResponse({
                "status": "success",
                **result
            })
        except ValueError as e:
            return JsonResponse({
                "status": "error",
                "error": str(e)
            }, status=403 if "Unauthorized" in str(e) else 404)
    
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500)
