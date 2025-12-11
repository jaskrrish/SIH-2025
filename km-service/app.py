"""
Key Management Service - ETSI GS QKD 014 Compliant REST API
Manages quantum key distribution for secure email communications
"""
import os
from datetime import datetime
from flask import Flask, request, jsonify
from sqlalchemy import or_, desc
from flask_cors import CORS
from dotenv import load_dotenv

from database import db, init_db
from models import QKDKey
from qkd_orchestrator import QKDOrchestrator

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize database
init_db(app)

# Initialize QKD Orchestrator
orchestrator = QKDOrchestrator()

# Helper function for timezone-aware datetime
def utc_now():
    """Return timezone-aware UTC datetime (Python 3.11+) or fallback"""
    return datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()

# ==================== Authentication ====================

def authenticate_sae(requester_sae: str) -> bool:
    """
    Authenticate SAE based on email
    In production, implement proper JWT/certificate validation
    """
    # For now, simple email validation
    if not requester_sae or '@' not in requester_sae:
        return False
    return True


# ==================== API Endpoints ====================

@app.route('/api/v1/status', methods=['GET'])
def status():
    """
    Health check endpoint
    
    GET /api/v1/status
    
    Returns:
        {
            "status": "OK",
            "service": "QuteMail-KM",
            "version": "2.0.0-ETSI",
            "qkd_orchestrator": {...},
            "database": "connected"
        }
    """
    try:
        # Test database connection
        db.session.execute(db.text('SELECT 1'))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return jsonify({
        "status": "OK",
        "service": "QuteMail-KM",
        "version": "2.0.0-ETSI",
        "description": "Quantum Key Management Service",
        "qkd_orchestrator": orchestrator.get_stats(),
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/v1/keys/request', methods=['POST'])
def request_key():
    """
    Request a quantum key for encryption (SAE-A → SAE-B)
    
    POST /api/v1/keys/request
    
    Request body:
    {
        "requester_sae": "alice@example.com",
        "recipient_sae": "bob@example.com",
        "key_size": 256,  // optional, default from env
        "ttl": 3600       // optional, default from env
    }
    
    Response:
    {
        "status": "success",
        "key_id": "abc123-alice",
        "key": "base64-encoded-key-material",
        "size": 256,
        "algorithm": "BB84",
        "expires_at": "2025-12-08T12:00:00",
        "message": "Key ready for encryption"
    }
    """
    try:
        data = request.get_json()
        
        # Validate request
        requester_sae = data.get('requester_sae')
        recipient_sae = data.get('recipient_sae')
        
        if not requester_sae or not recipient_sae:
            return jsonify({
                "status": "error",
                "error": "requester_sae and recipient_sae are required"
            }), 400
        
        # Authenticate requester
        if not authenticate_sae(requester_sae):
            return jsonify({
                "status": "error",
                "error": "Authentication failed: Invalid SAE identity"
            }), 401
        
        key_size = data.get('key_size', int(os.getenv('QKD_KEY_SIZE', '256')))
        ttl = data.get('ttl', int(os.getenv('QKD_KEY_TTL', '3600')))
        
        print(f"\n[KM] Key request: {requester_sae} → {recipient_sae}")
        
        # Check if unused key exists in pool (KM1 for requester)
        existing_key = QKDKey.find_available_key(requester_sae, recipient_sae, 'KM1')
        
        if existing_key:
            print(f"[KM] ♻️  Reusing existing key from pool: {existing_key.key_id}")
            
            # Mark as served
            existing_key.state = QKDKey.STATE_SERVED
            existing_key.served_at = utc_now()
            db.session.commit()
            
            return jsonify({
                "status": "success",
                "key_id": existing_key.key_id,
                "key": existing_key.to_dict(include_key_material=True)['key'],
                "size": existing_key.key_size,
                "algorithm": existing_key.algorithm,
                "expires_at": existing_key.expires_at.isoformat(),
                "message": "Key retrieved from pool",
                "source": "pool"
            })
        
        # No key in pool - orchestrate new QKD session
        print(f"[KM] 🔑 No key in pool, orchestrating QKD session...")
        
        alice_key_obj, bob_key_obj = orchestrator.orchestrate_key_generation(
            requester_sae=requester_sae,
            recipient_sae=recipient_sae,
            key_size=key_size
        )
        
        # Create key pair in database (simulates KM1 and KM2)
        alice_key, bob_key = QKDKey.create_key_pair(
            requester_sae=requester_sae,
            recipient_sae=recipient_sae,
            alice_key_bytes=alice_key_obj.key_material,
            bob_key_bytes=bob_key_obj.key_material,
            key_size=key_size,
            ttl_seconds=ttl,
            algorithm='BB84'
        )
        
        # Save both keys
        db.session.add(alice_key)
        db.session.add(bob_key)
        
        # Mark alice key as served
        alice_key.state = QKDKey.STATE_SERVED
        alice_key.served_at = utc_now()
        
        db.session.commit()
        
        print(f"[KM] ✅ Key pair created:")
        print(f"[KM]    Alice (KM1): {alice_key.key_id}")
        print(f"[KM]    Bob (KM2): {bob_key.key_id}")
        
        return jsonify({
            "status": "success",
            "key_id": alice_key.key_id,
            "key": alice_key.to_dict(include_key_material=True)['key'],
            "size": alice_key.key_size,
            "algorithm": alice_key.algorithm,
            "expires_at": alice_key.expires_at.isoformat(),
            "message": "New key generated via QKD",
            "source": "qkd_orchestrator"
        })
    
    except Exception as e:
        print(f"[KM] ❌ Error in key request: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/api/v1/keys/<key_id>', methods=['GET'])
def get_key(key_id):
    """
    Retrieve a key by ID (SAE-B retrieves for decryption)
    
    GET /api/v1/keys/{key_id}?requester_sae=bob@example.com
    
    Query params:
        requester_sae: SAE identity requesting the key
    
    Response:
    {
        "status": "success",
        "key_id": "abc123-bob",
        "key": "base64-encoded-key-material",
        "size": 256,
        "algorithm": "BB84"
    }
    """
    try:
        # Get requester SAE from query params
        requester_sae = request.args.get('requester_sae')
        
        if not requester_sae:
            return jsonify({
                "status": "error",
                "error": "requester_sae query parameter is required"
            }), 400
        
        # Authenticate requester
        if not authenticate_sae(requester_sae):
            return jsonify({
                "status": "error",
                "error": "Authentication failed: Invalid SAE identity"
            }), 401
        
        print(f"\n[KM] Key retrieval: {key_id} by {requester_sae}")
        
        # Find key in database
        requested_key = QKDKey.query.filter_by(key_id=key_id).first()
        
        if not requested_key:
            return jsonify({
                "status": "error",
                "error": f"Key {key_id} not found"
            }), 404
        
        # IMPORTANT: If requester is the recipient, automatically find their matching key (KM2)
        # Alice's key (KM1) has pair_key_id pointing to Bob's key (KM2)
        key = requested_key
        if requester_sae == requested_key.recipient_sae and requested_key.km_instance == 'KM1':
            # Bob is requesting Alice's key_id - find his matching key
            bob_key = QKDKey.query.filter_by(key_id=requested_key.pair_key_id).first()
            if bob_key:
                print(f"[KM] 🔄 Auto-mapped {key_id} (KM1) → {bob_key.key_id} (KM2) for recipient")
                key = bob_key
            else:
                return jsonify({
                    "status": "error",
                    "error": f"Matching recipient key not found for {key_id}"
                }), 404
        
        # Check expiry
        if utc_now() > key.expires_at:
            return jsonify({
                "status": "error",
                "error": f"Key {key.key_id} has expired"
            }), 410
        
        # Check if already consumed
        if key.state == QKDKey.STATE_CONSUMED:
            return jsonify({
                "status": "error",
                "error": f"Key {key.key_id} has already been consumed"
            }), 410
        
        # Authorization check - requester must be recipient
        if requester_sae != key.recipient_sae:
            print(f"[KM] ⚠️  Unauthorized: {requester_sae} != {key.recipient_sae}")
            return jsonify({
                "status": "error",
                "error": f"Unauthorized: Key not intended for {requester_sae}"
            }), 403
        
        # Final check - must be KM2 for recipient
        if key.km_instance != 'KM2':
            print(f"[KM] ⚠️  Wrong KM instance: {key.km_instance}, expected KM2")
            return jsonify({
                "status": "error",
                "error": "Key not available in recipient's KM instance"
            }), 404
        
        print(f"[KM] ✅ Key {key_id} retrieved by {requester_sae}")
        
        # Mark as served if not already
        if key.state == QKDKey.STATE_STORED:
            key.state = QKDKey.STATE_SERVED
            key.served_at = utc_now()
            db.session.commit()
        
        return jsonify({
            "status": "success",
            "key_id": key.key_id,
            "key": key.to_dict(include_key_material=True)['key'],
            "size": key.key_size,
            "algorithm": key.algorithm
        })
    
    except Exception as e:
        print(f"[KM] ❌ Error in key retrieval: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/api/v1/keys/consume', methods=['POST'])
def consume_key():
    """
    Mark a key as consumed (one-time use)
    
    POST /api/v1/keys/consume
    
    Request body:
    {
        "key_id": "abc123-bob",
        "requester_sae": "bob@example.com"
    }
    
    Response:
    {
        "status": "success",
        "message": "Key marked as consumed"
    }
    """
    try:
        data = request.get_json()
        
        key_id = data.get('key_id')
        requester_sae = data.get('requester_sae')
        
        if not key_id or not requester_sae:
            return jsonify({
                "status": "error",
                "error": "key_id and requester_sae are required"
            }), 400
        
        # Authenticate requester
        if not authenticate_sae(requester_sae):
            return jsonify({
                "status": "error",
                "error": "Authentication failed"
            }), 401
        
        # Find key
        key = QKDKey.query.filter_by(key_id=key_id).first()
        
        if not key:
            return jsonify({
                "status": "error",
                "error": f"Key {key_id} not found"
            }), 404
        
        # Authorization check
        if requester_sae != key.recipient_sae:
            return jsonify({
                "status": "error",
                "error": "Unauthorized"
            }), 403
        
        # Mark as consumed
        key.state = QKDKey.STATE_CONSUMED
        key.consumed_at = utc_now()
        db.session.commit()
        
        print(f"[KM] 🗑️  Key {key_id} marked as consumed")
        
        return jsonify({
            "status": "success",
            "message": "Key marked as consumed"
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/api/v1/keys/cleanup', methods=['POST'])
def cleanup_expired():
    """
    Cleanup expired keys (maintenance endpoint)
    
    POST /api/v1/keys/cleanup
    
    Response:
    {
        "status": "success",
        "removed_count": 5
    }
    """
    try:
        count = QKDKey.cleanup_expired_keys()
        
        return jsonify({
            "status": "success",
            "removed_count": count,
            "message": f"Cleaned up {count} expired keys"
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/api/v1/keys/list', methods=['GET'])
def list_keys():
    """
    List keys for a given email (matches requester or recipient).

    GET /api/v1/keys/list?email=user@example.com&limit=200
    """
    try:
        email = request.args.get('email')
        limit = int(request.args.get('limit', 200))
        if not email:
            return jsonify({"status": "error", "error": "email query param required"}), 400

        keys = (
            QKDKey.query.filter(
                or_(
                    QKDKey.requester_sae == email,
                    QKDKey.recipient_sae == email,
                )
            )
            .order_by(desc(QKDKey.created_at))
            .limit(limit)
            .all()
        )

        data = [
            {
                **k.to_dict(include_key_material=True),
                "km_instance": k.km_instance,
                "state": k.state,
                "served_at": k.served_at.isoformat() if k.served_at else None,
                "consumed_at": k.consumed_at.isoformat() if k.consumed_at else None,
            }
            for k in keys
        ]

        return jsonify({"status": "success", "keys": data})
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "status": "error",
        "error": "Endpoint not found"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "status": "error",
        "error": "Internal server error"
    }), 500


# ==================== Run Server ====================

if __name__ == '__main__':
    host = os.getenv('KM_HOST', '0.0.0.0')
    port = int(os.getenv('KM_PORT', '5001'))
    debug = os.getenv('KM_DEBUG', 'True').lower() == 'true'
    
    print("=" * 60)
    print("🔐 QuteMail Key Management Service - ETSI GS QKD 014")
    print("=" * 60)
    print(f"Host: {host}:{port}")
    print(f"Debug: {debug}")
    print(f"Database: {os.getenv('DATABASE_URL', 'sqlite:///km_keys.db')}")
    print("=" * 60)
    
    app.run(host=host, port=port, debug=debug)
