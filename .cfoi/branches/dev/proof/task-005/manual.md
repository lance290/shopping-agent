# Manual Proof - task-005

## Persisted intent + provider query map

1) Run search with structured payload:
```
curl -X POST http://localhost:8000/rows/2/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <SESSION_TOKEN>" \
  -d '{
    "query": "running shoes",
    "search_intent": { "product_category": "running_shoes", "max_price": 80 },
    "provider_query_map": { "queries": { "rainforest": { "provider_id": "rainforest", "query": "running shoes" } } }
  }'
```

2) Fetch row payload:
```
curl -s http://localhost:8000/rows/2 \
  -H "Authorization: Bearer <SESSION_TOKEN>"
```

Result (truncated):
```
"search_intent":"{\"product_category\": \"running_shoes\", \"max_price\": 80}",
"provider_query_map":"{\"queries\": {\"rainforest\": {\"provider_id\": \"rainforest\", \"query\": \"running shoes\"}}}"
```
# Manual Evidence

(Attach screenshots/logs here.)
