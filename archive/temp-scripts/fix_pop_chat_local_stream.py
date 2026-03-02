import os

path = "apps/backend/routes/pop_chat.py"
with open(path, "r") as f:
    content = f.read()

# Instead of relying on an HTTP call that could fail/timeout because of uvicorn single-worker issues or loopback URLs, 
# let's just trigger the real deal searching service directly here.
import re

if "_stream_search" in content:
    # First, fix imports
    content = content.replace(
        "from routes.chat import _create_row, _update_row, _save_choice_factors, _stream_search",
        "from routes.chat import _create_row, _update_row, _save_choice_factors\nfrom routes.rows_search import get_sourcing_repo, _sanitize_query\nfrom sourcing.service import SourcingService"
    )
    
    # Define a new helper function we can just call locally instead of going out over HTTP
    helper = """
async def _trigger_search_local(session: AsyncSession, row: Row, query: str):
    try:
        row.status = "bids_arriving"
        session.add(row)
        await session.commit()
        
        sourcing_service = SourcingService(session, get_sourcing_repo())
        sanitized = _sanitize_query(query, True)
        
        await sourcing_service.search_and_persist(row.id, sanitized)
    except Exception as e:
        logger.warning(f"[Pop Web] Search failed for row {row.id}: {e}")
"""

    if "def _trigger_search_local" not in content:
        content = content.replace("def _sign_guest_project", helper + "\ndef _sign_guest_project")
        
    # Replace usages
    content = re.sub(
        r"auth_header = request.headers.get\(\"Authorization\"\)\s+for row, q in created_rows:\s+try:\s+async for _batch in _stream_search.*?except Exception as e:\s+logger.warning\(.*?e\}\)",
        r"for row, q in created_rows:\n                await _trigger_search_local(session, row, q)",
        content,
        flags=re.DOTALL
    )
    
    content = re.sub(
        r"auth_header = request.headers.get\(\"Authorization\"\)\s+try:\s+async for _batch in _stream_search\(target_row.id, search_query, authorization=auth_header\):\s+pass\s+except Exception as e:\s+logger.warning\(.*?e\}\)",
        r"await _trigger_search_local(session, target_row, search_query)",
        content,
        flags=re.DOTALL
    )

    with open(path, "w") as f:
        f.write(content)
