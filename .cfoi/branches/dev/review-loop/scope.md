# Review Scope - feature-proactive-vendor-discovery

## Files to Review
- apps/backend/models/admin.py
- apps/backend/models/__init__.py
- apps/backend/startup_migrations.py
- apps/backend/sourcing/coverage.py
- apps/backend/sourcing/provenance.py
- apps/backend/sourcing/service.py
- apps/backend/sourcing/discovery/__init__.py
- apps/backend/sourcing/discovery/classifier.py
- apps/backend/sourcing/discovery/query_planner.py
- apps/backend/sourcing/discovery/adapters/base.py
- apps/backend/sourcing/discovery/adapters/__init__.py
- apps/backend/sourcing/discovery/adapters/organic.py
- apps/backend/sourcing/discovery/extractors.py
- apps/backend/sourcing/discovery/normalization.py
- apps/backend/sourcing/discovery/dedupe.py
- apps/backend/sourcing/discovery/orchestrator.py
- apps/backend/routes/rows_search.py
- apps/backend/tests/test_vendor_discovery_foundation.py

## Out of Scope
- Unchanged frontend rendering and store files
- Existing marketplace provider implementations

## Review Started
- 2026-03-10
