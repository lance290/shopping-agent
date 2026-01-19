# Adding New Affiliate Handlers

## Quick Start

1. Create a new handler class in `apps/backend/affiliate.py`:

```python
class MyNetworkHandler(AffiliateHandler):
    def __init__(self):
        self.api_key = os.getenv("MYNETWORK_API_KEY", "")
    
    @property
    def name(self) -> str:
        return "my_network"
    
    @property
    def domains(self) -> List[str]:
        return ["merchant1.com", "merchant2.com"]
    
    def transform(self, url: str, context: ClickContext) -> ResolvedLink:
        # Your transformation logic here
        pass
```

2. Register in `LinkResolver._register_builtin_handlers()`:

```python
self.register(MyNetworkHandler())
```

3. Add env var to `.env.example` and production config

4. Add tests to `tests/test_affiliate.py`

## Handler Guidelines

- Always return a `ResolvedLink`, even on error
- Set `rewrite_applied=False` if transformation fails
- Include error info in `metadata` for debugging
- Test with real URLs before deploying
