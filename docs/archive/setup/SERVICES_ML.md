# ML/AI Services Setup Guide

Complete guide for setting up ML/AI infrastructure in your project.

---

## Overview

This guide covers:
- **LLM Inference**: vLLM, TGI, Ray Serve
- **Traditional ML Serving**: BentoML, Triton
- **Model Storage**: MLflow, Weights & Biases, DVC
- **Vector Databases**: pgvector, Pinecone, Qdrant
- **GPU Infrastructure**: GCP, AWS, Modal, RunPod

---

## 1. LLM Inference Servers

### vLLM (Recommended for Most Use Cases)

**Best for:** Fast LLM inference with OpenAI-compatible API

**Setup:**
```bash
# Use Docker template
cp -r infra/docker/templates/vllm ./

# Build and run
docker build -t vllm-server vllm/
docker run --gpus all -p 8000:8000 \
  -e MODEL_NAME="meta-llama/Llama-2-7b-chat-hf" \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm-server
```

**Environment Variables:**
```bash
MODEL_NAME=meta-llama/Llama-2-7b-chat-hf
TENSOR_PARALLEL_SIZE=1  # Number of GPUs
GPU_MEMORY_UTILIZATION=0.9
MAX_MODEL_LEN=4096
PORT=8000
```

**Client Usage:**
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="meta-llama/Llama-2-7b-chat-hf",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

**See:** `infra/docker/templates/vllm/README.md` for full documentation

---

### TGI (Text Generation Inference)

**Best for:** HuggingFace ecosystem, production deployments

**Setup:**
```bash
docker run --gpus all -p 8080:80 \
  -v ~/.cache/huggingface:/data \
  ghcr.io/huggingface/text-generation-inference:latest \
  --model-id meta-llama/Llama-2-7b-chat-hf
```

**Client Usage:**
```python
from huggingface_hub import InferenceClient

client = InferenceClient(model="http://localhost:8080")
response = client.text_generation("Hello, how are you?")
```

---

### Ray Serve

**Best for:** Complex multi-model pipelines, custom logic

**Setup:**
```bash
# Use Docker template
cp -r infra/docker/templates/ray-serve ./

# Build and run
docker build -t ray-serve ray-serve/
docker run -p 8000:8000 -p 8265:8265 ray-serve
```

**See:** `infra/docker/templates/ray-serve/serve_app.py` for example

---

## 2. Traditional ML Serving

### BentoML (Recommended)

**Best for:** sklearn, XGBoost, PyTorch, TensorFlow models

**Setup:**
```bash
# Use Docker template
cp -r infra/docker/templates/bentoml ./

# Install BentoML
pip install bentoml

# Save your model
import bentoml
bentoml.sklearn.save_model("my_model", model)

# Build and run
docker build -t bentoml-service bentoml/
docker run -p 3000:3000 bentoml-service
```

**See:** `infra/docker/templates/bentoml/service.py` for example

---

### Triton Inference Server

**Best for:** Maximum performance, NVIDIA GPUs, TensorRT

**Setup:**
```bash
docker run --gpus all -p 8000:8000 -p 8001:8001 -p 8002:8002 \
  -v /path/to/model-repository:/models \
  nvcr.io/nvidia/tritonserver:latest \
  tritonserver --model-repository=/models
```

**Model Repository Structure:**
```
model-repository/
├── my_model/
│   ├── config.pbtxt
│   └── 1/
│       └── model.pt
```

---

## 3. Model Storage & Versioning

### MLflow (Recommended)

**Best for:** Model registry, experiment tracking, lineage

**Setup:**
```bash
# Use Docker template
cp -r infra/docker/templates/mlflow ./

# Build and run
docker build -t mlflow-server mlflow/
docker run -p 5000:5000 \
  -v $(pwd)/mlflow:/mlflow \
  mlflow-server
```

**Environment Variables (Production):**
```bash
MLFLOW_BACKEND_STORE_URI=postgresql://user:pass@host:5432/mlflow
MLFLOW_DEFAULT_ARTIFACT_ROOT=gs://my-bucket/mlflow-artifacts
GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-key.json
```

