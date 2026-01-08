# Diffusion Models: Image Generation & Text Generation (dLLM)
# Supports: Stable Diffusion, ControlNet, SDXL, Inception Mercury
FROM python:3.11-slim

# Install system dependencies for image processing
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1001 diffusion

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download model cache directory (optional, uncomment for pre-cached models)
# RUN mkdir -p /app/models

# Copy application code
COPY --chown=diffusion:diffusion . .

# Switch to non-root user
USER diffusion

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV HF_HOME=/app/models
ENV TRANSFORMERS_CACHE=/app/models

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Default: Start FastAPI server
# For Jupyter, override: CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8080"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
