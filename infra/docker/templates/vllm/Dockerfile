# vLLM LLM Inference Server Dockerfile
# Optimized for GPU inference with OpenAI-compatible API
#
# PRODUCTION NOTES:
# 1. Pin image tag instead of :latest (e.g., vllm/vllm-openai:v0.2.7)
# 2. For gated models, set HF_TOKEN environment variable
# 3. Mount HuggingFace cache: -v ~/.cache/huggingface:/root/.cache/huggingface
# 4. For production, consider adding non-root user (vLLM base runs as root)
FROM vllm/vllm-openai:latest

# Set working directory
WORKDIR /app

# Environment variables for vLLM configuration
# Default model: facebook/opt-125m (small, public, no auth required)
# For production, change to your model: meta-llama/Llama-2-7b-chat-hf, etc.
ENV MODEL_NAME="facebook/opt-125m"
ENV TENSOR_PARALLEL_SIZE=1
ENV GPU_MEMORY_UTILIZATION=0.9
ENV MAX_MODEL_LEN=4096
ENV PORT=8000

# Optional: Set HuggingFace token for gated models
# ENV HF_TOKEN="your-huggingface-token"

# Health check for monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose API port
EXPOSE ${PORT}

# Start vLLM server with OpenAI-compatible API
# Override MODEL_NAME at runtime: docker run -e MODEL_NAME="your-model" ...
CMD ["sh", "-c", "python -m vllm.entrypoints.openai.api_server \
  --model ${MODEL_NAME} \
  --tensor-parallel-size ${TENSOR_PARALLEL_SIZE} \
  --gpu-memory-utilization ${GPU_MEMORY_UTILIZATION} \
  --max-model-len ${MAX_MODEL_LEN} \
  --port ${PORT} \
  --host 0.0.0.0"]
