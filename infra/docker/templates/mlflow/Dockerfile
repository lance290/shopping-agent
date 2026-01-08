# MLflow Model Registry and Tracking Server Dockerfile
# Central model storage and versioning
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install MLflow and dependencies
RUN pip install --no-cache-dir \
    mlflow>=2.9.0 \
    psycopg2-binary>=2.9.0 \
    boto3>=1.28.0 \
    google-cloud-storage>=2.10.0

# Create non-root user for security
RUN useradd -m -u 1000 mlflow && \
    mkdir -p /mlflow/artifacts && \
    chown -R mlflow:mlflow /mlflow
USER mlflow

# Environment variables
ENV MLFLOW_PORT=5000
ENV MLFLOW_HOST=0.0.0.0
ENV MLFLOW_BACKEND_STORE_URI=sqlite:///mlflow/mlflow.db
ENV MLFLOW_DEFAULT_ARTIFACT_ROOT=/mlflow/artifacts

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${MLFLOW_PORT}/health || exit 1

# Expose port
EXPOSE ${MLFLOW_PORT}

# Start MLflow server
CMD mlflow server \
    --host ${MLFLOW_HOST} \
    --port ${MLFLOW_PORT} \
    --backend-store-uri ${MLFLOW_BACKEND_STORE_URI} \
    --default-artifact-root ${MLFLOW_DEFAULT_ARTIFACT_ROOT}
