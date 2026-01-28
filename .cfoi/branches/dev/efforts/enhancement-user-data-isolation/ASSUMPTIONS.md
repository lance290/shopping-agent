# Assumptions - enhancement-user-data-isolation

- **MVP scope**: `Row` is the only persisted user-owned entity that needs isolation right now.
- **Auth stability**: Session cookie `sa_session` is present for authenticated app usage and can be forwarded as `Authorization: Bearer <token>`.
- **No sharing/admin**: Sharing, org/team, and admin override are deferred.
- **Data reset acceptable**: It is acceptable to reset dev/prod DB for this effort.

