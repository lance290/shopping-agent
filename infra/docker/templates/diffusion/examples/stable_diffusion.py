"""
Stable Diffusion Image Generation
Supports SD 1.5, SD 2.1, SDXL, and ControlNet
"""
from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline
import torch
import base64
from io import BytesIO
import random

# Cache pipelines to avoid reloading
_pipelines = {}

async def generate_image_sd(
    prompt: str,
    negative_prompt: str = None,
    model: str = "sd15",
    steps: int = 50,
    guidance: float = 7.5,
    width: int = 512,
    height: int = 512,
    seed: int = None
):
    """Generate image using Stable Diffusion"""
    
    # Set seed for reproducibility
    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    generator = torch.Generator().manual_seed(seed)
    
    # Load appropriate model
    if model not in _pipelines:
        print(f"Loading {model} model...")
        if model == "sdxl":
            pipeline = StableDiffusionXLPipeline.from_pretrained(
                "stabilityai/stable-diffusion-xl-base-1.0",
                torch_dtype=torch.float16,
                use_safetensors=True
            )
        elif model == "sd21":
            pipeline = StableDiffusionPipeline.from_pretrained(
                "stabilityai/stable-diffusion-2-1",
                torch_dtype=torch.float16
            )
        else:  # sd15
            pipeline = StableDiffusionPipeline.from_pretrained(
                "runwayml/stable-diffusion-v1-5",
                torch_dtype=torch.float16
            )
        
        # Move to GPU if available
        if torch.cuda.is_available():
            pipeline = pipeline.to("cuda")
        
        _pipelines[model] = pipeline
    
    pipeline = _pipelines[model]
    
    # Generate image
    image = pipeline(
        prompt=prompt,
        negative_prompt=negative_prompt,
        num_inference_steps=steps,
        guidance_scale=guidance,
        width=width,
        height=height,
        generator=generator
    ).images[0]
    
    # Convert to base64
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{img_base64}", seed

if __name__ == "__main__":
    # Test image generation
    import asyncio
    
    async def test():
        prompt = "A serene landscape with mountains and a lake at sunset, highly detailed"
        image_data, seed = await generate_image_sd(prompt, model="sd15")
        print(f"Generated image with seed: {seed}")
        print(f"Image data length: {len(image_data)}")
    
    asyncio.run(test())
