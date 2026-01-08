"""
Xanadu Strawberry Fields Example: Photonic Quantum Computing
Demonstrate continuous-variable quantum computation with Gaussian Boson Sampling
"""
import strawberryfields as sf
from strawberryfields import ops
import numpy as np

def create_gbs_circuit(num_modes=4, cutoff=5):
    """
    Create Gaussian Boson Sampling (GBS) circuit
    GBS is a quantum advantage demonstration using photonic qubits
    """
    # Create quantum program
    prog = sf.Program(num_modes)
    
    # Define squeezing parameters (example adjacency matrix)
    # In real GBS, this encodes graph structure
    sq_params = [0.5, 0.6, 0.55, 0.6]  # Squeezing per mode
    
    with prog.context as q:
        # Apply squeezing to all modes
        for i, sq in enumerate(sq_params):
            ops.Squeezed(sq) | q[i]
        
        # Interferometer (Haar-random unitary)
        # In real GBS, this is programmable via beamsplitters
        ops.Interferometer(np.random.rand(num_modes, num_modes)) | q
        
        # Measurement in Fock basis (photon counting)
        ops.MeasureFock() | q
    
    return prog

def run_simulation(prog, shots=10, cutoff=5):
    """Run GBS on simulator"""
    # Use Fock backend (photon-number simulator)
    eng = sf.Engine("fock", backend_options={"cutoff_dim": cutoff})
    
    results = []
    for _ in range(shots):
        result = eng.run(prog)
        samples = result.samples
        results.append(samples)
    
    return results

def main():
    """Run Gaussian Boson Sampling example"""
    print("Creating Gaussian Boson Sampling circuit...")
    print("(Photonic quantum computing)\n")
    
    num_modes = 4
    circuit = create_gbs_circuit(num_modes=num_modes)
    print(circuit)
    
    print(f"\nRunning simulation with {num_modes} photonic modes...")
    results = run_simulation(circuit, shots=10)
    
    print(f"\nSample outputs (photon counts per mode):")
    for i, sample in enumerate(results[:5]):
        print(f"  Shot {i+1}: {sample}")
    
    print("\nGBS is used for:")
    print("  - Quantum advantage demonstrations")
    print("  - Graph problems (max clique, dense subgraph)")
    print("  - Molecular vibronic spectra")

if __name__ == "__main__":
    main()
