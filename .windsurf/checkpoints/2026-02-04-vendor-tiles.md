# Vendor Tiles Debug Checkpoint
**Date:** Feb 4, 2026 ~2:07am
**Status:** BROKEN - vendor tiles not displaying

## What Should Happen
1. User asks "private jet from SAN to EWR"
2. LLM asks clarifying questions (date, passengers)
3. User provides details
4. LLM creates row with `is_service: true`, `service_category: "private_aviation"`
5. BFF fetches vendors from `/outreach/vendors/private_aviation`
6. Frontend displays vendor tiles with "Request Quote" button

## What's Actually Happening
1-3 work correctly
4. LLM creates row but `choice_answers` is NULL - `is_service` not saved
5. RowStrip sees no `is_service`, triggers product search
6. Product search overwrites vendors with Amazon products

## Root Cause
The LLM sets `is_service: true` during `ask_clarification` but doesn't repeat it on `create_row`. The BFF needs to carry over the LLM's decision from `pendingClarification`.

## The Fix (Not Yet Working)
In `apps/bff/src/index.ts`, in the `create_row` handler:
```typescript
const pc = (pendingClarification?.partial_constraints || {}) as Record<string, any>;
const isService = action.is_service || pc.is_service;
const svcCategory = action.service_category || pc.service_category;
```

This is NOT a heuristic - it's preserving the LLM's earlier decision.

## Files Changed Today (20+ commits)
- `apps/bff/src/index.ts` - vendor fetch logic, pendingClarification handling
- `apps/bff/src/llm.ts` - added is_service to ask_clarification schema
- `apps/frontend/app/components/Chat.tsx` - vendors_loaded handler
- `apps/frontend/app/components/RowStrip.tsx` - skip product search for service rows

## To Resume
1. Ensure BFF carries over `is_service` from `pendingClarification.partial_constraints`
2. Ensure `ask_clarification` action stores `is_service: true` in `partial_constraints`
3. Ensure RowStrip checks `choice_answers.is_service` before triggering product search
4. Test: "private jet from SAN to EWR" → clarifying questions → vendor tiles

## Backend Vendor Data Confirmed Working
```bash
curl http://localhost:8000/outreach/vendors/private_aviation
# Returns 10 charter providers
```

## Current Git State
- Branch: dev
- Latest commit: badf6d7
- Stashed changes: WIP on dev
