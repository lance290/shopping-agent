# Implementation Plan: PRD 00 — Help Center & Self-Service

**Status:** Draft — awaiting approval  
**Priority:** P0 (can build in parallel with PRD 04)  
**Estimated effort:** 1-2 days  
**Depends on:** Nothing

---

## Goal

Give buyers and sellers a place to find answers and get help. A `/help` page with FAQ articles, category navigation, search, and a contact form.

---

## Current State

- **Zero help infrastructure.** No `/help` page, no FAQ, no contact form, no knowledge base.
- The only feedback mechanism is `ReportBugModal` → GitHub Issues (engineers, not support).
- The frontend success page after registration says "we'll contact you" — there's no way for the user to contact *us*.
- No "Need help?" link anywhere in the app.

---

## Build Order

### Phase A: Backend — HelpArticle Model + Routes (1-2 hours)

**File: `apps/backend/models.py`** — add model:

```python
class HelpArticle(SQLModel, table=True):
    __tablename__ = "help_article"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True)
    title: str
    body: str  # Markdown content
    category: str = Field(index=True)  # getting_started, buying, selling, payments, account, policies
    tags: Optional[str] = None  # JSON array of tag strings
    
    published: bool = False
    author_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    view_count: int = 0
    helpful_count: int = 0
    not_helpful_count: int = 0
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**New file: `apps/backend/routes/help.py`**

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /help/articles` | Public | List articles. `?category=`, `?q=` for search. Returns published only. |
| `GET /help/articles/{slug}` | Public | Single article by slug. Increments `view_count`. |
| `POST /help/articles/{slug}/feedback` | Public | `{ "helpful": true/false }` — updates helpful/not_helpful counts |
| `POST /help/articles` | Admin | Create article |
| `PATCH /help/articles/{slug}` | Admin | Update article |
| `DELETE /help/articles/{slug}` | Admin | Soft-delete (set `published=false`) |
| `POST /help/contact` | Optional auth | Contact form submission → logs + sends email to admin |

Search implementation: PostgreSQL `ILIKE` on `title` and `body` for MVP. Simple, no dependencies.

Contact form endpoint: Since we don't have a support ticket system yet (PRD 01), the contact form will:
1. Send an email to the admin address via existing Resend service
2. Return confirmation to user
3. Later, when PRD 01 (Support Tickets) is built, this creates a ticket instead

**File: `apps/backend/main.py`** — register router.

**Migration:** New `help_article` table.

---

### Phase B: Frontend — Help Pages (2-3 hours)

**New file: `apps/frontend/app/help/page.tsx`**
- Landing page: search bar + category cards (6 categories) + popular articles
- Clean, minimal design matching existing app style
- Search triggers `GET /api/help/articles?q=xxx`
- Mobile-responsive

**New file: `apps/frontend/app/help/[category]/page.tsx`**
- Filtered article list by category
- Breadcrumb: Help → Category Name

**New file: `apps/frontend/app/help/article/[slug]/page.tsx`**
- Full article rendered from Markdown
- "Was this helpful?" Yes/No buttons at bottom
- Sidebar or bottom: "Still need help? Contact us" link

**New file: `apps/frontend/app/help/contact/page.tsx`**
- Contact form: name (pre-filled if logged in), email (pre-filled), category dropdown, description textarea
- Submit → `POST /api/help/contact`
- Success: "We've received your message. We'll respond within 24 hours."

---

### Phase C: Contextual Help Links (30 min)

Add "Need help?" links to key pages:

| Page | Location | Link Target |
|------|----------|-------------|
| `merchants/register/page.tsx` | Below submit button | `/help?category=selling` |
| `seller/page.tsx` | Header area | `/help?category=selling` |
| `page.tsx` (main app) | Footer or mobile nav | `/help` |
| Post-checkout (if exists) | Confirmation area | `/help?category=payments` |

---

### Phase D: Seed Initial Content (30 min)

**New file: `apps/backend/scripts/seed_help_articles.py`**

Seed script that creates ~15 initial articles covering:
- **Getting Started (3):** How it works, what is AI procurement, creating an account
- **Buying (4):** Searching, offer tiles, pricing/affiliates, completing a purchase
- **Selling (4):** Registering, getting verified, RFP inbox, submitting quotes
- **Payments (2):** Payment methods, platform fees
- **Account (1):** Updating profile
- **Policies (1):** Affiliate disclosure (links to existing `/disclosure` page)

