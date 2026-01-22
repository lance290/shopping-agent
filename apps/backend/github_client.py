import os
import httpx
import asyncio
import logging
from typing import Optional, List, Dict, Any

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # format: "owner/repo"

logger = logging.getLogger("github_client")

class GitHubClient:
    def __init__(self, token: Optional[str] = None, repo: Optional[str] = None):
        self.token = token or GITHUB_TOKEN
        self.repo = repo or GITHUB_REPO
        self.base_url = "https://api.github.com"
        
        if not self.token:
            logger.warning("[GITHUB] Warning: GITHUB_TOKEN not set")
        if not self.repo:
            logger.warning("[GITHUB] Warning: GITHUB_REPO not set")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    async def create_issue(
        self, 
        title: str, 
        body: str, 
        labels: List[str] = None, 
        assignees: List[str] = None,
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Create a GitHub issue.
        Returns the created issue dict (including 'html_url') or None on failure.
        Retries on 5xx errors and 429 rate limits.
        """
        if not self.token or not self.repo:
            logger.error("[GITHUB] Cannot create issue: Missing credentials/config")
            return None

        url = f"{self.base_url}/repos/{self.repo}/issues"
        payload = {
            "title": title,
            "body": body,
            "labels": labels or [],
            "assignees": assignees or []
        }

        headers = self._get_headers()
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        url, 
                        headers=headers, 
                        json=payload
                    )
                    
                    if response.status_code == 201:
                        data = response.json()
                        logger.info(f"[GITHUB] Issue created: {data.get('html_url')}")
                        return data
                    
                    # Handle specific error codes that warrant a retry
                    if response.status_code in [429, 500, 502, 503, 504]:
                        retry_after = int(response.headers.get("Retry-After", 2 * (2 ** attempt)))
                        logger.warning(f"[GITHUB] Request failed with {response.status_code}. Retrying in {retry_after}s... (Attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_after)
                        continue
                        
                    # Non-retriable errors (400, 401, 403, 404, etc.)
                    logger.error(f"[GITHUB] Create issue failed: {response.status_code} - {response.text}")
                    return None
                    
            except httpx.RequestError as e:
                # Network errors are retriable
                wait_time = 2 * (2 ** attempt)
                logger.warning(f"[GITHUB] Network error: {e}. Retrying in {wait_time}s... (Attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"[GITHUB] Unexpected error creating issue: {e}")
                return None
                
        logger.error(f"[GITHUB] Failed to create issue after {max_retries} attempts.")
        return None

# Singleton instance
github_client = GitHubClient()
