# PRD L2: Landing Page & Onboarding

**Priority:** P1 — Pre-launch
**Target:** Week 3 (Feb 24–28, 2026)
**Depends on:** Custom domain (D1), Analytics (M1)

---

## Problem

There is no public-facing landing page. Users entering the app land directly in the chat workspace with no context. Viral share links and ad traffic have nowhere to land that explains value before asking for commitment.

---

## Solution

### R1 — Landing Page (`/`)

A single-page marketing site with:

1. **Hero section**
   - Headline: "Tell us what you need. We'll find who can deliver."
   - Subhead: "AI-powered procurement for anything — from private jets to plumbing."
   - CTA: "Start Shopping" → `/sign-up`
   - Background: subtle gradient or abstract mesh, not stock photos

2. **How It Works** (3 steps)
   - 💬 "Describe what you need" — conversational, not forms
   - 📊 "Compare options instantly" — tiles with real data
   - ✅ "Close the deal" — checkout, contracts, done

3. **Category Examples** (3 cards)
   - Private jet charter (Tim's use case — social proof)
   - Home services (roofing, HVAC — mass market)
   - Business procurement (office supplies, equipment — B2B)

4. **Social Proof**
   - Tim quote: "I contacted 12 charter companies in 5 minutes."
   - Metrics: "X vendors, Y categories, Z quotes delivered"

5. **For Sellers CTA**
   - "List your business" → `/merchants/register`

6. **Footer**
   - Links: Terms, Privacy, Contact
   - Social icons (if applicable)

### R2 — Onboarding Flow (Post-Signup)

First-time users see a 3-step guided experience:

1. "What are you looking for today?" — category picker or free text
2. Brief explanation of the chat + tiles layout
3. First search auto-triggered from their answer

Skip option available. Stores `user.onboarding_complete = true` after completion.

### R3 — Share Link Landing

When a non-authenticated user opens a share link (`/share/[token]`):

1. Show read-only project view with tiles
2. Banner: "Join to collaborate on this project"
3. Sign up → auto-added as collaborator
4. Redirect to the shared project after auth

---

## Design Notes

- **Mobile-first** — ads drive >80% mobile traffic
- Use existing Tailwind setup
- No heavy animations — fast load time is critical for ad conversion
- Meta tags (OG image, title, description) for rich social previews

---

## Acceptance Criteria

- [ ] Landing page loads at `/` for unauthenticated users
- [ ] Authenticated users bypass to `/workspace` (or equivalent)
- [ ] "Start Shopping" CTA → sign up → first search within 60 seconds
- [ ] Share links show read-only preview for non-auth users
- [ ] Mobile layout tested on iOS Safari and Android Chrome
- [ ] Lighthouse performance score > 80