**Client Usage:**
```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")

# Log experiment
with mlflow.start_run():
    mlflow.log_param("learning_rate", 0.01)
    mlflow.log_metric("accuracy", 0.95)
    mlflow.sklearn.log_model(model, "model")

# Register model
mlflow.register_model("runs:/<run_id>/model", "my_model")

# Load model
model = mlflow.pyfunc.load_model("models:/my_model/production")
```

**See:** `infra/docker/templates/mlflow/README.md` for full documentation

---

### Weights & Biases

**Best for:** Experiment tracking, team collaboration

**Setup:**
```bash
pip install wandb

# Login
wandb login

# Track experiments
import wandb

wandb.init(project="my-project")
wandb.log({"accuracy": 0.95})
wandb.finish()
```

---

### DVC (Data Version Control)

**Best for:** Data versioning, large datasets

**Setup:**
```bash
pip install dvc[gs]  # or [s3], [azure]

# Initialize
dvc init

# Track data
dvc add data/train.csv
git add data/train.csv.dvc .gitignore
git commit -m "Add training data"

# Configure remote storage
dvc remote add -d storage gs://my-bucket/dvc-storage
dvc push
```

---

## 4. Vector Databases

### pgvector (Simplest - PostgreSQL Extension)

**Best for:** Existing PostgreSQL users, simplicity

**Setup:**
```bash
# Add to docker-compose.yml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
```

**Usage:**
```python
import psycopg2
from pgvector.psycopg2 import register_vector

conn = psycopg2.connect(database="mydb")
register_vector(conn)

# Create table
conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
conn.execute('CREATE TABLE embeddings (id serial, embedding vector(1536))')

# Insert embedding
conn.execute('INSERT INTO embeddings (embedding) VALUES (%s)', (embedding,))

# Similarity search
conn.execute('SELECT * FROM embeddings ORDER BY embedding <-> %s LIMIT 5', (query_embedding,))
```

---

### Pinecone (Managed, Serverless)

**Best for:** Serverless, no infrastructure management

**Setup:**
```bash
pip install pinecone-client

# Initialize
import pinecone

pinecone.init(api_key="your-key", environment="us-west1-gcp")
index = pinecone.Index("my-index")

# Upsert vectors
index.upsert(vectors=[("id1", [0.1, 0.2, ...], {"metadata": "value"})])

# Query
results = index.query(vector=[0.1, 0.2, ...], top_k=5)
```

---

### Qdrant (Open Source, High Performance)

**Best for:** Self-hosted, high performance, Rust-based

**Setup:**
```bash
docker run -p 6333:6333 qdrant/qdrant

# Python client
pip install qdrant-client

from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)
client.create_collection(
    collection_name="my_collection",
    vectors_config={"size": 1536, "distance": "Cosine"}
)
```

---

## 5. GPU Infrastructure

### GCP Vertex AI

**Best for:** Managed ML platform, integrated with GCP

**Setup:**
```python
from google.cloud import aiplatform

aiplatform.init(project="my-project", location="us-central1")

# Deploy model
endpoint = aiplatform.Endpoint.create(display_name="my-endpoint")
model = aiplatform.Model.upload(
    display_name="my-model",
    artifact_uri="gs://my-bucket/model",
    serving_container_image_uri="gcr.io/my-project/serving-image"
)
model.deploy(endpoint=endpoint, machine_type="n1-standard-4", accelerator_type="NVIDIA_TESLA_T4")
```

---

### AWS SageMaker

**Best for:** AWS ecosystem, managed ML platform

**Setup:**
```python
import sagemaker

role = sagemaker.get_execution_role()
predictor = sagemaker.deploy(
    initial_instance_count=1,
    instance_type="ml.g4dn.xlarge",
    model_data="s3://my-bucket/model.tar.gz"
)
```

---

### Modal (Serverless GPU)

**Best for:** Pay-per-second GPU, developer-friendly

