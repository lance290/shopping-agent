import asyncio
from dotenv import load_dotenv
load_dotenv('apps/backend/.env')

from apps.backend.github_client import github_client

async def main():
    print(f"Token present: {bool(github_client.token)}")
    print(f"Repo: {github_client.repo}")
    
    try:
        issue = await github_client.create_issue(
            title="[Test] GitHub Integration Check",
            body="This is a test issue to verify permissions.",
            labels=["ai-fix"]
        )
        print("Issue creation result:")
        print(issue)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
