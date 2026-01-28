# App State Progress Log

- 2026-01-28 06:15:48Z
  - Search requests are reaching /api/search and backend /rows/{id}/search.
  - Providers returning empty results:
    - SerpAPI: 429 Too Many Requests
    - SearchAPI: 429 Too Many Requests
    - Rainforest: 0 results (request_info success=true, status=None)
  - Mock search is disabled by user request.
  - Next action: restore real provider results (fresh API keys/quota or disable rate-limited providers).

- 2026-01-28 06:17:35Z
  - User requested re-enable Google search provider.
  - Need GOOGLE_CSE_API_KEY and GOOGLE_CSE_CX values to enable Google CSE provider.

- 2026-01-28 06:39:42Z
  - Search results restored after backend query sanitization and skipping constraint/answer appends when explicit query is provided.
  - Added backend tests to cover explicit query vs. constraint-built query behavior.
