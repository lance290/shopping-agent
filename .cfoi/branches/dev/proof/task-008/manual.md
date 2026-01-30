# Manual Evidence

### Initial State (0 bids)
```
Row 2 has 0 bids
```

### First Search Response
```json
{
  "results": [
    {
      "title": "running shoes - Style A Premium Edition",
      "price": 131.79,
      "merchant": "Kohl's",
      "url": "https://example.com/product/4213989757",
      "bid_id": 2
    },
    ...
  ],
  "provider_statuses": [
    {
      "provider_id": "rainforest",
      "status": "timeout",
      "result_count": 0,
      "latency_ms": 8001,
      "message": "Search timed out"
    },
    {
      "provider_id": "mock",
      "status": "ok",
      "result_count": 15,
      "latency_ms": 14,
      "message": null
    }
  ]
}
```

### After First Search (15 bids created)
```
Row 2 has 15 bids
- Bid 2: running shoes - Style A Premium Edition (131.79 USD) - Canonical: https://example.com/product/4213989757
- Bid 3: running shoes - Style B Standard Edition (40.73 USD) - Canonical: https://example.com/product/4213989758
...
- Bid 16: running shoes - Style O Standard Edition (134.1 USD) - Canonical: https://example.com/product/4213989771
```

### After Second Search (15 bids stable - Deduplication verified)
```
Row 2 has 15 bids
- Bid 2: running shoes - Style A Premium Edition (131.79 USD) - Canonical: https://example.com/product/4213989757
...
```

✅ Bids are correctly persisted and deduplicated by canonical URL. Provider statuses are returned in the response.
