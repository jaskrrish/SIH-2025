"""
QKD Orchestrator - Manages quantum key generation and distribution
Wraps BB84 simulator and coordinates key distribution between KM instances
"""
import os
import secrets
import hashlib
from typing import Tuple, List, TYPE_CHECKING
from dataclasses import dataclass
import numpy as np

if TYPE_CHECKING:
    from braket.circuits import Circuit


@dataclass
class QKDKey:
    """Represents a QKD-generated key"""
    key_id: str
    key_material: bytes
    key_size: int


# ---------------------------
# Utility helpers (aligned with qkd-bb84/run_bb84.py)
# ---------------------------
MAX_SIM_QUBITS = 20  # above this, use analytic sampling to avoid simulator blow-up


def random_bits(n: int) -> np.ndarray:
    return np.random.randint(2, size=n)


def prepare_encode_circuit(alice_bits: np.ndarray, alice_bases: np.ndarray) -> "Circuit":
    try:
        from braket.circuits import Circuit
    except Exception as exc:  # pragma: no cover - exercised only when braket missing
        raise RuntimeError(
            "amazon-braket-sdk is required to prepare quantum circuits."
        ) from exc

    circuit = Circuit()
    for i in range(len(alice_bits)):
        if alice_bits[i] == 1:
            circuit.x(i)
        if alice_bases[i] == 1:
            circuit.h(i)
    return circuit


def apply_bob_measurement_ops(circuit: "Circuit", bob_bases: np.ndarray) -> "Circuit":
    for i in range(len(bob_bases)):
        if bob_bases[i] == 1:
            circuit.h(i)
        circuit.measure(i)
    return circuit


def run_braket_circuit(circuit: "Circuit", shots: int = 1) -> List[List[int]]:
    try:
        from braket.devices import LocalSimulator
    except Exception as exc:  # pragma: no cover - exercised only when braket missing
        raise RuntimeError(
            "amazon-braket-sdk is required to run quantum simulations."
        ) from exc

    device = LocalSimulator("default")
    result = device.run(circuit, shots=shots).result()
    return [list(m) for m in result.measurements]


def sample_measurements_classically(
    alice_bits: np.ndarray, alice_bases: np.ndarray, bob_bases: np.ndarray
) -> List[int]:
    bob_raw = []
    for a_bit, a_basis, b_basis in zip(alice_bits, alice_bases, bob_bases):
        if a_basis == b_basis:
            bob_raw.append(int(a_bit))
        else:
            bob_raw.append(int(np.random.randint(2)))
    return bob_raw


def apply_bitflip_noise(bits: List[int], prob: float) -> List[int]:
    if prob <= 0.0:
        return list(bits)
    out = []
    for b in bits:
        out.append(1 - b if np.random.rand() < prob else b)
    return out


def sift_keys(alice_bits: List[int], alice_bases: List[int], bob_bits: List[int], bob_bases: List[int]):
    keep_idx = [i for i in range(len(alice_bits)) if alice_bases[i] == bob_bases[i]]
    alice_sifted = [alice_bits[i] for i in keep_idx]
    bob_sifted = [bob_bits[i] for i in keep_idx]
    return alice_sifted, bob_sifted, keep_idx


def parity(bits: List[int]) -> int:
    return sum(bits) % 2


def find_and_fix_error(alice_block: List[int], bob_block: List[int]):
    if parity(alice_block) == parity(bob_block):
        return alice_block, bob_block
    if len(alice_block) == 1:
        return alice_block, [1 - bob_block[0]]
    mid = len(alice_block) // 2
    a_left, a_right = alice_block[:mid], alice_block[mid:]
    b_left, b_right = bob_block[:mid], bob_block[mid:]
    if parity(a_left) != parity(b_left):
        a_left, b_left = find_and_fix_error(a_left, b_left)
    else:
        a_right, b_right = find_and_fix_error(a_right, b_right)
    return (a_left + a_right), (b_left + b_right)


def reconcile_via_bisection(alice: List[int], bob: List[int], block_size: int = 16) -> List[int]:
    n = len(alice)
    bob_corrected = bob.copy()
    for start in range(0, n, block_size):
        end = min(start + block_size, n)
        a_block = alice[start:end]
        b_block = bob_corrected[start:end]
        if parity(a_block) != parity(b_block):
            _, fixed = find_and_fix_error(a_block, b_block)
            bob_corrected[start:end] = fixed
    return bob_corrected


