"""
Google Cirq Example: Quantum Teleportation
Demonstrate quantum teleportation protocol
"""
import cirq
import numpy as np

def create_teleportation_circuit():
    """Create quantum teleportation circuit"""
    # Create qubits
    q0 = cirq.NamedQubit("message")
    q1 = cirq.NamedQubit("alice")
    q2 = cirq.NamedQubit("bob")
    
    circuit = cirq.Circuit()
    
    # Prepare message qubit (arbitrary state)
    circuit.append(cirq.X(q0)**0.5)  # Rotate to superposition
    
    # Create Bell pair between Alice and Bob
    circuit.append([
        cirq.H(q1),
        cirq.CNOT(q1, q2)
    ])
    
    circuit.append(cirq.Moment())  # Visual separator
    
    # Alice's operations
    circuit.append([
        cirq.CNOT(q0, q1),
        cirq.H(q0)
    ])
    
    # Measure Alice's qubits
    circuit.append([
        cirq.measure(q0, key='m0'),
        cirq.measure(q1, key='m1')
    ])
    
    # Bob's corrections (classically controlled)
    # In real quantum computer, these would be conditional on measurements
    # For simulation, we'll show the full circuit
    circuit.append([
        cirq.CNOT(q1, q2),  # If m1=1
        cirq.CZ(q0, q2)     # If m0=1
    ])
    
    # Measure Bob's qubit (should match original message)
    circuit.append(cirq.measure(q2, key='result'))
    
    return circuit

def run_simulation(circuit, repetitions=100):
    """Run circuit on simulator"""
    simulator = cirq.Simulator()
    result = simulator.run(circuit, repetitions=repetitions)
    return result

def main():
    """Run teleportation example"""
    print("Creating quantum teleportation circuit...")
    circuit = create_teleportation_circuit()
    print(circuit)
    
    print("\nRunning simulation...")
    result = run_simulation(circuit, repetitions=10)
    
    print(f"\nResults:")
    print(result)
    
    print("\nQuantum teleportation transmits qubit state without physical transfer!")

if __name__ == "__main__":
    main()
