# Performance Testing Quick Start

## Quick Commands

### 1. Run the Database Migration

```bash
cd apps/backend
uv run alembic upgrade head
```

### 2. Verify Indexes Were Created

```bash
# Connect to database
psql $DATABASE_URL

# Check row table indexes
\d+ row

# Should show indexes like:
#   ix_row_status
#   ix_row_user_id
#   ix_row_created_at
#   ix_row_outreach_status
```

### 3. Test Query Performance

#### Before/After Comparison

```python
# Test script: test_performance.py
import asyncio
import time
from database import get_session, engine
from sqlmodel import select, text
from models import Row, Bid, AuthSession

async def test_row_status_query():
    """Test row filtering by status."""
    async with get_session() as session:
        # Time the query
        start = time.time()
        result = await session.exec(
            select(Row).where(Row.status == "sourcing").limit(100)
        )
        rows = result.all()
        duration = time.time() - start

        print(f"Row status query: {duration*1000:.2f}ms ({len(rows)} rows)")
        return duration

async def test_auth_lookup():
    """Test auth session lookup."""
    async with get_session() as session:
        start = time.time()
        result = await session.exec(
            select(AuthSession)
            .where(AuthSession.session_token_hash == "test_hash")
            .where(AuthSession.revoked_at.is_(None))
        )
        session_obj = result.first()
        duration = time.time() - start

        print(f"Auth lookup: {duration*1000:.2f}ms")
        return duration

async def test_bid_eager_loading():
    """Test bid queries with eager loading."""
    from sqlalchemy.orm import selectinload, joinedload

    async with get_session() as session:
        start = time.time()
        result = await session.exec(
            select(Row)
            .where(Row.id == 1)
            .options(
                selectinload(Row.bids).options(
                    joinedload(Bid.seller)
                )
            )
        )
        row = result.first()
        if row:
            _ = [bid.seller for bid in row.bids]  # Access loaded data
        duration = time.time() - start

        print(f"Bid eager loading: {duration*1000:.2f}ms")
        return duration

async def test_explain_analyze():
    """Run EXPLAIN ANALYZE on a query."""
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            EXPLAIN ANALYZE
            SELECT * FROM row
            WHERE status = 'sourcing'
            AND user_id = 1
            ORDER BY created_at DESC
            LIMIT 10
        """))

        print("\n=== EXPLAIN ANALYZE Output ===")
        for row in result:
            print(row[0])

async def main():
    print("Running Performance Tests...\n")

    await test_row_status_query()
    await test_auth_lookup()
    await test_bid_eager_loading()
    await test_explain_analyze()

    print("\n✓ Tests complete")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
cd apps/backend
uv run python test_performance.py
```

### 4. Check Index Usage

```sql
-- Connect to database
psql $DATABASE_URL

-- Check which indexes are being used
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as times_used,
    idx_tup_read as rows_read,
    idx_tup_fetch as rows_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC
LIMIT 20;

-- Find unused indexes (after running for a while)
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
AND idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

### 5. Monitor Connection Pool

#### Enable Pool Monitoring

Add to `.env`:
```bash
DB_ECHO=false
DB_ENABLE_QUERY_LOGGING=true
DB_SLOW_QUERY_THRESHOLD=0.5
```

#### Check Pool Health

```python
from database import check_db_health

health = await check_db_health()
print(health)
```

Or via HTTP endpoint (add to main.py):
```python
@app.get("/health/db")
async def db_health():
    from database import check_db_health
    return await check_db_health()
```

### 6. Load Testing

#### Simple Load Test with curl

```bash
# Test endpoint performance
time curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/rows

# Parallel requests
seq 1 100 | xargs -P 10 -I {} \
  curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/rows > /dev/null
```

#### Using Apache Bench

```bash
# Install ab
brew install apache-bench  # macOS
apt install apache2-utils   # Linux

# Run load test (100 requests, 10 concurrent)
ab -n 100 -c 10 -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/rows

# Look for:
#   Time per request: <100ms (good)
#   Failed requests: 0
#   Requests per second: >50
```

#### Using Locust (Recommended)

```bash
# Install
pip install locust

