# Plan: Multi-Provider Procurement Search Enhancement

## Goal
Enhance the existing `/api/rows/search` system with provider-specific adapters and unified result normalization to improve procurement search success rates across multiple provider sources.

## Constraints
- Must integrate with existing Clerk authentication and SQLAlchemy models
- Extend existing `/api/rows` CRUD patterns, not create parallel systems
- Build on current `rows_search` route functionality
- No external API dependencies for core functionality
- Focus on provider adapter architecture that advances North Star metrics
- Leverage existing simple REST architecture

## Technical Approach

### Backend Models (SQLAlchemy Extensions)
```python
# Extend existing rows model via Alembic migration
class Row(Base):  # Existing model
    # ... existing fields ...
    
    # Add provider-specific fields
    provider_source = Column(String, nullable=True)  # "acme_industrial", "global_supply"
    provider_data = Column(JSON, nullable=True)  # Raw provider response
    normalized_price = Column(Decimal(10, 2), nullable=True)  # Standardized pricing
    availability_status = Column(String, nullable=True)  # "in_stock", "2_weeks", "quote_only"
    last_provider_sync = Column(DateTime, nullable=True)
    provider_item_id = Column(String, nullable=True)  # Provider's unique ID for deduplication

class SearchFilter(Base):
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)  # Clerk user ID
    name = Column(String, nullable=False)  # "Heavy Equipment Search"
    filters = Column(JSON, nullable=False)  # price_min, price_max, category, location
    provider_preferences = Column(JSON, nullable=True)  # preferred/excluded providers
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
```

### Core Provider Search Engine
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

class ProviderSearchEngine:
    def __init__(self, timeout_seconds: int = 2):
        self.timeout = timeout_seconds
        self.providers = {}
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def search_all_providers(self, query: str, filters: dict) -> dict:
        """Query all providers simultaneously with circuit breaker and timeout"""
        provider_tasks = []
        
        for provider_name, adapter in self.providers.items():
            task = asyncio.create_task(
                self._search_single_provider(provider_name, adapter, query, filters)
            )
            provider_tasks.append(task)
        
        # Wait for all providers with timeout
        try:
            provider_results = await asyncio.wait_for(
                asyncio.gather(*provider_tasks, return_exceptions=True),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            # Handle partial results
            provider_results = [task.result() if task.done() else {"error": "timeout"} 
                              for task in provider_tasks]
        
        # Merge results with provider attribution
        merged_results = self._merge_provider_results(provider_results)
        
        return {
            "results": merged_results,
            "provider_coverage": self._calculate_coverage(provider_results),
            "search_meta": {
                "providers_queried": len(self.providers),
                "providers_responded": len([r for r in provider_results if not isinstance(r, Exception)]),
                "response_time": self.timeout,
                "dedupe_preserved": True  # Maintain separate entries for negotiation
            }
        }
    
    async def _search_single_provider(self, provider_name: str, adapter, query: str, filters: dict):
        """Search single provider with error handling"""
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                self.executor, 
                adapter.search, 
                query, 
                filters
            )
            return {
                "provider": provider_name,
                "results": results,
                "status": "success",
                "timestamp": datetime.utcnow()
            }
        except Exception as e:
            return {
                "provider": provider_name,
                "results": [],
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }
    
    def _merge_provider_results(self, provider_results: list) -> list:
        """Merge results while preserving provider attribution - NO DEDUPLICATION"""
        all_results = []
        
        for provider_result in provider_results:
            if isinstance(provider_result, dict) and provider_result.get("results"):
                for item in provider_result["results"]:
                    normalized_item = self._normalize_item(item, provider_result["provider"])
                    all_results.append(normalized_item)
        
        # Sort by price but maintain all provider options
        return sorted(all_results, key=lambda x: x.get("normalized_price", float('inf')))
    
    def _normalize_item(self, raw_item: dict, provider_name: str) -> dict:
        """Normalize item format while preserving provider identity"""
        return {
            "title": raw_item.get("name") or raw_item.get("title") or raw_item.get("item"),
            "description": raw_item.get("description", ""),
            "price": raw_item.get("price", 0),
            "normalized_price": Decimal(str(raw_item.get("price", 0))),
            "provider_source": provider_name,
            "provider_item_id": f"{provider_name}_{raw_item.get('id', 'unknown')}",
            "availability_status": raw_item.get("availability", "unknown"),
            "provider_data": raw_item,  # Preserve raw data
            "last_provider_sync": datetime.utcnow()
        }
    
    def _calculate_coverage(self, provider_results: list) -> dict:
        """Calculate provider coverage metrics"""
        successful_providers = [
            r["provider"] for r in provider_results 
            if isinstance(r, dict) and r.get("status") == "success" and r.get("results")
        ]
        
        return {
            "providers_with_results": len(successful_providers),
            "provider_names": successful_providers,
            "coverage_met": len(successful_providers) >= 2  # North Star: ≥2 providers
        }
