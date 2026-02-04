# Review Scope - parallel-llm-openrouter

## Files to Review (Code Changes)
- `apps/bff/src/llm.ts` (modified - parallel LLM functions, OpenRouter switch)
- `apps/bff/src/index.ts` (modified - parallel flow implementation)
- `apps/bff/src/intent/index.ts` (modified - OpenRouter switch)
- `apps/backend/sourcing/repository.py` (modified - streaming timeout)
- `apps/backend/tests/test_provider_initialization.py` (modified - provider tests)

## Out of Scope
- `apps/bff/package.json` - dependency addition only
- `apps/bff/pnpm-lock.yaml` - lockfile

## Review Started: 2026-02-03T19:13:00-08:00
