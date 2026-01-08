"""
IBM Qiskit Example: Bell State Circuit
Create and measure a quantum entanglement state
"""
from qiskit import QuantumCircuit, transpile
from qiskit_aer import Aer
from qiskit.visualization import plot_histogram
import matplotlib.pyplot as plt

def create_bell_state():
    """Create a Bell state (maximally entangled qubits)"""
    # Create quantum circuit with 2 qubits and 2 classical bits
    qc = QuantumCircuit(2, 2)
    
    # Apply Hadamard gate to qubit 0
    qc.h(0)
    
    # Apply CNOT gate (qubit 0 controls qubit 1)
    qc.cx(0, 1)
    
    # Measure qubits
    qc.measure([0, 1], [0, 1])
    
    return qc

def run_simulation(circuit, shots=1000):
    """Run circuit on simulator"""
    # Use Aer simulator
    simulator = Aer.get_backend('qasm_simulator')
    
    # Transpile circuit for simulator
    compiled_circuit = transpile(circuit, simulator)
    
    # Run simulation
    job = simulator.run(compiled_circuit, shots=shots)
    result = job.result()
    counts = result.get_counts(circuit)
    
    return counts

def main():
    """Run Bell state example"""
    print("Creating Bell state circuit...")
    circuit = create_bell_state()
    print(circuit)
    
    print("\nRunning simulation...")
    counts = run_simulation(circuit, shots=1000)
    
    print(f"\nResults (1000 shots):")
    for state, count in counts.items():
        print(f"  |{state}⟩: {count} ({count/10:.1f}%)")
    
    print("\nExpected: ~50% |00⟩ and ~50% |11⟩ (entangled state)")
    
    # Uncomment to plot histogram
    # plot_histogram(counts)
    # plt.show()

if __name__ == "__main__":
    main()
