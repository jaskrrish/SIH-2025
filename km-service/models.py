"""
Database models for QKD Key Management
ETSI GS QKD 014 compliant key storage with encryption at rest
"""
import os
import uuid
import base64
from datetime import datetime, timedelta
from database import db
from cryptography.fernet import Fernet


class QKDKey(db.Model):
    """
    Store quantum-generated keys with encryption at rest
    Compliant with ETSI GS QKD 014 key lifecycle
    """
    __tablename__ = 'qkd_keys'
    
    # Key identification
    key_id = db.Column(db.String(50), primary_key=True)  # UUID with suffix (e.g., uuid-alice)
    key_id_extension = db.Column(db.String(255), default='')
    
    # Encrypted key material (NEVER store plaintext!)
    encrypted_key_material = db.Column(db.LargeBinary, nullable=False)
    key_size = db.Column(db.Integer, nullable=False)  # bits
    
    # SAE identities
    requester_sae = db.Column(db.String(255), nullable=False, index=True)  # Alice
    recipient_sae = db.Column(db.String(255), nullable=False, index=True)  # Bob
    
    # Which KM instance this key belongs to (KM1 for Alice, KM2 for Bob)
    km_instance = db.Column(db.String(10), nullable=False)  # 'KM1' or 'KM2'
    
    # Key lifecycle states (ETSI requirement)
    STATE_STORED = 'STORED'
    STATE_CACHED = 'CACHED'
    STATE_SERVED = 'SERVED'
    STATE_CONSUMED = 'CONSUMED'
    
    state = db.Column(db.String(10), default=STATE_STORED, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow(), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    served_at = db.Column(db.DateTime)
    consumed_at = db.Column(db.DateTime)
    
    # QKD algorithm metadata
    algorithm = db.Column(db.String(50), default='BB84')
    
    # Pairing - links alice and bob keys
    pair_key_id = db.Column(db.String(50), index=True)  # UUID with suffix of matching key
    
    def __repr__(self):
        return f"<QKDKey {self.key_id[:8]}... {self.km_instance} {self.state}>"
    
    @staticmethod
    def _get_cipher():
        """Get Fernet cipher for encryption/decryption"""
        encryption_key = os.getenv('KM_ENCRYPTION_KEY', 'dev-key-change-in-production-32b')
        # Ensure key is 32 bytes
        key_bytes = encryption_key.encode()[:32].ljust(32, b'0')
        key = base64.urlsafe_b64encode(key_bytes)
        return Fernet(key)
    
    def encrypt_key_material(self, key_bytes: bytes):
        """Encrypt key material before storage"""
        cipher = self._get_cipher()
        self.encrypted_key_material = cipher.encrypt(key_bytes)
    
    def decrypt_key_material(self) -> bytes:
        """Decrypt key material for retrieval"""
        cipher = self._get_cipher()
        return cipher.decrypt(self.encrypted_key_material)
    
    def to_dict(self, include_key_material=False):
        """Convert to dictionary for API responses"""
        result = {
            'key_id': self.key_id,
            'key_id_extension': self.key_id_extension,
            'size': self.key_size,
            'requester_sae': self.requester_sae,
            'recipient_sae': self.recipient_sae,
            'km_instance': self.km_instance,
            'state': self.state,
            'algorithm': self.algorithm,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
        }
        
        if include_key_material:
            # Decrypt and encode as base64
            key_bytes = self.decrypt_key_material()
            result['key'] = base64.b64encode(key_bytes).decode('utf-8')
        
        return result
    
    @classmethod
    def create_key_pair(cls, requester_sae, recipient_sae, alice_key_bytes, bob_key_bytes, 
                       key_size=256, ttl_seconds=3600, algorithm='BB84'):
        """
        Create a pair of matching keys (for Alice and Bob)
        This simulates KM1 and KM2 having matching keys
        """
        # Generate shared key ID
        shared_key_id = str(uuid.uuid4())
        alice_key_id = f"{shared_key_id}-alice"
        bob_key_id = f"{shared_key_id}-bob"
        
        now = datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()
        expiry = now + timedelta(seconds=ttl_seconds)
        
        # Create Alice's key (KM1)
        alice_key = cls(
            key_id=alice_key_id,
            key_size=key_size,
            requester_sae=requester_sae,
            recipient_sae=recipient_sae,
            km_instance='KM1',
            state=cls.STATE_STORED,
            expires_at=expiry,
            algorithm=algorithm,
            pair_key_id=bob_key_id
        )
        alice_key.encrypt_key_material(alice_key_bytes)
        
        # Create Bob's key (KM2)
        bob_key = cls(
            key_id=bob_key_id,
            key_size=key_size,
            requester_sae=requester_sae,
            recipient_sae=recipient_sae,
            km_instance='KM2',
            state=cls.STATE_STORED,
            expires_at=expiry,
            algorithm=algorithm,
            pair_key_id=alice_key_id
        )
        bob_key.encrypt_key_material(bob_key_bytes)
        
        return alice_key, bob_key
    
    @classmethod
    def find_available_key(cls, requester_sae, recipient_sae, km_instance):
        """
        Find an unused key for the SAE pair
        Returns key in STORED or CACHED state
        """
        now = datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()
        return cls.query.filter(
            cls.requester_sae == requester_sae,
            cls.recipient_sae == recipient_sae,
            cls.km_instance == km_instance,
            cls.state.in_([cls.STATE_STORED, cls.STATE_CACHED]),
            cls.expires_at > now
        ).first()
    
    @classmethod
    def cleanup_expired_keys(cls):
        """Remove expired keys from database"""
        now = datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()
        expired = cls.query.filter(cls.expires_at < now).all()
        count = len(expired)
        for key in expired:
            db.session.delete(key)
        db.session.commit()
        return count