**Setup:**
```python
import modal

stub = modal.Stub("my-app")

@stub.function(gpu="A100")
def inference(input_data):
    # Your inference code
    return predictions

# Deploy
stub.deploy("my-app")
```

---

### RunPod (Cost-Effective)

**Best for:** Spot instances, lower cost

**Setup:**
```bash
# Deploy via RunPod dashboard or API
# Use Docker image with your model
```

---

## 6. Complete ML Stack Example

### RAG Application with LLM + Vector DB

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  # Vector database
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # LLM inference
  vllm:
    build: ./infra/docker/templates/vllm
    environment:
      MODEL_NAME: "meta-llama/Llama-2-7b-chat-hf"
    ports:
      - "8000:8000"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # Model registry
  mlflow:
    build: ./infra/docker/templates/mlflow
    environment:
      MLFLOW_BACKEND_STORE_URI: "postgresql://postgres:password@postgres:5432/mlflow"
    ports:
      - "5000:5000"
    depends_on:
      - postgres

volumes:
  postgres_data:
```

---

## 7. Security Best Practices

### Model Security
- **Rate limiting**: Prevent abuse and control costs
- **Input validation**: Sanitize prompts and inputs
- **Output filtering**: Detect and filter toxic/harmful outputs
- **Model watermarking**: Protect against model extraction

### Data Privacy
- **PII detection**: Scan prompts and outputs for sensitive data
- **Data anonymization**: Remove PII from training data
- **Audit logging**: Track all model access and predictions
- **Encryption**: Encrypt models and data at rest

### Compliance
- **Model versioning**: Track which model version was used
- **Explainability**: Implement SHAP/LIME for GDPR/HIPAA
- **Bias testing**: Regular fairness audits
- **Right-to-explanation**: Document model decisions

---

## 8. Monitoring & Observability

### Metrics to Track
- **Inference latency**: P50, P95, P99
- **Throughput**: Requests per second
- **GPU utilization**: Memory and compute usage
- **Error rates**: Failed predictions
- **Model drift**: Input/output distribution changes
- **Cost**: GPU hours, API calls

### Tools
- **Prometheus + Grafana**: Metrics and dashboards
- **Weights & Biases**: Experiment tracking
- **LangSmith**: LLM tracing and debugging
- **Arize AI**: ML observability and drift detection

---

## 9. Cost Optimization

### Tips
1. **Use quantization**: AWQ/GPTQ for 2-4x speedup
2. **Batch requests**: Increase throughput
3. **Auto-scaling**: Scale down during low traffic
4. **Spot instances**: Use RunPod or AWS spot for training
5. **Cache responses**: Reduce redundant inference
6. **Model selection**: Use smallest model that meets requirements

### Cost Comparison (per hour)
- **GCP T4**: ~$0.35/hr
- **GCP V100**: ~$2.48/hr
- **GCP A100**: ~$3.67/hr
- **AWS P3**: ~$3.06/hr
- **Modal A100**: ~$1.10/hr (pay-per-second)
- **RunPod A100**: ~$0.79/hr (spot)

---

## 10. Troubleshooting

### Out of Memory
- Reduce `GPU_MEMORY_UTILIZATION`
- Use quantized models (AWQ/GPTQ)
- Reduce batch size or max sequence length
- Use tensor parallelism across multiple GPUs

### Slow Inference
- Check GPU utilization (`nvidia-smi`)
- Enable continuous batching (vLLM default)
- Use faster model architecture
- Optimize model with TensorRT

### Model Download Issues
- Mount HuggingFace cache volume
- Set `HF_TOKEN` for gated models
- Use local model files
- Check network connectivity

---

## Additional Resources

- **vLLM Docs**: https://docs.vllm.ai
- **BentoML Docs**: https://docs.bentoml.com
- **MLflow Docs**: https://mlflow.org/docs
- **Ray Serve Docs**: https://docs.ray.io/en/latest/serve
- **Triton Docs**: https://docs.nvidia.com/deeplearning/triton-inference-server
