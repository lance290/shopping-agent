# Manual Evidence

## Curl verification (BFF -> backend)
Command:
```bash
curl -X POST http://localhost:8081/api/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <SESSION_TOKEN>" \
  -d '{
    "rowId": 1,
    "query": "red running shoes under $80"
  }'
```

Response (excerpt):
```json
{
  "results": [],
  "search_intent": {
    "product_category": "running_shoes",
    "taxonomy_version": "1.0",
    "category_path": ["Footwear", "Athletic Shoes", "Running Shoes"],
    "product_name": "running shoes",
    "max_price": 80,
    "features": {"color": "red"},
    "keywords": ["red", "running", "shoes"],
    "raw_input": "red running shoes under $80"
  }
}
```
