# vLLM LLM Inference Server

Fast and efficient LLM inference with OpenAI-compatible API.

## Features

- **24x faster** than vanilla HuggingFace Transformers
- **PagedAttention** for efficient memory management
- **OpenAI-compatible API** (drop-in replacement)
- **Continuous batching** for high throughput
- **Multi-GPU support** via tensor parallelism

## Quick Start

### Local Development (CPU - for testing only)

```bash
docker build -t vllm-server .
docker run -p 8000:8000 \
  -e MODEL_NAME="facebook/opt-125m" \
  vllm-server
```

### Production (GPU)

```bash
docker build -t vllm-server .
docker run --gpus all -p 8000:8000 \
  -e MODEL_NAME="meta-llama/Llama-2-7b-chat-hf" \
  -e TENSOR_PARALLEL_SIZE=1 \
  -e GPU_MEMORY_UTILIZATION=0.9 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm-server
```

### Multi-GPU (Tensor Parallelism)

```bash
docker run --gpus all -p 8000:8000 \
  -e MODEL_NAME="meta-llama/Llama-2-70b-chat-hf" \
  -e TENSOR_PARALLEL_SIZE=4 \
  -e GPU_MEMORY_UTILIZATION=0.9 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm-server
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_NAME` | `meta-llama/Llama-2-7b-chat-hf` | HuggingFace model ID |
| `TENSOR_PARALLEL_SIZE` | `1` | Number of GPUs for tensor parallelism |
| `GPU_MEMORY_UTILIZATION` | `0.9` | GPU memory utilization (0.0-1.0) |
| `MAX_MODEL_LEN` | `4096` | Maximum sequence length |
| `PORT` | `8000` | API server port |

## API Usage

### OpenAI-Compatible Endpoint

```python
from openai import OpenAI

# Point to your vLLM server
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"  # vLLM doesn't require API key
)

response = client.chat.completions.create(
    model="meta-llama/Llama-2-7b-chat-hf",
    messages=[
        {"role": "user", "content": "Hello, how are you?"}
    ]
)

print(response.choices[0].message.content)
```

### Direct HTTP Request

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-2-7b-chat-hf",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

## Supported Models

- Llama 2, Llama 3
- Mistral, Mixtral
- Qwen, Qwen2
- Yi, DeepSeek
- GPT-2, GPT-J, GPT-NeoX
- OPT, BLOOM
- And many more...

See [vLLM supported models](https://docs.vllm.ai/en/latest/models/supported_models.html)

## Performance Tips

1. **GPU Memory**: Set `GPU_MEMORY_UTILIZATION=0.9` for maximum throughput
2. **Tensor Parallelism**: Use multiple GPUs for large models (70B+)
3. **Quantization**: Use AWQ or GPTQ quantized models for faster inference
4. **Batch Size**: vLLM automatically batches requests for optimal throughput

## Security Considerations

- **Rate Limiting**: Add nginx/API gateway for production
- **Authentication**: Use API gateway for auth (vLLM has no built-in auth)
- **Input Validation**: Sanitize prompts to prevent injection attacks
- **Output Filtering**: Filter toxic/harmful outputs
- **Monitoring**: Track inference costs and usage patterns

## GCP Deployment

```bash
# Build and push to GCR
docker build -t gcr.io/YOUR-PROJECT/vllm-server .
docker push gcr.io/YOUR-PROJECT/vllm-server

# Deploy to Cloud Run (GPU support coming soon)
# Or use GKE with GPU nodes
```

## Railway Deployment

```bash
# Railway automatically detects Dockerfile
railway up

# Set environment variables in Railway dashboard
```

## Troubleshooting

**Out of Memory:**
- Reduce `GPU_MEMORY_UTILIZATION`
- Use quantized model (AWQ/GPTQ)
- Reduce `MAX_MODEL_LEN`

**Slow Inference:**
- Check GPU utilization (`nvidia-smi`)
- Ensure tensor parallelism matches GPU count
- Use smaller model or quantization

**Model Download Fails:**
- Mount HuggingFace cache: `-v ~/.cache/huggingface:/root/.cache/huggingface`
- Set `HF_TOKEN` for gated models