# Create locustfile.py (see DATABASE_OPTIMIZATION.md)

# Run UI-based load test
locust -f locustfile.py --host=http://localhost:8000

# Or headless
locust -f locustfile.py --host=http://localhost:8000 \
  --users 50 --spawn-rate 10 --run-time 60s --headless
```

---

## Performance Targets

### Query Performance
- Simple queries (single table): <10ms
- Complex queries (joins): <50ms
- Aggregations: <100ms
- Search queries: <200ms

### API Response Times
- GET endpoints: <100ms (P50), <500ms (P95)
- POST endpoints: <200ms (P50), <1s (P95)
- Admin stats: <1s

### Database Load
- Connection pool utilization: <80%
- Active connections: <50% of max_connections
- Slow queries (>1s): <10 per hour

---

## Common Issues & Fixes

### Issue: Queries still slow after migration

**Check**:
```sql
EXPLAIN ANALYZE SELECT * FROM row WHERE status = 'sourcing';
```

**Expected**: `Index Scan using ix_row_status`
**If you see**: `Seq Scan` → Run `ANALYZE row;` to update statistics

### Issue: Connection pool exhausted

**Symptoms**:
```
TimeoutError: QueuePool limit of size 20 overflow 10 reached
```

**Fix**:
```bash
# Increase pool size
DB_POOL_SIZE=30
DB_MAX_OVERFLOW=20
```

### Issue: N+1 queries

**Symptoms**: Many individual queries in logs

**Fix**: Use eager loading
```python
# Bad
rows = await session.exec(select(Row))
for row in rows:
    print(row.bids)  # Triggers query per row

# Good
rows = await session.exec(
    select(Row).options(selectinload(Row.bids))
)
```

### Issue: Slow admin stats endpoint

**Check**: Look for separate queries in logs

**Fix**: Admin endpoint already optimized with aggregate queries. If still slow:
1. Add database read replica
2. Cache results (5-minute TTL)
3. Pre-compute metrics asynchronously

---

## Benchmarking Commands

### Database Level

```bash
# Connection test
time psql $DATABASE_URL -c "SELECT 1"

# Simple query benchmark
pgbench -c 10 -j 2 -T 60 $DATABASE_URL

# Table statistics
psql $DATABASE_URL -c "
  SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size('public.'||tablename)) as size,
    n_live_tup as rows
  FROM pg_stat_user_tables
  ORDER BY pg_total_relation_size('public.'||tablename) DESC
"
```

### Application Level

```bash
# Start backend with timing
cd apps/backend
time uv run uvicorn main:app --reload

# Test specific endpoint
time curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/rows/1/bids

# Profile with py-spy
pip install py-spy
py-spy record -o profile.svg -- uv run python main.py
```

---

## Before/After Metrics Template

Document your improvements:

```markdown
## Performance Improvements

### Test Setup
- Database: PostgreSQL 15
- Rows: 10,000
- Bids: 500,000
- Environment: Local development

### Query: Row by Status

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Execution time | 523ms | 4.2ms | 124x faster |
| Rows scanned | 10,000 | 847 | 12x fewer |
| Index used | None (seq scan) | ix_row_status | ✓ |

### Query: Auth Lookup

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Execution time | 189ms | 0.8ms | 236x faster |
| Rows scanned | 15,432 | 1 | 15,432x fewer |
| Index used | None | ix_auth_session_token_active | ✓ |

### API Endpoint: GET /api/rows

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| P50 response time | 342ms | 28ms | 12x faster |
| P95 response time | 1,234ms | 89ms | 14x faster |
| Queries per request | 52 (N+1) | 2 | 26x fewer |
```

---

## Next Steps

1. **Run migration**: `uv run alembic upgrade head`
2. **Verify indexes**: Check with `\d+` in psql
3. **Test performance**: Run the test script
4. **Monitor production**: Watch slow query logs
5. **Iterate**: Add more indexes if needed

For detailed information, see [DATABASE_OPTIMIZATION.md](./DATABASE_OPTIMIZATION.md)
