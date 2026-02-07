# PRD 00: Help Center & Self-Service

**Phase:** 6 — Customer Support & Trust Infrastructure  
**Priority:** P0  
**Status:** Planning  
**Parent:** [Phase 6 Parent](./parent.md)

---

## Problem Statement

Users (buyers and sellers) have **no self-service support resources**. There is no FAQ, no knowledge base, no contact page, and no way to find answers to common questions. The only feedback mechanism is a bug-report modal that routes to GitHub Issues — invisible to users and unmonitored for support.

When users can't find help, they abandon the platform. Self-service support deflects 60-80% of support volume.

---

## Solution Overview

Build a **Help Center** at `/help` with:

1. **FAQ / Knowledge Base** — Categorized articles answering common questions
2. **Contact Form** — Structured intake for support requests (routes to support tickets, PRD 01)
3. **Status Page** — Platform health indicators
4. **Contextual Help** — In-app help links on key pages (checkout, seller dashboard, etc.)

---

## Scope

### In Scope
- `/help` landing page with search and category navigation
- FAQ content for buyers (searching, purchasing, returns) and sellers (registration, quoting, payments)
- `/help/contact` — Contact form (name, email, category, description, attachments)
- Contextual "Need help?" links on: checkout flow, seller dashboard, merchant registration, disclosure page
- Admin: CRUD for help articles (title, body, category, published status)
- SEO: Help articles server-rendered, indexable

### Out of Scope
- AI chatbot for support (future — could leverage existing BFF chat)
- Community forum
- Phone support
- Live chat with agents

---

## User Stories

**US-01:** As a buyer, I want to find answers to common questions (how search works, how to pay, what affiliate means) without contacting anyone.

**US-02:** As a seller, I want to understand how to get verified, how quoting works, and when I get paid.

**US-03:** As a user with a problem, I want to submit a support request with details and attachments so someone can help me.

**US-04:** As an admin, I want to create and edit help articles so users can find answers without filing tickets.

---

## Business Requirements

### Authentication & Authorization
- Help center: **public** (no auth required) — SEO and pre-signup discovery
- Contact form: **optional auth** — pre-fills email if logged in, but anonymous submissions allowed
- Admin article CRUD: **admin only**

### Data Requirements

**HelpArticle model:**
```
id, slug (unique), title, body (markdown), category, tags[], 
published (bool), author_id (FK user), 
view_count, helpful_count, not_helpful_count,
created_at, updated_at
```

**HelpCategory enum:**
- `getting_started` — How BuyAnything.ai works
- `buying` — Searching, comparing, purchasing
- `selling` — Registration, quoting, payments, verification
- `payments` — Affiliate, Stripe checkout, commissions, refunds
- `account` — Login, profile, notifications, privacy
- `policies` — Terms of service, privacy policy, disclosure

### Performance
- Help page loads < 1s (static/ISR)
- Search across articles < 200ms
- Contact form submission < 500ms

### UX
- Clean, minimal design consistent with platform
- Search bar prominent on help landing page
- Category cards with article counts
- "Was this helpful?" feedback on each article
- Breadcrumb navigation
- Mobile-responsive

---

## Technical Design

### Backend

**New file:** `routes/help.py`

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /help/articles` | Public | List articles, optional `?category=` and `?q=` search |
| `GET /help/articles/{slug}` | Public | Single article by slug, increments view_count |
| `POST /help/articles` | Admin | Create article |
| `PATCH /help/articles/{slug}` | Admin | Update article |
| `DELETE /help/articles/{slug}` | Admin | Unpublish article |
| `POST /help/articles/{slug}/feedback` | Public | Record helpful/not-helpful vote |
| `POST /help/contact` | Optional | Submit contact form → creates support ticket (PRD 01) |

### Frontend

| Page | Description |
|------|-------------|
| `/help` | Landing page: search bar + category cards + popular articles |
| `/help/[category]` | Article list filtered by category |
| `/help/article/[slug]` | Single article with feedback widget |
| `/help/contact` | Contact form (category selector, description, file upload) |

### Contextual Help Links

Add "Need help?" links to:
- Checkout confirmation page
- Seller dashboard (empty state + profile tab)
- Merchant registration form
- Disclosure page
- Post-purchase confirmation

---

## Content Plan (Initial Articles)

### Getting Started
- How does BuyAnything.ai work?
- What is an AI procurement agent?
- How do I create an account?

### Buying
- How do I search for products or services?
- What do the offer tiles show?
- How does pricing work? (affiliate vs direct)
- How do I complete a purchase?
- What happens after I buy?

### Selling
- How do I register as a seller?
- How do I get verified?
- How does the RFP inbox work?
- How do I submit a quote?
- When do I get paid?
- What are platform fees?

### Payments & Refunds
- What payment methods are accepted?
- How do affiliate commissions work?
- What is the platform fee for sellers?
- How do I request a refund?

### Account
- How do I update my profile?
- How do notifications work?
- How do I delete my account?

### Policies
- Terms of Service
- Privacy Policy
- Affiliate Disclosure

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Help page views / week | Growing WoW |
| Search-to-article-click rate | > 40% |
| "Was this helpful?" positive rate | > 70% |
| Contact form submissions (deflection = total help views - submissions) | < 20% of help views |
| Time from contact submission to first response | < 24 hours |

---

## Acceptance Criteria

- [ ] `/help` page renders with search and category navigation
- [ ] At least 15 initial articles published across all categories
- [ ] Search returns relevant results within 200ms
- [ ] Contact form creates a support ticket (or email if PRD 01 not yet built)
- [ ] "Was this helpful?" feedback persisted per article
- [ ] Admin can create, edit, and unpublish articles
- [ ] Contextual "Need help?" links appear on checkout, seller dashboard, and registration pages
- [ ] All pages mobile-responsive and accessible (WCAG AA)

---

## Dependencies
- **PRD 01 (Support Tickets):** Contact form routes to ticket system when available; falls back to email
- **Email service:** Already exists (`services/email.py`) for contact form confirmation

## Risks
- **Content debt** — Initial articles need to be written; stale content worse than none → add "last updated" dates
- **Search quality** — Simple text search may miss intent → start with PostgreSQL full-text search, upgrade later