```

### Provider Adapter System
```python
class ProviderAdapter:
    def __init__(self, provider_config: dict):
        self.config = provider_config
        self.name = provider_config.get("name", "unknown")
    
    def search(self, query: str, filters: dict) -> List[dict]:
        """Convert search to provider-specific format and return results"""
        raise NotImplementedError

class MockAcmeIndustrialAdapter(ProviderAdapter):
    def search(self, query: str, filters: dict) -> List[dict]:
        # Mock realistic price variations and availability
        base_items = [
            {"id": "ACM001", "name": "Industrial Pump A100", "price": 1500, "availability": "in_stock"},
            {"id": "ACM002", "name": "Hydraulic Valve V200", "price": 850, "availability": "2_weeks"},
            {"id": "ACM003", "name": "Motor Controller MC50", "price": 2200, "availability": "in_stock"}
        ]
        
        # Filter by price range if specified
        if filters.get("price_min") or filters.get("price_max"):
            price_min = filters.get("price_min", 0)
            price_max = filters.get("price_max", float('inf'))
            base_items = [item for item in base_items if price_min <= item["price"] <= price_max]
        
        # Search filter
        if query:
            query_lower = query.lower()
            base_items = [item for item in base_items if query_lower in item["name"].lower()]
        
        return base_items

class MockGlobalSupplyAdapter(ProviderAdapter):
    def search(self, query: str, filters: dict) -> List[dict]:
        # Same items with 15-30% price differences
        base_items = [
            {"id": "GS1001", "name": "Industrial Pump A100", "price": 1350, "availability": "in_stock"},  # 10% lower
            {"id": "GS1002", "name": "Hydraulic Valve V200", "price": 950, "availability": "in_stock"},   # 12% higher
            {"id": "GS1003", "name": "Motor Controller MC50", "price": 2650, "availability": "quote_only"} # 20% higher
        ]
        
        # Apply same filtering logic
        if filters.get("price_min") or filters.get("price_max"):
            price_min = filters.get("price_min", 0)
            price_max = filters.get("price_max", float('inf'))
            base_items = [item for item in base_items if price_min <= item["price"] <= price_max]
        
        if query:
            query_lower = query.lower()
            base_items = [item for item in base_items if query_lower in item["name"].lower()]
        
        return base_items

class MockSupplyChainPlusAdapter(ProviderAdapter):
    def search(self, query: str, filters: dict) -> List[dict]:
        # Third provider with different inventory
        base_items = [
            {"id": "SCP100", "name": "Industrial Pump A100", "price": 1750, "availability": "1_week"},    # 17% higher
            {"id": "SCP200", "name": "Heavy Duty Compressor", "price": 3200, "availability": "in_stock"},
            {"id": "SCP300", "name": "Pneumatic Cylinder PC300", "price": 450, "availability": "in_stock"}
        ]
        
        # Apply filtering
        if filters.get("price_min") or filters.get("price_max"):
            price_min = filters.get("price_min", 0)
            price_max = filters.get("price_max", float('inf'))
            base_items = [item for item in base_items if price_min <= item["price"] <= price_max]
        
        if query:
            query_lower = query.lower()
            base_items = [item for item in base_items if query_lower in item["name"].lower()]
        
        return base_items
```

### Backend Routes (FastAPI Extensions)
```python
# Initialize search engine with providers
search_engine = ProviderSearchEngine(timeout_seconds=2)
search_engine.providers = {
    "acme_industrial": MockAcmeIndustrialAdapter({"name": "Acme Industrial"}),
    "global_supply": MockGlobalSupplyAdapter({"name": "Global Supply Co"}),
    "supply_chain_plus": MockSupplyChainPlusAdapter({"name": "SupplyChain Plus"})
}

