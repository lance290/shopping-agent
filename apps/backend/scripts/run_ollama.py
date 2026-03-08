import httpx
import json
import sys
import asyncio

async def test():
    try:
        prompt = """You are an expert B2B lead generator and data enricher with web search capabilities.
Research the CPG brand: "Abbot's Butcher".

Your goal is to find their company details and specific key personnel.
Find the names, titles, and (if available) emails or LinkedIn URLs of people currently working at Abbot's Butcher with any of these titles (or similar): VP of Growth, Director of Shopper Marketing.

Output ONLY valid JSON. Do not include markdown fences (```json ... ```). Do not include your thinking or any extra explanations. 

Required JSON Structure:
{
    "website": "https://...",
    "tagline": "Short 1-sentence tagline",
    "description": "Detailed description of the company and their main products.",
    "seo_summary": "High-density 2-3 sentence summary of their core offerings.",
    "services_list": ["Product 1", "Product 2"],
    "contacts": [
        {
            "name": "Jane Doe",
            "title": "VP of Growth",
            "email_or_linkedin": "jane@example.com or https://linkedin.com/in/..."
        }
    ]
}
"""
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "gpt-oss:20b",
                    "messages": [{"role": "user", "content": prompt}],
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 1500}
                }
            )
            print("Status:", resp.status_code)
            data = resp.json()
            print("Response:", data)
            msg = data.get("message", {})
            print("Content:", msg.get("content"))
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(test())
