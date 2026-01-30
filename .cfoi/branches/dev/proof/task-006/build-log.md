# Build Log - task-006

## Summary
Implemented provider query adapters and taxonomy helpers to map SearchIntent into per-provider query payloads.

## Files Touched
- apps/backend/sourcing/taxonomy.py
- apps/backend/sourcing/adapters/__init__.py
- apps/backend/sourcing/adapters/base.py
- apps/backend/sourcing/adapters/rainforest.py
- apps/backend/sourcing/adapters/google_cse.py
- apps/backend/sourcing/__init__.py
- apps/backend/tests/test_provider_adapters.py

## Root Cause Addressed
Search Architecture v2 lacked adapter-layer query construction, preventing provider-specific query maps from being generated and audited.

## North Star Alignment
Supports provider adapter activation and auditability (provider_query_map) per effort north star.
Reference: .cfoi/branches/dev/efforts/refactor-search-architecture-v2/product-north-star.md

## Manual Test Instructions
1. POST `/rows/{id}/search` with category + price constraints.
2. Fetch row and confirm provider_query_map includes rainforest/google_cse entries.
