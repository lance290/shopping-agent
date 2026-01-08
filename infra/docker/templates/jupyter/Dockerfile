# JupyterLab Notebook Server
# Designed for local dev / GPU containers; defaults to no auth (set your own tokens in production)
FROM python:3.11-slim

WORKDIR /workspace

# Install system deps for common data/ML packages and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m -u 1000 jovyan && chown -R jovyan:jovyan /workspace
USER jovyan

# Environment
ENV JUPYTER_PORT=8888
ENV JUPYTERLAB_DIR=/workspace

# Expose port
EXPOSE 8888

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:${JUPYTER_PORT}/api/status || exit 1

# Start JupyterLab (no token/password by default; override for production)
CMD ["sh", "-c", "jupyter lab --ip=0.0.0.0 --port ${JUPYTER_PORT} --no-browser --NotebookApp.token='' --NotebookApp.password='' --NotebookApp.allow_origin='*' --NotebookApp.disable_check_xsrf=False --NotebookApp.allow_remote_access=True --notebook-dir=${JUPYTERLAB_DIR}"]
