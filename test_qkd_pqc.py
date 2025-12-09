"""
QKD+PQC Implementation Validation Script
Tests the complete encryption/decryption flow
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qutemail_core.settings')

import django
django.setup()

from crypto import level_qkd_pqc
from kyber import Kyber768
import base64


def test_kyber_basic():
    """Test basic Kyber operations"""
    print("\n" + "="*60)
    print("TEST 1: Basic Kyber KEM Operations")
    print("="*60)
    
    # Generate keypair
    print("Generating Kyber768 keypair...")
    public_key, private_key = Kyber768.keygen()
    print(f"✅ Public key size: {len(public_key)} bytes")
    print(f"✅ Private key size: {len(private_key)} bytes")
    
    # Encapsulation
    print("\nPerforming encapsulation...")
    encapsulated_key, shared_secret_alice = Kyber768.enc(public_key)
    print(f"✅ Encapsulated key size: {len(encapsulated_key)} bytes")
    print(f"✅ Shared secret size: {len(shared_secret_alice)} bytes")
    
    # Decapsulation
    print("\nPerforming decapsulation...")
    shared_secret_bob = Kyber768.dec(encapsulated_key, private_key)
    print(f"✅ Decapsulated shared secret size: {len(shared_secret_bob)} bytes")
    
    # Verify match
    if shared_secret_alice == shared_secret_bob:
        print("✅ SUCCESS: Shared secrets match!")
        return True
    else:
        print("❌ FAILED: Shared secrets don't match!")
        return False


def test_level_qkd_pqc():
    """Test level_qkd_pqc encrypt/decrypt"""
    print("\n" + "="*60)
    print("TEST 2: QKD+PQC Level Encryption/Decryption")
    print("="*60)
    
    # This test requires KM service to be running
    print("⚠️  This test requires KM service running on localhost:5001")
    print("    Start with: cd km-service && python app.py")
    
    try:
        from crypto.km_client import km_client
        
        # Check KM service health
        print("\nChecking KM service status...")
        health = km_client.check_health()
        if health.get('status') != 'OK':
            print(f"❌ KM service not available: {health}")
            return False
        print("✅ KM service is running")
        
        # Generate test keypairs
        print("\nGenerating PQC keypairs for test users...")
        alice_keypair = km_client.generate_pqc_keypair(user_sae='alice@test.com')
        bob_keypair = km_client.generate_pqc_keypair(user_sae='bob@test.com')
        print(f"✅ Alice keypair: {alice_keypair['key_id']}")
        print(f"✅ Bob keypair: {bob_keypair['key_id']}")
        
        # Test encryption
        print("\nEncrypting message...")
        plaintext = b"Hello, this is a test message for QKD+PQC encryption!"
        
        encryption_result = level_qkd_pqc.encrypt(
            plaintext=plaintext,
            requester_sae='alice@test.com',
            recipient_sae='bob@test.com'
        )
        
        print(f"✅ Ciphertext length: {len(encryption_result['ciphertext'])} chars")
        print(f"✅ Encapsulated blob length: {len(encryption_result['metadata']['encapsulated_blob'])} chars")
        print(f"✅ Algorithm: {encryption_result['metadata']['algorithm']}")
        
        # Test decryption
        print("\nDecrypting message...")
        decrypted = level_qkd_pqc.decrypt(
            ciphertext=encryption_result['ciphertext'],
            encapsulated_blob=encryption_result['metadata']['encapsulated_blob'],
            requester_sae='bob@test.com'
        )
        
        print(f"✅ Decrypted length: {len(decrypted)} bytes")
        
        # Verify match
        if decrypted == plaintext:
            print(f"✅ SUCCESS: Decrypted message matches!")
            print(f"   Original:  {plaintext.decode('utf-8')}")
            print(f"   Decrypted: {decrypted.decode('utf-8')}")
            return True
        else:
            print("❌ FAILED: Decrypted message doesn't match!")
            print(f"   Original:  {plaintext}")
            print(f"   Decrypted: {decrypted}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_key_derivation():
    """Test HKDF key derivation"""
    print("\n" + "="*60)
    print("TEST 3: HKDF Key Derivation Consistency")
    print("="*60)
    
    # Simulate shared secret
    shared_secret = os.urandom(32)
    print(f"Shared secret: {base64.b64encode(shared_secret).decode()[:50]}...")
    
    # Derive keys (should be identical)
    key1 = level_qkd_pqc.derive_aes_key_from_shared_secret(shared_secret)
    key2 = level_qkd_pqc.derive_aes_key_from_shared_secret(shared_secret)
    
    print(f"Key 1: {base64.b64encode(key1).decode()[:50]}...")
    print(f"Key 2: {base64.b64encode(key2).decode()[:50]}...")
    
    if key1 == key2:
        print("✅ SUCCESS: Derived keys are identical!")
        return True
    else:
        print("❌ FAILED: Derived keys don't match!")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🔐 QKD+PQC Implementation Validation")
    print("="*60)
    
    results = []
    
    # Test 1: Basic Kyber
    results.append(("Kyber KEM Operations", test_kyber_basic()))
    
    # Test 2: Key Derivation
    results.append(("HKDF Key Derivation", test_key_derivation()))
    
    # Test 3: Full encrypt/decrypt (requires KM service)
    results.append(("QKD+PQC Encrypt/Decrypt", test_level_qkd_pqc()))
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("="*60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
    print("="*60)
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
