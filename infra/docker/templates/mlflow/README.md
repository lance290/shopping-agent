# MLflow Model Registry & Tracking Server

Central model storage, versioning, and experiment tracking.

## Features

- **Model Registry**: Version and manage ML models
- **Experiment Tracking**: Log parameters, metrics, artifacts
- **Model Lineage**: Track which experiment produced which model
- **Multi-framework**: Works with any ML framework
- **REST API**: Programmatic access to models and experiments

## Quick Start

### Local Development (SQLite)

```bash
docker build -t mlflow-server .
docker run -p 5000:5000 \
  -v $(pwd)/mlflow:/mlflow \
  mlflow-server
```

Access UI at http://localhost:5000

### Production (PostgreSQL + S3)

```bash
docker run -p 5000:5000 \
  -e MLFLOW_BACKEND_STORE_URI="postgresql://user:pass@host:5432/mlflow" \
  -e MLFLOW_DEFAULT_ARTIFACT_ROOT="s3://my-bucket/mlflow-artifacts" \
  -e AWS_ACCESS_KEY_ID="your-key" \
  -e AWS_SECRET_ACCESS_KEY="your-secret" \
  mlflow-server
```

### Production (PostgreSQL + GCS)

```bash
docker run -p 5000:5000 \
  -e MLFLOW_BACKEND_STORE_URI="postgresql://user:pass@host:5432/mlflow" \
  -e MLFLOW_DEFAULT_ARTIFACT_ROOT="gs://my-bucket/mlflow-artifacts" \
  -e GOOGLE_APPLICATION_CREDENTIALS="/app/gcp-key.json" \
  -v /path/to/gcp-key.json:/app/gcp-key.json \
  mlflow-server
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MLFLOW_PORT` | `5000` | Server port |
| `MLFLOW_HOST` | `0.0.0.0` | Server host |
| `MLFLOW_BACKEND_STORE_URI` | `sqlite:///mlflow/mlflow.db` | Database connection string |
| `MLFLOW_DEFAULT_ARTIFACT_ROOT` | `/mlflow/artifacts` | Artifact storage location |

## Client Usage

### Python Client

```python
import mlflow

# Set tracking URI
mlflow.set_tracking_uri("http://localhost:5000")

# Log experiment
with mlflow.start_run():
    mlflow.log_param("learning_rate", 0.01)
    mlflow.log_metric("accuracy", 0.95)
    mlflow.log_artifact("model.pkl")

# Register model
mlflow.register_model(
    model_uri="runs:/<run_id>/model",
    name="my_model"
)
```

### Model Deployment

```python
import mlflow

# Load model from registry
model = mlflow.pyfunc.load_model("models:/my_model/production")

# Make predictions
predictions = model.predict(data)
```

## Model Registry Workflow

1. **Train & Log**: Train model, log to MLflow
2. **Register**: Register model in registry
3. **Stage**: Promote through stages (Staging → Production)
4. **Deploy**: Deploy production model
5. **Monitor**: Track model performance

## Stages

- **None**: Initial registration
- **Staging**: Testing/validation
- **Production**: Live deployment
- **Archived**: Deprecated models

## Backend Store Options

### SQLite (Development)
```
sqlite:///mlflow/mlflow.db
```

### PostgreSQL (Production)
```
postgresql://user:password@host:5432/mlflow
```

### MySQL (Production)
```
mysql://user:password@host:3306/mlflow
```

## Artifact Store Options

### Local Filesystem
```
/mlflow/artifacts
```

### AWS S3
```
s3://bucket-name/path
```

### Google Cloud Storage
```
gs://bucket-name/path
```

### Azure Blob Storage
```
wasbs://container@account.blob.core.windows.net/path
```

## Security Considerations

- **Authentication**: Use reverse proxy (nginx) with basic auth
- **Authorization**: Implement RBAC via proxy
- **Encryption**: Use TLS for production
- **Secrets**: Store credentials in secret manager
- **Network**: Restrict access to internal network

## GCP Deployment

```bash
# Build and push to GCR
docker build -t gcr.io/YOUR-PROJECT/mlflow-server .
docker push gcr.io/YOUR-PROJECT/mlflow-server

# Deploy to Cloud Run
gcloud run deploy mlflow-server \
  --image gcr.io/YOUR-PROJECT/mlflow-server \
  --platform managed \
  --region us-central1 \
  --set-env-vars MLFLOW_BACKEND_STORE_URI="postgresql://..." \
  --set-env-vars MLFLOW_DEFAULT_ARTIFACT_ROOT="gs://..."
```

## Railway Deployment

```bash
# Railway automatically detects Dockerfile
railway up

# Set environment variables in Railway dashboard:
# - MLFLOW_BACKEND_STORE_URI (use Railway PostgreSQL)
# - MLFLOW_DEFAULT_ARTIFACT_ROOT (use GCS or S3)
```

## Integrations

### Weights & Biases
```python
import wandb
import mlflow

# Log to both
with mlflow.start_run():
    wandb.init(project="my-project")
    # Training code...
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlflow-server
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: mlflow
        image: mlflow-server:latest
        env:
        - name: MLFLOW_BACKEND_STORE_URI
          value: "postgresql://..."
```

## Troubleshooting

**Database Connection Failed:**
- Check `MLFLOW_BACKEND_STORE_URI` format
- Verify database is accessible
- Check credentials

**Artifact Upload Failed:**
- Verify cloud credentials (AWS/GCP)
- Check bucket permissions
- Ensure bucket exists

**UI Not Loading:**
- Check port mapping
- Verify firewall rules
- Check logs: `docker logs <container>`
