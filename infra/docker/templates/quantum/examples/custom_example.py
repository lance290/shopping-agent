"""
Custom Quantum Algorithm Template
Build your own quantum algorithms using PennyLane (framework-agnostic)
"""
import pennylane as qml
import numpy as np

def custom_quantum_circuit(params, wires=2):
    """
    Custom parametrized quantum circuit
    Modify this to implement your own quantum algorithm
    """
    # Example: Variational Quantum Eigensolver (VQE) ansatz
    for i in range(wires):
        qml.RY(params[i], wires=i)
    
    for i in range(wires - 1):
        qml.CNOT(wires=[i, i + 1])
    
    for i in range(wires):
        qml.RZ(params[wires + i], wires=i)

def custom_cost_function(params):
    """
    Custom cost function for variational quantum algorithm
    Modify this to define your optimization objective
    """
    # Example: Expectation value of Pauli-Z on all qubits
    dev = qml.device("default.qubit", wires=2)
    
    @qml.qnode(dev)
    def circuit(params):
        custom_quantum_circuit(params, wires=2)
        return qml.expval(qml.PauliZ(0) @ qml.PauliZ(1))
    
    return circuit(params)

def optimize_circuit(initial_params, steps=100, learning_rate=0.1):
    """
    Optimize quantum circuit parameters
    Uses gradient descent with parameter-shift rule
    """
    params = initial_params.copy()
    opt = qml.GradientDescentOptimizer(stepsize=learning_rate)
    
    costs = []
    for step in range(steps):
        params = opt.step(custom_cost_function, params)
        cost = custom_cost_function(params)
        costs.append(cost)
        
        if step % 10 == 0:
            print(f"Step {step}: Cost = {cost:.4f}")
    
    return params, costs

def main():
    """Run custom quantum algorithm"""
    print("Custom Quantum Algorithm Template")
    print("="*50)
    
    # Initialize random parameters
    num_params = 4  # Adjust based on circuit
    initial_params = np.random.rand(num_params) * 2 * np.pi
    
    print(f"\nInitial parameters: {initial_params}")
    print(f"Initial cost: {custom_cost_function(initial_params):.4f}")
    
    print("\nOptimizing circuit...")
    final_params, costs = optimize_circuit(initial_params, steps=50)
    
    print(f"\nFinal parameters: {final_params}")
    print(f"Final cost: {costs[-1]:.4f}")
    print(f"Improvement: {costs[0] - costs[-1]:.4f}")
    
    print("\n" + "="*50)
    print("CUSTOMIZE THIS TEMPLATE:")
    print("  1. Modify custom_quantum_circuit() for your quantum algorithm")
    print("  2. Modify custom_cost_function() for your optimization goal")
    print("  3. Adjust optimization parameters (steps, learning_rate)")
    print("\nUse Cases:")
    print("  - VQE for chemistry")
    print("  - QAOA for optimization")
    print("  - Quantum machine learning")
    print("  - Custom quantum protocols")

if __name__ == "__main__":
    main()
