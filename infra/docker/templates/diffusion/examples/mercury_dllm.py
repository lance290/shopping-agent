"""
Inception Mercury dLLM (Diffusion-based Language Model)
10x faster than autoregressive LLMs via parallel token generation
"""
from openai import AsyncOpenAI
import os

# Mercury uses OpenAI-compatible API
_client = None

def get_mercury_client(api_key: str):
    """Get or create Mercury API client"""
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.inceptionlabs.ai/v1"  # Mercury endpoint
        )
    return _client

async def generate_text_mercury(
    prompt: str,
    max_tokens: int = 1000,
    temperature: float = 0.7,
    api_key: str = None
):
    """
    Generate text using Inception Mercury dLLM
    
    Mercury uses diffusion for text generation instead of autoregressive:
    - Generates tokens in parallel (not one-at-a-time)
    - 10x faster than GPT-4
    - More efficient GPU utilization
    - Better for structured output
    """
    
    if api_key is None:
        api_key = os.getenv("INCEPTION_API_KEY")
    
    if not api_key:
        raise ValueError("INCEPTION_API_KEY required. Get it from https://www.inceptionlabs.ai/")
    
    client = get_mercury_client(api_key)
    
    # Call Mercury API (OpenAI-compatible)
    response = await client.chat.completions.create(
        model="mercury",  # or "mercury-pro" for larger model
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens,
        temperature=temperature
    )
    
    text = response.choices[0].message.content
    tokens = response.usage.total_tokens
    
    return text, tokens

# Example: Structured output (Mercury excels at this)
async def generate_json_mercury(
    prompt: str,
    schema: dict,
    api_key: str = None
):
    """Generate structured JSON output"""
    
    structured_prompt = f"""Generate JSON following this schema:
{schema}

User request: {prompt}

Output only valid JSON, no explanation:"""
    
    text, tokens = await generate_text_mercury(
        prompt=structured_prompt,
        max_tokens=1000,
        temperature=0.3,  # Lower temperature for structured output
        api_key=api_key
    )
    
    return text, tokens

if __name__ == "__main__":
    # Test Mercury generation
    import asyncio
    
    async def test():
        # Example 1: Simple text generation
        prompt = "Explain how diffusion models work in 100 words"
        text, tokens = await generate_text_mercury(prompt)
        print("="*50)
        print("Mercury dLLM Output:")
        print("="*50)
        print(text)
        print(f"\nTokens used: {tokens}")
        
        # Example 2: Structured output (Mercury's strength)
        schema = {
            "name": "string",
            "age": "number",
            "hobbies": ["string"]
        }
        json_text, _ = await generate_json_mercury(
            "Create a person profile for a software engineer",
            schema
        )
        print("\n" + "="*50)
        print("Structured Output:")
        print("="*50)
        print(json_text)
    
    asyncio.run(test())
