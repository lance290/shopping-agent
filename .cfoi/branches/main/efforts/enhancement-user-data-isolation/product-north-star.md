# Effort North Star (Effort: enhancement-user-data-isolation, v2026-01-09)

## Goal Statement
Ensure each authenticated user can only see and operate on their own chats/searches/rows.

## Ties to Product North Star
- **Product Mission**: Trustworthy, low-friction procurement boards
- **Supports Metric**: Buyer satisfaction (trust + privacy) and auditability

## In Scope
- Add ownership semantics to persisted user data (rows/chats/searches)
- Enforce authorization checks server-side so cross-user access is prevented
- Add automated test coverage proving isolation

## Out of Scope
- Team/organization sharing
- Admin impersonation / support tooling
- Fine-grained permissions beyond “owner-only”

## Acceptance Checkpoints
- [ ] A user cannot read another user’s rows/chats/searches, even by guessing IDs
- [ ] A user cannot modify/delete another user’s rows/chats/searches

## Dependencies & Risks
- **Dependencies**: Stable auth session → user resolution (email → user_id)
- **Risks**: Missing call sites causing partial isolation; data migrations required

## Approver / Date
- Approved by: TBD
- Date: TBD
