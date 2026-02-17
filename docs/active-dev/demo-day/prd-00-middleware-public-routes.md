# PRD: Middleware & Public Route Access

## Business Outcome
- Measurable impact: 100% of public pages accessible to anonymous visitors (currently 0% — all redirect to /login)
- Success criteria: Affiliate network reviewer can browse homepage, search, guides, vendors, and share pages without signing in
- Target users: Anonymous visitors, affiliate network reviewers, vendors receiving outreach links

## Scope
- In-scope:
  - Update Next.js middleware to allow anonymous access to public routes
  - Ensure `/share/*` and `/quote/*` pages work for anonymous visitors (currently blocked)
  - Session detection at `/` — logged-in users see workspace, anonymous see public homepage
  - Backend API proxy must support `allowAnonymous` for public search endpoints
- Out-of-scope:
  - Building the actual public pages (separate PRDs)
  - Changing the auth flow itself (phone/SMS stays as-is)
  - Backend auth changes

## User Flow
1. Anonymous visitor arrives at any public URL (e.g., `/`, `/search?q=shoes`, `/share/abc123`, `/vendors`)
2. Middleware checks: is this a public route? If yes, pass through without redirect
3. Visitor sees the page content without being forced to log in
4. If visitor clicks "Sign In", they go to `/login` and return to their previous page after auth
5. If visitor is already logged in (has `sa_session` cookie) and hits `/`, they see the workspace

## Business Requirements

### Authentication & Authorization
- Anonymous users can access all public pages without any authentication
- The workspace at `/` requires a valid `sa_session` cookie
- API routes that serve public pages must accept anonymous requests (clickout tracking already handles `user_id=None`)
- Protected routes: only the workspace (`/` when logged in), `/admin/*`, `/seller/*`

### Monitoring & Visibility
- Track anonymous vs authenticated page views (for conversion funnel analysis)
- Log middleware decisions for debugging route access issues

### Billing & Entitlements
- No billing impact — public access is free
- Affiliate clickouts must work for anonymous users (already supported by `/api/out`)

### Data Requirements
- No new data persistence needed
- Existing `ClickoutEvent` model already handles `user_id=None` for anonymous clicks

### Performance Expectations
- Middleware check adds < 1ms per request (simple path matching)
- No additional API calls for public route detection

### UX & Accessibility
- No "flash of login page" — public pages render immediately
- Share links (`/share/*`) and quote links (`/quote/*`) must work on first click from email/SMS

### Privacy, Security & Compliance
- Public pages must not leak private user data (rows, bids, comments)
- Anonymous clickout events are logged with IP/UA but no user_id
- Rate limiting on public search to prevent abuse

## Dependencies
- Upstream: None — this is the first slice, no prerequisites
- Downstream: Every other demo-day PRD depends on this (no public pages work without it)

## Risks & Mitigations
- Accidentally exposing protected routes → Use explicit protected-path list (short) rather than public-path list (growing)
- Share/quote pages currently broken for anonymous → Test with incognito browser after deploy

## Acceptance Criteria (Business Validation)
- [ ] Anonymous user can load `/` and see public homepage (not login redirect)
- [ ] Anonymous user can load `/share/[valid-token]` and see shared content (baseline: currently redirects to login)
- [ ] Anonymous user can load `/quote/[valid-token]` and see quote form (baseline: currently redirects to login)
- [ ] Logged-in user at `/` still sees workspace (no regression)
- [ ] `/admin/*` and `/seller/*` still require auth (no regression)

## Traceability
- Parent PRD: `docs/active-dev/demo-day/parent.md`
- Product North Star: `.cfoi/branches/dev/product-north-star.md`

---
**Note:** Technical implementation decisions (middleware rewrite strategy, path matching approach) are made during /plan and /task phases, not in this PRD.
