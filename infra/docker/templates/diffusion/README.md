# Diffusion Models: Image & Text Generation

Production-ready template for **two types** of diffusion models:
1. **Image Generation** - Stable Diffusion, SDXL, ControlNet
2. **Text Generation** - Inception Mercury dLLM (diffusion-based LLM)

---

## What's Included

### Image Diffusion
- **Stable Diffusion 1.5** - Fast, good quality
- **Stable Diffusion 2.1** - Better quality  
- **SDXL** - Best quality (slower)
- **ControlNet** - Guided generation (coming soon)

### Text Diffusion (Mercury dLLM)
- **Inception Mercury** - 10x faster than GPT-4
- Parallel token generation (not autoregressive)
- Excellent for structured output
- OpenAI-compatible API

---

## Quick Start

```bash
# Build
docker build -t diffusion-api .

# Run with GPU
docker run --gpus all -p 8080:8080 \
  -e HUGGINGFACE_TOKEN=hf_... \
  -e INCEPTION_API_KEY=sk-... \
  diffusion-api

# Test
curl -X POST http://localhost:8080/generate/image \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A beautiful sunset", "model": "sd15"}'
```

---

## API Endpoints

### Image Generation
```bash
POST /generate/image
{
  "prompt": "A serene landscape with mountains",
  "negative_prompt": "blurry, low quality",
  "model": "sd15",  # or "sd21", "sdxl"
  "num_inference_steps": 50,
  "guidance_scale": 7.5,
  "width": 512,
  "height": 512
}
```

### Text Generation (Mercury)
```bash
POST /generate/text
{
  "prompt": "Explain quantum computing in 100 words",
  "model": "mercury",
  "max_tokens": 1000,
  "temperature": 0.7
}
```

---

## Mercury dLLM vs Traditional LLMs

| Feature | Mercury (dLLM) | GPT-4 (Autoregressive) |
|---------|----------------|------------------------|
| **Generation** | Parallel tokens | Sequential tokens |
| **Speed** | 10x faster | Baseline |
| **Structured Output** | Excellent | Good |
| **GPU Efficiency** | High | Medium |
| **Use Cases** | APIs, batch jobs | Interactive chat |

**When to use Mercury:**
- API backends (speed matters)
- Structured data extraction
- Batch processing
- Cost optimization

**When to use GPT-4:**
- Interactive chat
- Creative writing
- Complex reasoning

---

## Configuration

### Get API Keys

**HuggingFace** (for Stable Diffusion):
```bash
# Visit https://huggingface.co/settings/tokens
export HUGGINGFACE_TOKEN=hf_...
```

**Inception Labs** (for Mercury):
```bash
# Visit https://www.inceptionlabs.ai/
export INCEPTION_API_KEY=sk-inception...
```

---

## GPU Requirements

### Image Generation
- **SD 1.5**: 4GB VRAM (T4, RTX 2060)
- **SD 2.1**: 6GB VRAM (RTX 3060)
- **SDXL**: 10GB+ VRAM (A10G, RTX 3080)

### Text Generation (Mercury)
- API-based, no local GPU needed
- Runs on Inception's infrastructure

---

## Cost Optimization

### Image Generation (Self-Hosted)
- Use SD 1.5 for speed (2-3s per image)
- Use SDXL for quality (10-15s per image)
- Batch generations for efficiency

### Text Generation (Mercury API)
- **Pricing**: ~$0.50 per 1M tokens
- 10x cheaper than GPT-4 ($30/1M tokens)
- No infrastructure costs

---

## Production Deployment

### Deploy to Modal (GPU serverless)
```bash
modal deploy diffusion_modal.py
```

### Deploy to GCP Cloud Run (CPU/small GPU)
```bash
gcloud run deploy diffusion-api \
  --source . \
  --gpu 1 \
  --gpu-type nvidia-tesla-t4
```

---

## Examples

See `examples/` directory:
- `stable_diffusion.py` - Image generation
- `mercury_dllm.py` - Text generation via diffusion

---

## Resources

- **Stable Diffusion**: https://github.com/Stability-AI/stablediffusion
- **Diffusers**: https://huggingface.co/docs/diffusers
- **Inception Mercury**: https://www.inceptionlabs.ai/
- **Mercury Paper**: https://arxiv.org/abs/[coming-soon]

---

**Created:** November 15, 2025  
**Status:** Production-Ready  
**Models:** SD, SDXL, Mercury dLLM
