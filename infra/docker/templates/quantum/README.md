# Quantum Computing Development Environment

Production-ready Docker environment for quantum computing with **four frameworks**: Qiskit (IBM), Cirq (Google), Strawberry Fields (Xanadu photonic), and PennyLane (custom algorithms).

---

## Supported Frameworks

### 1. **Qiskit** (IBM Quantum)
- Gate-based quantum computing
- IBM Quantum hardware access
- Extensive algorithm library
- **Best for:** General quantum algorithms, VQE, QAOA

### 2. **Cirq** (Google Quantum)
- Gate-based quantum computing
- Google Quantum hardware access
- NISQ-era algorithms
- **Best for:** Near-term quantum algorithms, Google QPU access

### 3. **Strawberry Fields** (Xanadu Photonic)
- Continuous-variable quantum computing
- Photonic quantum computing
- Gaussian Boson Sampling
- **Best for:** GBS, photonic circuits, quantum advantage demos

### 4. **Custom** (PennyLane)
- Framework-agnostic
- Differentiable quantum programming
- Quantum machine learning
- **Best for:** Custom algorithms, VQE, quantum ML

---

## Quick Start

### Local Development

```bash
# Build Docker image
docker build -t quantum-dev .

# Run Jupyter Lab
docker run -p 8080:8080 -v $(pwd):/app quantum-dev

# Access at http://localhost:8080
```

### Run Examples

```bash
# Qiskit: Bell state entanglement
python examples/qiskit_example.py

# Cirq: Quantum teleportation
python examples/cirq_example.py

# Strawberry Fields: Gaussian Boson Sampling
python examples/strawberryfields_example.py

# Custom: Variational quantum algorithm
python examples/custom_example.py
```

---

## Framework Comparison

| Feature | Qiskit | Cirq | Strawberry Fields | Custom (PennyLane) |
|---------|--------|------|-------------------|---------------------|
| **Type** | Gate-based | Gate-based | Photonic | Framework-agnostic |
| **Hardware** | IBM Quantum | Google Quantum | Xanadu | Multiple backends |
| **Qubits** | Discrete | Discrete | Continuous-variable | Both |
| **ML Support** | Limited | Limited | Good | Excellent |
| **Learning Curve** | Medium | Medium | High | Low |
| **Use Cases** | General QC | NISQ algorithms | GBS, photonics | Custom, VQE, QML |

---

## Use Cases by Framework

### Qiskit (IBM)
```python
from qiskit import QuantumCircuit

# Quantum Fourier Transform
qc = QuantumCircuit(3)
qc.h(0)
qc.cp(np.pi/2, 0, 1)
qc.cp(np.pi/4, 0, 2)
qc.h(1)
qc.cp(np.pi/2, 1, 2)
qc.h(2)
```

**Best for:**
- Shor's algorithm (factorization)
- Grover's search
- VQE (chemistry)
- QAOA (optimization)

---

### Cirq (Google)
```python
import cirq

# Quantum random circuit
qubits = cirq.GridQubit.rect(2, 2)
circuit = cirq.Circuit()
circuit.append(cirq.H(q) for q in qubits)
circuit.append(cirq.CNOT(qubits[0], qubits[1]))
```

**Best for:**
- Quantum supremacy experiments
- Variational algorithms
- Error mitigation
- Google QPU access

---

### Strawberry Fields (Xanadu)
```python
import strawberryfields as sf

# Gaussian Boson Sampling
prog = sf.Program(4)
with prog.context as q:
    sf.ops.Squeezed(0.5) | q[0]
    sf.ops.BSgate() | (q[0], q[1])
```

**Best for:**
- Gaussian Boson Sampling
- Graph problems
- Molecular simulations
- Photonic quantum computing

---

### Custom (PennyLane)
```python
import pennylane as qml

# Quantum ML
@qml.qnode(dev)
def circuit(params, x):
    qml.RY(x, wires=0)
    qml.RY(params[0], wires=1)
    qml.CNOT(wires=[0, 1])
    return qml.expval(qml.PauliZ(1))
```

**Best for:**
- Custom quantum algorithms
- Quantum machine learning
- Hybrid quantum-classical
- Research & prototyping

---

## Hardware Access

### IBM Quantum (Qiskit)

```python
from qiskit_ibm_runtime import QiskitRuntimeService

# Save credentials (one time)
QiskitRuntimeService.save_account(
    channel="ibm_quantum",
    token="YOUR_IBM_TOKEN"
)

# Use real quantum computer
service = QiskitRuntimeService()
backend = service.backend("ibmq_manila")
job = backend.run(circuit)
```

