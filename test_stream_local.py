import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        # Check against dev URL to see if external host answers correctly
        # The frontend calls /api/pop/chat, and Pop chat makes self-call to /rows/id/search/stream
        # Let's inspect the dev server config to find where the backend is hosted
        resp = await client.post("https://dev.popsavings.com/api/rows/112/search/stream", json={"query": "ice cream"})
        print(resp.status_code)
        
        # Test frontend pop route
        resp_pop = await client.post("https://dev.popsavings.com/api/pop/chat", json={
            "action": "create_row", 
            "title": "Milk", 
            "project_id": 1
        })
        print(resp_pop.status_code)

asyncio.run(main())
