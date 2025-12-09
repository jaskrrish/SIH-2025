"""
Smart Email Caching Service
Handles Redis caching with intelligent fetch logic
"""
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import json
from typing import Optional, List, Dict
from .models import EmailMetadata
from .imap_client import IMAPClient


class EmailCacheService:
    """Manage email caching with Redis"""
    
    # Cache configuration
    CACHE_TTL = 7200  # 2 hours in seconds
    FETCH_LIMIT_RECENT = 5  # Fetch 5 emails if synced < 1 hour ago
    FETCH_LIMIT_STALE = 20  # Fetch 20 emails if synced > 1 hour ago or cache empty
    SYNC_THRESHOLD = 3600  # 1 hour in seconds
    
    @staticmethod
    def _get_cache_key(message_id: str) -> str:
        """Generate cache key for email content"""
        return f"email:content:{message_id}"
    
    @staticmethod
    def _get_list_cache_key(user_id: int, account_id: int) -> str:
        """Generate cache key for email list"""
        return f"email:list:{user_id}:{account_id}"
    
    @classmethod
    def get_email_content(cls, message_id: str) -> Optional[Dict]:
        """
        Get email content from cache
        Returns: Dict with full email content or None if not cached
        """
        cache_key = cls._get_cache_key(message_id)
        content = cache.get(cache_key)
        
        if content:
            # Deserialize if stored as JSON string
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except:
                    return None
        
        return content
    
    @classmethod
    def cache_email_content(cls, message_id: str, email_data: Dict) -> bool:
        """
        Cache email content in Redis
        
        Args:
            message_id: Unique email identifier
            email_data: Full email content dict
        
        Returns: True if cached successfully
        """
        from datetime import datetime
        import base64
        
        cache_key = cls._get_cache_key(message_id)
        
        # Recursively serialize datetime and bytes objects for JSON
        def deep_serialize(data):
            if isinstance(data, dict):
                return {k: deep_serialize(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [deep_serialize(item) for item in data]
            elif isinstance(data, datetime):
                return data.isoformat()
            elif isinstance(data, bytes):
                return base64.b64encode(data).decode('utf-8')
            return data
        
        try:
            serializable_data = deep_serialize(email_data)
            # Serialize to JSON for storage
            cache.set(cache_key, json.dumps(serializable_data), timeout=cls.CACHE_TTL)
            return True
        except Exception as e:
            print(f"[CACHE] ❌ Failed to cache email {message_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    @classmethod
    def invalidate_email(cls, message_id: str):
        """Remove email from cache"""
        cache_key = cls._get_cache_key(message_id)
        cache.delete(cache_key)
    
    @classmethod
    def get_cached_email_list(cls, user_id: int, account_id: int) -> Optional[List[str]]:
        """Get list of cached message IDs"""
        cache_key = cls._get_list_cache_key(user_id, account_id)
        cached_list = cache.get(cache_key)
        
        if cached_list and isinstance(cached_list, str):
            try:
                return json.loads(cached_list)
            except:
                return None
        
        return cached_list
    
    @classmethod
    def update_email_list_cache(cls, user_id: int, account_id: int, message_ids: List[str]):
        """Update cached email list"""
        cache_key = cls._get_list_cache_key(user_id, account_id)
        cache.set(cache_key, json.dumps(message_ids), timeout=cls.CACHE_TTL)
    
    @classmethod
    def should_fetch_emails(cls, account) -> tuple[bool, int]:
        """
        Determine if emails should be fetched and how many
        
        Returns: (should_fetch: bool, limit: int)
        """
        now = timezone.now()
        
        # No sync yet - fetch initial batch
        if not account.last_synced:
            return True, cls.FETCH_LIMIT_STALE
        
        # Calculate time since last sync
        time_since_sync = (now - account.last_synced).total_seconds()
        
        # Synced > 1 hour ago - fetch larger batch
        if time_since_sync > cls.SYNC_THRESHOLD:
            return True, cls.FETCH_LIMIT_STALE
        
        # Synced recently - fetch smaller batch
        return True, cls.FETCH_LIMIT_RECENT
    
    @classmethod
    def sync_emails_smart(cls, user, account, limit_override: Optional[int] = None) -> Dict:
        """
        Smart email sync with intelligent fetch logic
        
        Returns: Dict with sync statistics
        """
        should_fetch, limit = cls.should_fetch_emails(account)
        if limit_override:
            # Respect caller override but keep it positive
            limit = max(1, min(limit, limit_override))
        
        if not should_fetch:
            return {
                'fetched': 0,
                'cached': 0,
                'reason': 'No sync needed - recently synced'
            }
        
        # Fetch emails from IMAP
        imap_client = IMAPClient(account)
        imap_client.connect()
        
        try:
            fetched_emails = imap_client.fetch_emails(limit=limit)
            imap_client.disconnect()
        except Exception as e:
            imap_client.disconnect()
            raise e
        
        # Decrypt emails before caching
        from crypto import router as crypto_router
        import base64
        
        print(f"[CACHE] Processing {len(fetched_emails)} fetched emails for decryption...")
        
        for idx, email_data in enumerate(fetched_emails):
            message_id = email_data.get('message_id', 'unknown')
            subject = email_data.get('subject', 'No subject')[:50]
            security_level = email_data.get('security_level', 'regular')
            is_encrypted = email_data.get('is_encrypted', False)
            
            print(f"[CACHE] Email {idx+1}/{len(fetched_emails)}: {subject}")
            print(f"[CACHE]   - is_encrypted: {is_encrypted}, security_level: {security_level}")
            print(f"[CACHE]   - body_text length: {len(email_data.get('body_text', ''))}")
            print(f"[CACHE]   - to_emails: {email_data.get('to_emails')}")
            print(f"[CACHE]   - attachments: {len(email_data.get('attachments', []))}")
            
            # Decrypt email body if encrypted
            if is_encrypted and security_level != 'regular':
                try:
                    body_text = email_data.get('body_text', '')
                    encryption_metadata = email_data.get('encryption_metadata', {})
                    
                    if security_level == 'qkd':
                        key_id = encryption_metadata.get('key_id')
                        if not key_id:
                            raise ValueError('QKD email missing key_id')
                        # QKD requires positional args: ciphertext, key_id, requester_sae
                        decrypted_bytes = crypto_router.decrypt(
                            security_level='qkd',
                            ciphertext=body_text,
                            key_id=key_id,
                            requester_sae=account.email
                        )
                    elif security_level == 'aes':
                        aes_key = encryption_metadata.get('key')
                        if not aes_key:
                            raise ValueError('AES email missing key')
                        decrypted_bytes = crypto_router.decrypt(
                            security_level='aes',
                            ciphertext=body_text,
                            key_material=base64.b64decode(aes_key)
                        )
                    elif security_level == 'qs_otp':
                        key_id = encryption_metadata.get('key_id')
                        if not key_id:
                            raise ValueError('OTP email missing key_id')
                        # OTP requires positional args: ciphertext (string of bits), key_id, requester_sae
                        decrypted_bytes = crypto_router.decrypt(
                            security_level='qs_otp',
                            ciphertext=body_text,  # String of '0' and '1' characters
                            key_id=key_id,
                            requester_sae=account.email
                        )
                    else:
                        raise ValueError(f'Unknown security level: {security_level}')
                    email_data['body_text'] = decrypted_bytes.decode('utf-8')
                    print(f"[CACHE] ✅ Decrypted email: {email_data.get('subject', 'No subject')[:50]}")
                except Exception as e:
                    print(f"[CACHE] ❌ Failed to decrypt email {email_data.get('message_id')}: {str(e)}")
                    email_data['body_text'] = f"[Encrypted message - decryption failed: {str(e)}]"
            
            # Decrypt attachments if encrypted
            attachments = email_data.get('attachments', [])
            for att in attachments:
                if att.get('is_encrypted', False) and att.get('security_level', 'regular') != 'regular':
                    try:
                        att_security_level = att.get('security_level')
                        # Attachment data is in 'file_data' from IMAP, but may be 'data' from other sources
                        att_data = att.get('file_data') or att.get('data', '')
                        # Metadata is in 'encryption_metadata' from IMAP
                        att_metadata = att.get('encryption_metadata') or att.get('metadata', {})
                        
                        print(f"[CACHE] Decrypting attachment: {att.get('filename')}")
                        print(f"[CACHE]   - att keys: {list(att.keys())}")
                        print(f"[CACHE]   - att_metadata: {att_metadata}")
                        print(f"[CACHE]   - att_data type: {type(att_data)}, len: {len(att_data) if att_data else 0}")
                        
                        if att_security_level == 'qkd':
                            key_id = att_metadata.get('key_id')
                            if not key_id:
                                raise ValueError(f"QKD attachment {att.get('filename')} missing key_id")
                            # QKD requires positional args: ciphertext, key_id, requester_sae
                            decrypted_bytes = crypto_router.decrypt(
                                security_level='qkd',
                                ciphertext=att_data,
                                key_id=key_id,
                                requester_sae=account.email
                            )
                        elif att_security_level == 'aes':
                            aes_key = att_metadata.get('key')
                            if not aes_key:
                                raise ValueError(f"AES attachment {att.get('filename')} missing key")
                            decrypted_bytes = crypto_router.decrypt(
                                security_level='aes',
                                ciphertext=att_data,
                                key_material=base64.b64decode(aes_key)
                            )
                        elif att_security_level == 'qs_otp':
                            key_id = att_metadata.get('key_id')
                            if not key_id:
                                raise ValueError(f"OTP attachment {att.get('filename')} missing key_id")
                            # OTP requires positional args: ciphertext (string of bits), key_id, requester_sae
                            decrypted_bytes = crypto_router.decrypt(
                                security_level='qs_otp',
                                ciphertext=att_data,  # String of '0' and '1' characters
                                key_id=key_id,
                                requester_sae=account.email
                            )
                        else:
                            raise ValueError(f'Unknown security level: {att_security_level}')
                        
                        # Store decrypted data in both 'data' and 'file_data' for compatibility
                        decrypted_base64 = base64.b64encode(decrypted_bytes).decode('utf-8')
                        att['data'] = decrypted_base64
                        att['file_data'] = decrypted_base64  # Keep compatibility with IMAP structure
                        att['is_encrypted'] = False
                        # Remove encryption_metadata since it's now decrypted
                        att.pop('encryption_metadata', None)
                        print(f"[CACHE] ✅ Decrypted attachment: {att.get('filename')}")
                    except Exception as e:
                        print(f"[CACHE] ❌ Failed to decrypt attachment {att.get('filename')}: {str(e)}")
                        att['decryption_error'] = str(e)
        
        # Process fetched emails
        cached_count = 0
        new_metadata_count = 0
        
        for email_data in fetched_emails:
            message_id = email_data['message_id']
            
            # Cache full email content (now decrypted)
            if cls.cache_email_content(message_id, email_data):
                cached_count += 1
            
            # Store/update metadata in DB
            metadata, created = EmailMetadata.objects.update_or_create(
                message_id=message_id,
                defaults={
                    'user': user,
                    'account': account,
                    'subject': email_data.get('subject', '')[:500],  # Truncate
                    'from_email': email_data.get('from_email', ''),
                    'from_name': email_data.get('from_name', ''),
                    'is_encrypted': email_data.get('is_encrypted', False),
                    'has_attachments': len(email_data.get('attachments', [])) > 0,
                    'sent_at': email_data.get('sent_at'),
                }
            )
            
            if created:
                new_metadata_count += 1
        
        # Update account sync info
        account.last_synced = timezone.now()
        account.sync_count += 1
        account.total_emails_cached = cached_count
        account.save()
        
        # Update cached email list
        message_ids = [e['message_id'] for e in fetched_emails]
        cls.update_email_list_cache(user.id, account.id, message_ids)
        
        return {
            'fetched': len(fetched_emails),
            'cached': cached_count,
            'new_metadata': new_metadata_count,
            'limit': limit,
            'last_synced': account.last_synced
        }
    
    @classmethod
    def get_email_on_demand(cls, user, account, message_id: str) -> Optional[Dict]:
        """
        Get email with on-demand fetch if not cached
        
        Args:
            user: User instance
            account: EmailAccount instance
            message_id: Email message ID
        
        Returns: Full email data dict or None
        """
        # Check cache first
        cached_content = cls.get_email_content(message_id)
        if cached_content:
            return cached_content
        
        # Not in cache - fetch from IMAP
        print(f"[CACHE] Email {message_id} not in cache, fetching from IMAP...")
        
        try:
            imap_client = IMAPClient(account)
            imap_client.connect()
            
            # Fetch single email by message_id
            # Note: You'll need to add a method to IMAPClient to fetch by message_id
            email_data = imap_client.fetch_email_by_id(message_id)
            
            imap_client.disconnect()
            
            if email_data:
                # Cache it for future use
                cls.cache_email_content(message_id, email_data)
                return email_data
            
        except Exception as e:
            print(f"[CACHE] Failed to fetch email {message_id}: {str(e)}")
            return None
        
        return None
    
    @classmethod
    def clear_account_cache(cls, user_id: int, account_id: int):
        """Clear all cached emails for an account"""
        # Get all metadata
        metadata_list = EmailMetadata.objects.filter(
            user_id=user_id,
            account_id=account_id
        )
        
        # Clear each email from cache
        for metadata in metadata_list:
            cls.invalidate_email(metadata.message_id)
        
        # Clear list cache
        list_cache_key = cls._get_list_cache_key(user_id, account_id)
        cache.delete(list_cache_key)
