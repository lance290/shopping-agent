# Effort North Star (Effort: feature-email-auth, v2026-01-09)

## Goal Statement
Enable secure, low-friction email sign-in using verification codes (sent via Resend) so returning users can access the home page reliably.

## Ties to Product North Star
- **Product Mission**: Eliminate friction by reducing onboarding/auth overhead while maintaining trust and auditability.
- **Supports Metric**: Time to first request (<15 seconds) by keeping authentication fast and simple.

## In Scope
- Email sign-in using a verification code delivered via Resend
- Ability to log out and log back in at will
- Home page as the only protected route for now

## Out of Scope
- Password-based authentication
- Code expiration, rate limiting, device trust, and multi-factor policies (deferred)

## Acceptance Checkpoints
- [ ] Unauthenticated user cannot access home page
- [ ] User can request a verification code via Resend and complete sign-in
- [ ] User can log out and log back in successfully

## Dependencies & Risks
- **Dependencies**: Working email delivery via Resend; env vars configured
- **Risks**: Abuse/spam risk without expiration or rate limiting

## Approver / Date
- Approved by: USER
- Date: 2026-01-09