**Get token:** https://quantum-computing.ibm.com/

---

### Google Quantum (Cirq)

```python
import cirq_google

# Access Google quantum processors
engine = cirq_google.Engine(project_id="YOUR_PROJECT_ID")
processor = engine.get_processor("YOUR_PROCESSOR")
result = processor.run(circuit)
```

**Apply for access:** https://quantumai.google/

---

### Xanadu (Strawberry Fields)

```python
import strawberryfields as sf

# Use Xanadu cloud (requires API token)
eng = sf.RemoteEngine("X8")
result = eng.run(prog)
```

**Get token:** https://cloud.xanadu.ai/

---

## Advanced Features

### 1. Variational Quantum Eigensolver (VQE)

```python
# Chemistry example (H2 molecule)
from qiskit.algorithms import VQE
from qiskit.primitives import Estimator

vqe = VQE(estimator=Estimator(), ansatz=ansatz, optimizer=optimizer)
result = vqe.compute_minimum_eigenvalue(hamiltonian)
print(f"Ground state energy: {result.eigenvalue}")
```

### 2. Quantum Approximate Optimization (QAOA)

```python
# Max-cut problem
from qiskit.algorithms import QAOA

qaoa = QAOA(optimizer=optimizer, reps=3)
result = qaoa.compute_minimum_eigenvalue(qubit_op)
print(f"Optimal solution: {result.optimal_point}")
```

### 3. Quantum Machine Learning

```python
# Quantum neural network
import pennylane as qml

@qml.qnode(dev)
def qnn(inputs, weights):
    qml.AngleEmbedding(inputs, wires=range(n_qubits))
    qml.StronglyEntanglingLayers(weights, wires=range(n_qubits))
    return qml.expval(qml.PauliZ(0))
```

---

## Environment Variables

```bash
# IBM Quantum
IBM_QUANTUM_TOKEN=your-token

# Google Quantum
GOOGLE_CLOUD_PROJECT=your-project-id

# Xanadu Cloud
XANADU_API_KEY=your-api-key

# Jupyter
JUPYTER_TOKEN=your-jupyter-token
```

Create `.env` file:
```bash
cp .env.example .env
# Edit with your tokens
```

---

## Performance & Cost

### Simulators (Free)
- **Qiskit Aer**: Up to ~30 qubits
- **Cirq Simulator**: Up to ~20 qubits
- **Strawberry Fields**: Up to ~12 modes

### Real Quantum Hardware

**IBM Quantum:**
- **Free tier**: 10 minutes/month on 5-qubit systems
- **Premium**: $1.60/min on advanced systems

**Google Quantum:**
- By application only
- Research collaborations

**Xanadu:**
- **Free tier**: Limited GBS runs
- **Paid**: $0.10-1.00 per circuit execution

---

## Production Deployment

### API Server Mode

```dockerfile
# Change CMD in Dockerfile
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
```

Create `api.py`:
```python
from fastapi import FastAPI
from qiskit import QuantumCircuit, transpile
from qiskit_aer import Aer

app = FastAPI()

@app.post("/run-circuit")
async def run_circuit(circuit_data: dict):
    # Convert to quantum circuit
    # Run on simulator or hardware
    # Return results
    pass
```

---

## Troubleshooting

### Issue: "No module named 'qiskit'"

**Fix:** Rebuild Docker image
```bash
docker build --no-cache -t quantum-dev .
```

### Issue: IBM Quantum authentication fails

**Fix:** Save credentials correctly
```python
from qiskit_ibm_runtime import QiskitRuntimeService
QiskitRuntimeService.save_account(token="YOUR_TOKEN", overwrite=True)
```

### Issue: Simulation too slow

**Fix:** Reduce qubits or use sparse simulator
```python
# Use statevector instead of qasm
backend = Aer.get_backend('statevector_simulator')
```

---

## Resources

- **Qiskit**: https://qiskit.org/
- **Cirq**: https://quantumai.google/cirq
- **Strawberry Fields**: https://strawberryfields.ai/
- **PennyLane**: https://pennylane.ai/
- **Quantum Computing Report**: https://quantumcomputingreport.com/

---

## Example Projects

### 1. Quantum Chemistry (VQE)
Calculate molecular ground states

### 2. Optimization (QAOA)
Solve combinatorial problems

### 3. Machine Learning (QML)
Quantum-enhanced ML models

### 4. Cryptography
Quantum key distribution (BB84)

### 5. Simulation
Simulate quantum systems

---

**Created:** November 15, 2025  
**Status:** Production-Ready  
**Frameworks:** Qiskit, Cirq, Strawberry Fields, Custom
