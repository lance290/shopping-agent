import asyncio
import uuid
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        req = {
            "messages": [
                {"role": "user", "content": "I need a present for my wife"},
                {"role": "assistant", "content": "Would you like it personalized?"},
                {"role": "user", "content": "Yes, personalized"}
            ],
            "activeRowId": None,
            "projectId": None,
            "pendingClarification": {
                "type": "clarification",
                "title": "Anniversary gift",
                "partial_constraints": {}
            }
        }
        headers = {
            "X-Anonymous-Session-Id": str(uuid.uuid4())
        }
        # Note: the dev server must be running on 8000
        async with client.stream("POST", "http://127.0.0.1:8000/api/chat", json=req, headers=headers) as response:
            async for line in response.aiter_lines():
                if line:
                    print(line)

if __name__ == "__main__":
    asyncio.run(main())
