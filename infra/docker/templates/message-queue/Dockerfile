# Message Queue Consumer/Producer Service
# Supports: Kafka, RabbitMQ, Redis Streams
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1001 mqworker

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=mqworker:mqworker . .

# Switch to non-root user
USER mqworker

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV QUEUE_TYPE=rabbitmq

# Expose port for health API
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Default: Start worker (can override for API mode)
CMD ["python", "worker.py"]
