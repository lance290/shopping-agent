# Manual Proof - task-006

## Provider adapter outputs

1) Invoke search with structured payload (example):
```
curl -X POST http://localhost:8000/rows/2/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <SESSION_TOKEN>" \
  -d '{
    "query": "running shoes",
    "search_intent": { "product_category": "running_shoes", "max_price": 80 }
  }'
```

2) Fetch row payload:
```
curl -s http://localhost:8000/rows/2 \
  -H "Authorization: Bearer <SESSION_TOKEN>"
```

Captured snippet (provider_query_map):
```
"provider_query_map":"{\"queries\": {\"rainforest\": {\"provider_id\": \"rainforest\", \"query\": \"running shoes\", \"filters\": {\"max_price\": 80.0}, \"metadata\": {\"taxonomy_version\": \"shopping_v1\", \"category\": \"running_shoes\"}}, \"google_cse\": {\"provider_id\": \"google_cse\", \"query\": \"running shoes\", \"filters\": {}, \"metadata\": {\"taxonomy_version\": \"shopping_v1\", \"category_path\": \"shoes > running shoes\"}}}}"
```
