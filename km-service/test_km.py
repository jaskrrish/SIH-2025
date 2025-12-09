"""
Test script for KM Service
Tests the full flow: Alice requests key → Bob retrieves key
"""
import requests
import json
import time

KM_URL = "http://localhost:5001"

def test_health_check():
    """Test 1: Health check"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    response = requests.get(f"{KM_URL}/api/v1/status")
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    
    assert response.status_code == 200
    assert response.json()['status'] == 'OK'
    print("✅ Health check passed")


def test_key_request_and_retrieval():
    """Test 2: Full key exchange flow"""
    print("\n" + "="*60)
    print("TEST 2: Key Request and Retrieval Flow")
    print("="*60)
    
    # Alice requests a key to send to Bob
    print("\n👤 Alice (jeyasurya0207@gmail.com) requesting key for Bob (aalan@qutemail.tech)...")
    
    request_data = {
        "requester_sae": "jeyasurya0207@gmail.com",
        "recipient_sae": "aalan@qutemail.tech",
        "key_size": 256,
        "ttl": 3600
    }
    
    response = requests.post(f"{KM_URL}/api/v1/keys/request", json=request_data)
    print(f"\nStatus Code: {response.status_code}")
    
    alice_response = response.json()
    print(json.dumps(alice_response, indent=2))
    
    assert response.status_code == 200
    assert alice_response['status'] == 'success'
    
    alice_key_id = alice_response['key_id']
    alice_key = alice_response['key']
    
    print(f"\n✅ Alice received key:")
    print(f"   Key ID: {alice_key_id}")
    print(f"   Key (first 32 chars): {alice_key[:32]}...")
    
    # Extract Bob's key ID (replace -alice with -bob)
    bob_key_id = alice_key_id.replace('-alice', '-bob')
    
    # Wait a moment
    time.sleep(0.5)
    
    # Bob retrieves his matching key
    print(f"\n👤 Bob (aalan@qutemail.tech) retrieving matching key {bob_key_id}...")
    
    response = requests.get(
        f"{KM_URL}/api/v1/keys/{bob_key_id}",
        params={"requester_sae": "aalan@qutemail.tech"}
    )
    
    print(f"\nStatus Code: {response.status_code}")
    
    bob_response = response.json()
    print(json.dumps(bob_response, indent=2))
    
    assert response.status_code == 200
    assert bob_response['status'] == 'success'
    
    bob_key = bob_response['key']
    
    print(f"\n✅ Bob received key:")
    print(f"   Key ID: {bob_key_id}")
    print(f"   Key (first 32 chars): {bob_key[:32]}...")
    
    # Verify keys match
    print(f"\n🔐 Verifying keys match...")
    assert alice_key == bob_key, "Keys don't match!"
    print("✅ Keys match! Alice and Bob have the same key material.")
    
    return alice_key_id, bob_key_id


def test_unauthorized_access():
    """Test 3: Unauthorized access attempt"""
    print("\n" + "="*60)
    print("TEST 3: Unauthorized Access Attempt")
    print("="*60)
    
    # First, create a key
    request_data = {
        "requester_sae": "alice@example.com",
        "recipient_sae": "bob@example.com"
    }
    
    response = requests.post(f"{KM_URL}/api/v1/keys/request", json=request_data)
    bob_key_id = response.json()['key_id'].replace('-alice', '-bob')
    
    # Try to access with wrong SAE
    print(f"\n👤 Charlie trying to access Bob's key (should fail)...")
    
    response = requests.get(
        f"{KM_URL}/api/v1/keys/{bob_key_id}",
        params={"requester_sae": "charlie@example.com"}
    )
    
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    
    assert response.status_code == 403
    print("✅ Unauthorized access correctly blocked")


def test_key_reuse():
    """Test 4: Key pool reuse"""
    print("\n" + "="*60)
    print("TEST 4: Key Pool Reuse")
    print("="*60)
    
    alice_sae = "alice2@example.com"
    bob_sae = "bob2@example.com"
    
    # First request - should create new key
    print(f"\n👤 First request from {alice_sae} to {bob_sae}...")
    
    response1 = requests.post(f"{KM_URL}/api/v1/keys/request", json={
        "requester_sae": alice_sae,
        "recipient_sae": bob_sae
    })
    
    result1 = response1.json()
    print(f"Source: {result1.get('source')}")
    assert result1['source'] == 'qkd_orchestrator'
    
    # Second request - should reuse from pool (but we marked first as SERVED)
    # So it should create a new one
    print(f"\n👤 Second request from {alice_sae} to {bob_sae}...")
    
    response2 = requests.post(f"{KM_URL}/api/v1/keys/request", json={
        "requester_sae": alice_sae,
        "recipient_sae": bob_sae
    })
    
    result2 = response2.json()
    print(f"Source: {result2.get('source')}")
    
    print("✅ Key pool management working")


def test_key_consumption():
    """Test 5: Mark key as consumed"""
    print("\n" + "="*60)
    print("TEST 5: Key Consumption")
    print("="*60)
    
    # Create a key
    response = requests.post(f"{KM_URL}/api/v1/keys/request", json={
        "requester_sae": "alice3@example.com",
        "recipient_sae": "bob3@example.com"
    })
    
    bob_key_id = response.json()['key_id'].replace('-alice', '-bob')
    
    # Consume the key
    print(f"\n👤 Bob consuming key {bob_key_id}...")
    
    response = requests.post(f"{KM_URL}/api/v1/keys/consume", json={
        "key_id": bob_key_id,
        "requester_sae": "bob3@example.com"
    })
    
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    
    assert response.status_code == 200
    
    # Try to retrieve consumed key
    print(f"\n👤 Attempting to retrieve consumed key (should fail)...")
    
    response = requests.get(
        f"{KM_URL}/api/v1/keys/{bob_key_id}",
        params={"requester_sae": "bob3@example.com"}
    )
    
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 410
    print("✅ Consumed key correctly rejected")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 QuteMail KM Service - Test Suite")
    print("="*60)
    
    try:
        test_health_check()
        test_key_request_and_retrieval()
        test_unauthorized_access()
        test_key_reuse()
        test_key_consumption()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ TEST FAILED: {str(e)}")
        print("="*60)
        raise


if __name__ == "__main__":
    run_all_tests()
