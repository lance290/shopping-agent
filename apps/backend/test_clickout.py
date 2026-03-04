import asyncio
from unittest.mock import AsyncMock, patch

async def mock_get_current_session(authorization, session):
    return None

async def test_performance():
    from fastapi import Request
    from routes.clickout import clickout_redirect
    import time
    
    # Enable Skimlinks
    import os
    os.environ["SKIMLINKS_PUBLISHER_ID"] = "12345X67890"
    
    mock_req = Request({"type": "http", "client": ["127.0.0.1", 12345], "headers": []})
    
    with patch('routes.clickout.get_current_session', new=mock_get_current_session):
        start = time.time()
        res = await clickout_redirect(
            url="https://www.apple.com/iphone",
            request=mock_req,
            authorization=None,
            session=AsyncMock()
        )
        duration = time.time() - start
        print(f"Clickout took {duration:.3f}s")
        print(f"Final URL: {res.headers.get('location')}")

if __name__ == "__main__":
    asyncio.run(test_performance())
