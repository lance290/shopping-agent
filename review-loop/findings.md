# Review Findings - parallel-llm-openrouter

## Summary
- **Files reviewed:** 5
- **Critical issues:** 2 (fixed)
- **Major issues:** 1 (DRY - deferred)
- **Minor issues:** 1 (test default - fixed)

## Issues Found & Fixed

### 1. Wrong API Key Check in intent/index.ts ✅ FIXED
**Location:** `apps/bff/src/intent/index.ts:205`
**Issue:** Checked `GOOGLE_GENERATIVE_AI_API_KEY` but we switched to OpenRouter
**Fix:** Changed to check `OPENROUTER_API_KEY`

### 2. Wrong API Key Check in llm.ts ✅ FIXED
**Location:** `apps/bff/src/llm.ts:237`
**Issue:** `triageProviderQuery` checked wrong env var
**Fix:** Changed to check `OPENROUTER_API_KEY`

### 3. Test Default Mismatch ✅ FIXED
**Location:** `apps/backend/tests/test_provider_initialization.py`
**Issue:** Test expected 8s default but streaming uses 30s
**Fix:** Updated test to expect 30s default

## Deferred (Architectural)

### 4. DRY Violation: Fetch Utilities Duplicated (Major)
**Location:** `llm.ts` and `index.ts`
**Description:** `fetchJsonWithTimeout`, `fetchJsonWithTimeoutRetry`, `sleep`, `isRetryableFetchError` are duplicated
**Recommendation:** Extract to shared `utils/fetch.ts`
**Status:** Deferred - would require module restructuring

## Security Review
- ✅ Auth checks present on all protected endpoints
- ✅ No hardcoded secrets (uses env vars)
- ✅ Input validation on API endpoints
- ✅ OpenRouter API key loaded from env

## Performance Review
- ✅ Parallel LLM calls for title extraction + factors
- ✅ Streaming search results (non-blocking)
- ✅ 30s timeout allows slow providers to complete

## Verdict
**PASS** - Critical API key issues fixed. DRY violation deferred.
