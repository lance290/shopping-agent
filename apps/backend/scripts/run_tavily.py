import os
import json
import httpx
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

def perform_search(query: str) -> str:
    print(f"Searching Tavily for: {query}")
    try:
        resp = httpx.post(
            "https://api.tavily.com/search",
            headers={"Content-Type": "application/json"},
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "basic",
                "max_results": 3,
                "include_raw_content": False
            }
        )
        resp.raise_for_status()
        data = resp.json()
        context = []
        for r in data.get("results", []):
            context.append(f"Title: {r.get('title')}\nURL: {r.get('url')}\nSnippet: {r.get('content')}\n")
        return "\n".join(context)
    except Exception as e:
        print(f"Search failed for '{query}': {e}")
        return ""

print(perform_search("Magic Spoon cereal brand products"))
