# Decisions - enhancement-user-data-isolation

> Record architectural/product decisions and rationale.

- **2026-01-09**: Scope isolation to `Row` only for MVP; design to support future account-based system.
- **2026-01-09**: Add `user_id` to `AuthSession` and use it as the authorization anchor.
- **2026-01-09**: Accept DB reset (no migration) for initial rollout.

