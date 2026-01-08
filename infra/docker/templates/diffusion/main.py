"""
Diffusion Models API Server
Supports: Image generation (Stable Diffusion) and Text generation (Inception Mercury dLLM)
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
import os

app = FastAPI(
    title="Diffusion API",
    description="Image & Text generation via diffusion models",
    version="1.0.0"
)

# Request/Response models
class ImageGenerationRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    model: Literal["sd15", "sd21", "sdxl", "controlnet"] = "sd15"
    num_inference_steps: int = 50
    guidance_scale: float = 7.5
    width: int = 512
    height: int = 512
    seed: Optional[int] = None

class TextGenerationRequest(BaseModel):
    prompt: str
    model: Literal["mercury"] = "mercury"
    max_tokens: int = 1000
    temperature: float = 0.7

class ImageGenerationResponse(BaseModel):
    image_url: str  # Base64 or URL
    seed: int
    model: str

class TextGenerationResponse(BaseModel):
    text: str
    model: str
    tokens_used: int

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Diffusion API",
        "version": "1.0.0",
        "models": {
            "image": ["sd15", "sd21", "sdxl", "controlnet"],
            "text": ["mercury"]
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/generate/image", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest):
    """
    Generate image using Stable Diffusion
    
    Models:
    - sd15: Stable Diffusion 1.5 (fast, good quality)
    - sd21: Stable Diffusion 2.1 (better quality)
    - sdxl: Stable Diffusion XL (best quality, slower)
    - controlnet: ControlNet (guided generation)
    """
    try:
        # Import here to avoid loading if not used
        from examples.stable_diffusion import generate_image_sd
        
        # Validate API key if using HuggingFace models
        hf_token = os.getenv("HUGGINGFACE_TOKEN")
        if not hf_token:
            raise HTTPException(
                status_code=500,
                detail="HUGGINGFACE_TOKEN not configured"
            )
        
        # Generate image
        image_data, seed = await generate_image_sd(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            model=request.model,
            steps=request.num_inference_steps,
            guidance=request.guidance_scale,
            width=request.width,
            height=request.height,
            seed=request.seed
        )
        
        return ImageGenerationResponse(
            image_url=image_data,  # Base64 encoded
            seed=seed,
            model=request.model
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate/text", response_model=TextGenerationResponse)
async def generate_text(request: TextGenerationRequest):
    """
    Generate text using Inception Mercury dLLM
    
    Mercury is a diffusion-based LLM that generates tokens in parallel
    instead of autoregressive (one-at-a-time) generation.
    
    Benefits:
    - 10x faster than GPT-4
    - More efficient GPU utilization
    - Better for structured output
    """
    try:
        # Mercury requires API key
        mercury_api_key = os.getenv("INCEPTION_API_KEY")
        if not mercury_api_key:
            raise HTTPException(
                status_code=500,
                detail="INCEPTION_API_KEY not configured. Get it from https://www.inceptionlabs.ai/"
            )
        
        # Import here to avoid loading if not used
        from examples.mercury_dllm import generate_text_mercury
        
        # Generate text
        text, tokens = await generate_text_mercury(
            prompt=request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            api_key=mercury_api_key
        )
        
        return TextGenerationResponse(
            text=text,
            model="mercury",
            tokens_used=tokens
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
