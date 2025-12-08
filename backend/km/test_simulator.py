import pathlib
import sys
import numpy as np
import pytest

# Ensure project root is on sys.path for imports when running pytest directly
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.km.simulator import BB84Simulator, QKDKey, MAX_SIM_QUBITS

def test_generate_key_pair_basic():
    np.random.seed(123)  # makes random_bits deterministic
    sim = BB84Simulator(error_rate=0.0)
    key_size = 16  # prepared_qubits=32 > MAX_SIM_QUBITS (20), so classical path
    alice_key, bob_key = sim.generate_key_pair(key_size=key_size)

    assert isinstance(alice_key, QKDKey)
    assert isinstance(bob_key, QKDKey)
    assert alice_key.key_id == bob_key.key_id
    assert alice_key.key_size == key_size
    assert bob_key.key_size == key_size
    assert alice_key.key_material == bob_key.key_material
    assert len(alice_key.key_material) * 8 == key_size  # bytes -> bits
    # Stored in key_store and retrievable
    assert sim.get_key(alice_key.key_id) == alice_key.key_material

def test_generate_with_noise_still_sizes_and_matches():
    np.random.seed(456)
    sim = BB84Simulator(error_rate=0.05)  # uses bitflip noise
    key_size = 16
    alice_key, bob_key = sim.generate_key_pair(key_size=key_size)
    assert alice_key.key_material == bob_key.key_material
    assert len(alice_key.key_material) * 8 == key_size


def test_show_key_pair(capsys):
    """
    Helper test to view a generated key pair. Run with `-s` to see prints:
    pytest -q -s backend/km/test_simulator.py::test_show_key_pair
    """
    np.random.seed(789)
    sim = BB84Simulator(error_rate=0.0)
    alice_key, bob_key = sim.generate_key_pair(key_size=256)

    print(f"Key ID: {alice_key.key_id}")
    print(f"Alice key hex: {alice_key.key_material.hex()}")
    print(f"Bob key hex:   {bob_key.key_material.hex()}")
    # Keep a simple sanity check so the test still validates behavior
    assert alice_key.key_material == bob_key.key_material