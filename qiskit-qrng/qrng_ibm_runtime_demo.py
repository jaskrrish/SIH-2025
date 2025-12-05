from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.transpiler import generate_preset_pass_manager
import math

# 1. Connect to IBM Quantum Platform
service = QiskitRuntimeService(
    channel="ibm_quantum_platform",
    token="xdc5VckmUgkYIFRDBJ_-6JhUtHNMXDVeVfijMhfW9XDa",  # <-- put your API key here
)

# 2. Choose one of your available hardware backends
_bitCache = ''
backend_name = "ibm_fez"  # you can also use "ibm_torino" or "ibm_marrakesh"
backend = service.backend(backend_name)

print("Using backend:", backend.name)

# 3. Build a small circuit
# qc = QuantumCircuit(1)
# qc.h(0)
# qc.measure_all()

# =================================
circuit = None
n=8
qr = QuantumRegister(n)
cr = ClassicalRegister(n)
circuit = QuantumCircuit(qr, cr)
circuit.h(qr) # Apply Hadamard gate to qubits
circuit.measure(qr,cr) 


def _bit_from_counts(counts):
    return [k for k, v in counts.items() if v == 1][0]

# Populates the bitCache with at least n more bits.
def _request_bits(n):
    global _bitCache
    iterations = math.ceil(n/circuit.width()*2)
    for _ in range(iterations):
        # Create new job and run the quantum circuit
        pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
        isa_circuit = pm.run(circuit)
        sampler = Sampler(mode=backend)  # "job mode" using this backend
        job = sampler.run([isa_circuit], shots=256)
        result = job.result()
        _bitCache += _bit_from_counts(result[0].data.c0.get_counts())


def get_bit_string(n: int) -> str:
    """
    Returns a random n-bit bitstring.

    Parameters:
        n (int): Account token on IBMQ. If no token is given, will fall back to a local provider.
    """
    global _bitCache
    if len(_bitCache) < n:
        _request_bits(n-len(_bitCache))
    bitString = _bitCache[0:n]
    _bitCache = _bitCache[n:]
    return bitString

def get_random_int32() -> int:
    """Returns a uniformly random 32 bit integer."""
    return int(get_bit_string(32),2)

# =================================

print("Original circuit:")
print(circuit)


print(get_random_int32())

# 4. Transpile the circuit for this backend (very important for real hardware)
# pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
# isa_circuit = pm.run(qc)

# print("\nTranspiled circuit:")
# print(isa_circuit)

# # 5. Run using SamplerV2 primitive
# sampler = Sampler(mode=backend)  # "job mode" using this backend
# job = sampler.run([isa_circuit], shots=256)

# print("\nJob submitted. Job ID:", job.job_id())
# result = job.result()

# # 6. Extract and print counts
# counts = result[0].data.meas.get_counts()
# print("\nResult counts from hardware:", counts)