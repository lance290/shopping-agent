# BentoML Model Serving Dockerfile
# Production-ready ML model serving for traditional ML models
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install BentoML and common ML frameworks
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 bentoml && chown -R bentoml:bentoml /app
USER bentoml

# Environment variables
ENV BENTOML_PORT=3000
ENV BENTOML_HOST=0.0.0.0

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${BENTOML_PORT}/healthz || exit 1

# Expose port
EXPOSE ${BENTOML_PORT}

# Start BentoML service
# Use environment variables for host and port configuration
CMD ["sh", "-c", "bentoml serve service:svc --host ${BENTOML_HOST} --port ${BENTOML_PORT}"]