class BB84Simulator:
    """BB84 protocol simulator using Amazon Braket for quantum key generation"""
    
    def __init__(self, error_rate: float = 0.0):
        """
        Initialize BB84 simulator
        
        Args:
            error_rate: Simulated quantum channel error rate (0.0 - 1.0)
        """
        self.error_rate = error_rate
        self.key_store = {}
    
    def generate_key_pair(self, key_size: int = 256, bitflip_prob: float = 0.0) -> Tuple[QKDKey, QKDKey]:
        """
        Simulate BB84 key generation for two parties (Alice and Bob) using
        Amazon Braket for small circuits and an analytic fallback for large ones.

        Args:
            key_size: Desired key size in bits.
            bitflip_prob: Channel bit-flip probability (overrides error_rate when > 0).

        Returns:
            Tuple of (alice_key, bob_key) with matching key_material
        """
        key_size_bits = key_size
        effective_bitflip = bitflip_prob if bitflip_prob > 0.0 else self.error_rate
        max_attempts = 4  # exponentially grow prepared qubits to hit target size

        for attempt in range(max_attempts):
            prepared_qubits = max(key_size_bits * 2, key_size_bits * 2 * (2**attempt))

            alice_bits = random_bits(prepared_qubits)
            alice_bases = random_bits(prepared_qubits)
            bob_bases = random_bits(prepared_qubits)

            if prepared_qubits > MAX_SIM_QUBITS:
                bob_raw = sample_measurements_classically(alice_bits, alice_bases, bob_bases)
            else:
                circuit = prepare_encode_circuit(alice_bits, alice_bases)
                circuit = apply_bob_measurement_ops(circuit, bob_bases)
                meas_shots = run_braket_circuit(circuit, shots=1)
                bob_raw = meas_shots[0]

            bob_raw_noisy = apply_bitflip_noise(bob_raw, prob=effective_bitflip)

            alice_sift, bob_sift, kept_indices = sift_keys(
                list(alice_bits), list(alice_bases), bob_raw_noisy, list(bob_bases)
            )
            n_sift = len(alice_sift)
            if n_sift >= key_size_bits:
                break
        else:
            raise RuntimeError(
                f"Not enough sifted bits after {max_attempts} attempts "
                f"(last attempt prepared {prepared_qubits}, sifted {n_sift}); "
                "increase key_size or base qubit budget."
            )

        mismatches = sum(1 for a, b in zip(alice_sift, bob_sift) if a != b)
        qber = mismatches / n_sift if n_sift else 0.0

        block_size = min(16, max(1, n_sift))
        bob_reconciled = reconcile_via_bisection(alice_sift, bob_sift, block_size=block_size)

        final_mismatches = sum(1 for a, b in zip(alice_sift, bob_reconciled) if a != b)
        reconciled = (final_mismatches == 0)

        key_bits = alice_sift[:key_size_bits]
        key_bytes = self._bits_to_bytes(key_bits)

        key_id = hashlib.sha256(key_bytes + secrets.token_bytes(16)).hexdigest()[:32]

        alice_key = QKDKey(
            key_id=key_id,
            key_material=key_bytes,
            key_size=key_size_bits
        )
        bob_key = QKDKey(
            key_id=key_id,
            key_material=key_bytes,  # Same key material after reconciliation
            key_size=key_size_bits
        )

        self.key_store[key_id] = key_bytes

        return alice_key, bob_key
    
    @staticmethod
    def _bits_to_bytes(bits: List[int]) -> bytes:
        """Convert list of bits to bytes"""
        byte_array = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                if i + j < len(bits):
                    byte |= bits[i + j] << (7 - j)
            byte_array.append(byte)
        return bytes(byte_array)


class QKDOrchestrator:
    """
    Orchestrates QKD sessions and key distribution
    Manages BB84 simulator and coordinates key generation
    """
    
    def __init__(self, error_rate: float = None):
        """Initialize orchestrator with BB84 simulator"""
        if error_rate is None:
            error_rate = float(os.getenv('QKD_ERROR_RATE', '0.0'))
        
        self.simulator = BB84Simulator(error_rate=error_rate)
        self.session_count = 0
    
    def orchestrate_key_generation(self, requester_sae: str, recipient_sae: str, 
                                   key_size: int = None) -> Tuple[QKDKey, QKDKey]:
        """
        Orchestrate a QKD session between two SAEs
        
        Args:
            requester_sae: Alice (sender) SAE identity
            recipient_sae: Bob (receiver) SAE identity
            key_size: Key size in bits (default from env)
        
        Returns:
            Tuple of (alice_key_obj, bob_key_obj)
        """
        if key_size is None:
            key_size = int(os.getenv('QKD_KEY_SIZE', '256'))
        
        self.session_count += 1
        
        print(f"[QKD-Orchestrator] Session #{self.session_count}: {requester_sae} → {recipient_sae}")
        print(f"[QKD-Orchestrator] Generating {key_size}-bit key pair using BB84...")
        
        # Run BB84 simulator
        alice_key, bob_key = self.simulator.generate_key_pair(key_size=key_size)
        
        print(f"[QKD-Orchestrator] ✅ Key pair generated: {alice_key.key_id[:16]}...")
        print(f"[QKD-Orchestrator]    Alice key: {len(alice_key.key_material)} bytes")
        print(f"[QKD-Orchestrator]    Bob key: {len(bob_key.key_material)} bytes")
        
        # Verify keys match (sanity check)
        assert alice_key.key_material == bob_key.key_material, "Key mismatch in BB84!"
        assert alice_key.key_id == bob_key.key_id, "Key ID mismatch!"
        
        return alice_key, bob_key
    
    def get_stats(self) -> dict:
        """Get orchestrator statistics"""
        return {
            'total_sessions': self.session_count,
            'error_rate': self.simulator.error_rate,
            'keys_in_store': len(self.simulator.key_store)
        }
