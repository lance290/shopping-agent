import os
import json
import httpx
import asyncio

async def test():
    key = os.getenv("RAINFOREST_API_KEY")
    if not key:
        print("No API key")
        return
    params = {
        "api_key": key,
        "type": "search",
        "amazon_domain": "amazon.com",
        "search_term": "laptop",
    }
    async with httpx.AsyncClient() as client:
        res = await client.get("https://api.rainforestapi.com/request", params=params)
        data = res.json()
        with open("scratch_rainforest.json", "w") as f:
            json.dump(data.get("search_results", [])[:2], f, indent=2)
        print("Done")

asyncio.run(test())
