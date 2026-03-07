import os
import json
import httpx
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

def perform_search(query: str) -> str:
    print(f"Searching SerpAPI for: {query}")
    try:
        resp = httpx.get(
            "https://serpapi.com/search",
            params={
                "api_key": SERPAPI_API_KEY,
                "q": query,
                "engine": "google",
                "num": 3
            },
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        context = []
        for r in data.get("organic_results", []):
            context.append(f"Title: {r.get('title')}\nURL: {r.get('link')}\nSnippet: {r.get('snippet')}\n")
        return "\n".join(context)
    except Exception as e:
        print(f"Search failed for '{query}': {e}")
        return ""

print(perform_search("Magic Spoon cereal brand products"))
print(perform_search("Magic Spoon linkedin VP Growth"))
