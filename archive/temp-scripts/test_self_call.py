import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        # Note the trailing slash if there is one, or /api prefix
        resp = await client.post("http://127.0.0.1:8000/rows/112/search/stream", json={"query": "ice cream"}, headers={"Authorization": "Bearer fake"})
        print(resp.status_code)
        print(resp.text[:500])

asyncio.run(main())
