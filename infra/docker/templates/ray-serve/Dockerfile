# Ray Serve Multi-Model Serving Dockerfile
# For complex ML pipelines with auto-scaling
FROM rayproject/ray:latest-py310

# Set working directory
WORKDIR /app

# Install additional dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Environment variables
ENV RAY_SERVE_PORT=8000
ENV RAY_DASHBOARD_PORT=8265

# Health check (Ray Serve native endpoint)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:${RAY_SERVE_PORT}/-/health || exit 1

# Expose ports
EXPOSE ${RAY_SERVE_PORT} ${RAY_DASHBOARD_PORT}

# Start Ray Serve
CMD ["python", "serve_app.py"]
