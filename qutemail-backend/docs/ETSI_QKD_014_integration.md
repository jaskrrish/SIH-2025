# ETSI GS QKD 014 Integration

## Overview

This document describes the integration of the ETSI GS QKD 014 standard for Quantum Key Distribution (QKD) in the QtEmail backend.

## ETSI GS QKD 014 Standard

ETSI GS QKD 014 defines the protocol and data format for communication between a Key Management (KM) layer and applications using QKD.

### Key Components

1. **SAE (Secure Application Entity)**: The application requesting keys
2. **KM (Key Management)**: The QKD system managing quantum keys
3. **Key IDs**: Unique identifiers for quantum keys
4. **Key Material**: The actual cryptographic key data

## API Endpoints

### 1. Get Encryption Keys

**Endpoint**: `POST /api/v1/keys/{sae_id}/enc_keys`

**Request**:
```json
{
  "number": 1,
  "size": 256
}
```

**Response**:
```json
{
  "keys": [
    {
      "key_ID": "unique-key-identifier",
      "key": "base64-encoded-key-material"
    }
  ]
}
```

### 2. Get Decryption Keys

**Endpoint**: `POST /api/v1/keys/{sae_id}/dec_keys`

**Request**:
```json
{
  "key_IDs": [
    {"key_ID": "unique-key-identifier"}
  ]
}
```

**Response**:
```json
{
  "keys": [
    {
      "key_ID": "unique-key-identifier",
      "key": "base64-encoded-key-material"
    }
  ]
}
```

### 3. Get Status

**Endpoint**: `GET /api/v1/keys/{sae_id}/status`

**Response**:
```json
{
  "source_KME_ID": "kme-source",
  "target_KME_ID": "kme-target",
  "master_SAE_ID": "sae-master",
  "slave_SAE_ID": "sae-slave",
  "key_size": 256,
  "stored_key_count": 100,
  "max_key_count": 1000,
  "max_key_per_request": 10,
  "max_key_size": 4096,
  "min_key_size": 64,
  "max_SAE_ID_count": 10
}
```

## Implementation

### Client Implementation

The `QKDKeyManagementClient` class in `apps/qkd/km_client.py` implements the ETSI GS QKD 014 client:

```python
from apps.qkd.km_client import QKDKeyManagementClient

client = QKDKeyManagementClient(km_url="http://localhost:8080")

# Request a key
key_data = client.get_key(key_size=256, sae_id="alice")

# Retrieve a key by ID
key = client.get_key_with_id(key_id="key-123", sae_id="alice")

# Check status
status = client.get_status(sae_id="alice")
```

### BB84 Simulator

For development and testing without a real QKD system, we provide a BB84 simulator in `apps/qkd/simulator.py`:

```python
from apps.qkd.simulator import BB84Simulator

simulator = BB84Simulator(error_rate=0.01)
alice_key, bob_key = simulator.generate_key_pair(key_size=256)
```

## Configuration

Set the following environment variables:

```bash
# Production mode (use real QKD KM)
QKD_KM_URL=http://qkd-km-server:8080
QKD_SIMULATOR_MODE=False

# Development mode (use BB84 simulator)
QKD_SIMULATOR_MODE=True
```

## Security Considerations

1. **Key Usage**: Each QKD key should be used only once (one-time pad principle)
2. **Key Storage**: Keys should be stored securely and deleted after use
3. **Authentication**: Communication with KM should be authenticated
4. **TLS**: Use TLS for communication with KM in production
5. **SAE Registration**: SAEs must be registered with the KM before requesting keys

## References

- [ETSI GS QKD 014](https://www.etsi.org/deliver/etsi_gs/QKD/001_099/014/01.01.01_60/gs_QKD014v010101p.pdf)
- [ETSI QKD Standards](https://www.etsi.org/technologies/quantum-key-distribution)
