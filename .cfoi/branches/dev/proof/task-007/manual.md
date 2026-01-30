# Manual Proof - task-007

## Provider status + normalization snapshot

1) Ensure mock provider enabled (so provider_status entries are present):
```
USE_MOCK_SEARCH=true
```

2) Run search:
```
curl -X POST http://localhost:8000/rows/2/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <SESSION_TOKEN>" \
  -d '{
    "query": "running shoes",
    "search_intent": { "product_category": "running_shoes", "max_price": 80 }
  }'
```

3) Capture response snippet showing provider_statuses entries with status + latency.

## Evidence

```json
{
  "results": [],
  "provider_statuses": [
    {
      "provider_id": "rainforest",
      "status": "timeout",
      "result_count": 0,
      "latency_ms": 8002,
      "message": "Search timed out"
    }
  ]
}
```

✅ `provider_statuses` returned with `status`, `latency_ms`, and `message` fields.