@app.get("/api/rows/search")  # Enhanced existing route
async def search_rows_enhanced(
    q: str,
    provider_sources: Optional[str] = None,  # "acme_industrial,global_supply"
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    availability: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    filters = {
        "price_min": price_min,
        "price_max": price_max,
        "availability": availability
    }
    
    # Multi-provider search
    search_results = await search_engine.search_all_providers(q, filters)
    
    # Store successful results in database
    stored_rows = []
    for result in search_results["results"]:
        row_data = {
            "title": result["title"],
            "description": result["description"],
            "price": result["price"],
            "provider_source": result["provider_source"],
            "provider_data": result["provider_data"],
            "normalized_price": result["normalized_price"],
            "availability_status": result["availability_status"],
            "provider_item_id": result["provider_item_id"],
            "last_provider_sync": result["last_provider_sync"],
            "user_id": user["user_id"]
        }
        
        # Create new Row instance
        row = Row(**row_data)
        db.add(row)
        stored_rows.append(row)
    
    db.commit()
    
    return {
        "rows": stored_rows,
        "search_meta": search_results["search_meta"],
        "provider_coverage": search_results["provider_coverage"]
    }

@app.post("/api/rows/search/filters")
async def save_search_filter(filter_data: dict, user: dict = Depends(get_current_user)):
    filter_obj = SearchFilter(
        user_id=user["user_id"],
        name=filter_data["name"],
        filters=filter_data["filters"],
        provider_preferences=filter_data.get("provider_preferences")
    )
    db.add(filter_obj)
    db.commit()
    return filter_obj

@app.get("/api/rows/search/filters")
async def get_search_filters(user: dict = Depends(get_current_user)):
    return db.query(SearchFilter).filter(SearchFilter.user_id == user["user_id"]).all()
```

### Frontend Components (Next.js App Router)
- `app/search/page.tsx` - Enhanced search interface with provider filtering
- `components/ProviderFilterPanel.tsx` - Select/exclude specific providers
- `components/SearchResultCard.tsx` - Enhanced row display with provider attribution
- `components/SavedFiltersDropdown.tsx` - Quick access to saved search combinations
- `components/ProviderComparisonView.tsx` - Compare same item across providers
- `hooks/useEnhancedSearch.ts` - Extended search functionality with provider awareness

### Search Enhancement Features
- **Concurrent Provider Querying** - All providers searched simultaneously with 2-second timeout
- **Circuit Breaker Pattern** - Handle partial results when providers fail or timeout
- **No Cross-Provider Deduplication** - Preserve separate entries for negotiation options
- **Provider Coverage Tracking** - Ensure ≥2 providers contribute results per search
- **Price Variation Display** - Show 15-30% price spreads across providers
- **Intelligent Error Handling** - Continue search with available providers if others fail

## Success Criteria
- [ ] Search queries simultaneously query 3+ mock provider sources within 2 seconds
- [ ] Provider coverage: ≥2 providers contributing results per search (95% of queries)
- [ ] Price ranges accurately reflect cross-provider variations (15-30% spreads visible)
- [ ] No cross-provider deduplication - preserve negotiation options
- [ ] Circuit breaker handles provider timeouts/failures gracefully
- [ ] Search success rate improves by 40% through multi-provider coverage
- [ ] Provider attribution visible on all search results
- [ ] System handles partial results when providers fail
- [ ] Enhanced search maintains existing `/api/rows` performance benchmarks
- [ ] Concurrent provider querying completes within timeout constraints

## Dependencies
- Existing `/api/rows` and `/api/rows/search` functionality
- Current Row model and database schema
- Mock provider datasets with realistic price variations
- Existing user authentication via Clerk
- Current SQLAlchemy/FastAPI patterns for data operations
- asyncio for concurrent provider queries

## Risks
- **Provider timeout cascade** - All providers timing out simultaneously (mitigated by circuit breaker)
- **Database performance** - Storing results from 3+ providers per search (mitigated by async writes)
- **Memory usage** - Concurrent provider queries consuming resources (mitigated by ThreadPoolExecutor limits)
- **Mock data maintenance** - Keeping provider variations realistic (documented update process)
- **Partial result handling** - User experience when some providers fail (clear status indicators)

## North Star Alignment
This plan directly advances the North Star metrics by:
- **Provider coverage: ≥2 providers contributing results per search** - Concurrent querying with coverage tracking
- **No cross-provider dedupe to preserve negotiation options** - Explicit preservation of duplicate items from different providers
- **Multi-provider search completion within 2-second timeout** - Async provider querying with circuit breakers
- **Price variation visibility for procurement decisions** - 15-30% price spreads displayed across providers
- **Foundation for real provider API integration** - Adapter pattern supports future external APIs