Content can be placeholder-quality initially — the structure matters more than perfect copy.

---

### Phase E: Frontend Proxy Routes (15 min)

| Route file | Method | Proxies to |
|-----------|--------|-----------|
| `app/api/help/articles/route.ts` | GET, POST | `/help/articles` |
| `app/api/help/articles/[slug]/route.ts` | GET, PATCH, DELETE | `/help/articles/{slug}` |
| `app/api/help/articles/[slug]/feedback/route.ts` | POST | `/help/articles/{slug}/feedback` |
| `app/api/help/contact/route.ts` | POST | `/help/contact` |

---

### Phase F: Tests (1 hour)

**New file: `apps/backend/tests/test_help_center.py`**

| # | Test | Expected |
|---|------|----------|
| 1 | List articles (empty) | 200, `[]` |
| 2 | Admin creates article | 201, article returned |
| 3 | List articles (has one) | 200, article in list |
| 4 | Get article by slug | 200, view_count incremented |
| 5 | Get article (bad slug) | 404 |
| 6 | Search articles by query | 200, matching articles |
| 7 | Filter articles by category | 200, correct filter |
| 8 | Feedback helpful | 200, helpful_count incremented |
| 9 | Feedback not helpful | 200, not_helpful_count incremented |
| 10 | Non-admin can't create article | 403 |
| 11 | Unpublished articles hidden from public | 200, empty list (article exists but unpublished) |
| 12 | Contact form submission | 200, email sent (demo mode) |

---

## Files Changed Summary

| File | Change Type | Lines Est. |
|------|------------|-----------|
| `apps/backend/models.py` | Add `HelpArticle` model | +20 |
| `apps/backend/routes/help.py` | **New file** — 7 endpoints | ~200 |
| `apps/backend/main.py` | Register help router | +2 |
| `apps/backend/services/email.py` | Add `send_contact_form_email()` | +40 |
| `apps/backend/alembic/versions/p6_help_articles.py` | **New file** — create table | ~25 |
| `apps/backend/scripts/seed_help_articles.py` | **New file** — seed content | ~150 |
| `apps/backend/tests/test_help_center.py` | **New file** — 12 tests | ~250 |
| `apps/frontend/app/help/page.tsx` | **New file** — landing page | ~150 |
| `apps/frontend/app/help/[category]/page.tsx` | **New file** — category list | ~80 |
| `apps/frontend/app/help/article/[slug]/page.tsx` | **New file** — article detail | ~100 |
| `apps/frontend/app/help/contact/page.tsx` | **New file** — contact form | ~120 |
| `apps/frontend/app/api/help/articles/route.ts` | **New file** — proxy | ~20 |
| `apps/frontend/app/api/help/articles/[slug]/route.ts` | **New file** — proxy | ~20 |
| `apps/frontend/app/api/help/articles/[slug]/feedback/route.ts` | **New file** — proxy | ~15 |
| `apps/frontend/app/api/help/contact/route.ts` | **New file** — proxy | ~15 |
| Contextual help links (3-4 existing files) | Small edits | ~15 |

**Total:** ~1,200 lines across 16 files (12 new, 4 modified)

---

## Open Questions

1. **Markdown rendering library for frontend?** Options: `react-markdown` (already in many Next.js projects) or simple HTML. Recommendation: `react-markdown` — handles formatting, code blocks, links cleanly.
2. **Should help articles be server-rendered (SSR/ISR)?** Recommendation: Yes — better SEO, faster load. Use Next.js `generateStaticParams` with ISR revalidation.
3. **Contact form: require auth or allow anonymous?** Recommendation: Allow anonymous but pre-fill if logged in. Reduces friction for pre-signup users.
4. **Admin article editor UI:** Build a proper editor or just API + seed script for now? Recommendation: API + seed for MVP. Admin editor is nice-to-have.

---

## Relationship to PRD 01 (Support Tickets)

The contact form is the bridge:
- **Phase 6 v1 (now):** Contact form sends email to admin via Resend
- **Phase 6 v2 (PRD 01):** Contact form creates a `SupportTicket` record + sends email
- The endpoint signature stays the same; only the backend implementation changes
