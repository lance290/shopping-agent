# PRD L6: SEO & Content Strategy

**Priority:** P3 — Post-launch
**Target:** Month 2 (April 2026)
**Depends on:** Landing page (L2), Custom domain (D1), Analytics (L5)

---

## Problem

The platform has zero indexable pages. All content is behind authentication. There is no organic traffic strategy. Every user must come through paid ads or direct referral. This is expensive and unsustainable.

Competitors like Yelp, Thumbtack, and Angi own category + city keyword combinations. We have none.

---

## Solution

### R1 — Category Landing Pages (Auto-Generated)

Generate public SEO pages for each category with market data:

- `/categories/private-jet-charter` — "Compare Private Jet Charter Quotes"
- `/categories/hvac-repair` — "Get HVAC Repair Quotes Near You"
- `/categories/office-furniture` — "Find Office Furniture Deals"

Content structure:
1. Category description (AI-generated, human-reviewed)
2. Average price ranges (from anonymized transaction data)
3. Top factors to consider (from choice_factors data)
4. "Get Quotes" CTA → sign up → chat with pre-filled category
5. FAQ section (common questions for that category)

### R2 — City + Category Pages

For service categories, generate location-specific pages:

- `/categories/hvac-repair/nashville-tn`
- `/categories/private-jet-charter/nashville-tn`

Content includes local seller count, average prices, local factors.

**Scale:** Start with Tim's home market (Nashville) + 10 largest US metros.

### R3 — Blog / Guides

Create buyer guides for high-intent categories:

- "How to Charter a Private Jet: Complete 2026 Guide"
- "How to Get the Best Roofing Quote: 7 Things to Compare"
- "Business Procurement Automation: Why AI Agents Beat RFP Forms"

Publish 2–4 posts/month. Each includes CTA to try BuyAnything.

### R4 — Technical SEO

- Sitemap.xml for all public pages
- robots.txt allowing crawling of landing + category pages
- Schema.org markup (Product, Service, FAQPage)
- OG meta tags for all public pages (rich social previews)
- Core Web Vitals optimization (LCP < 2.5s, CLS < 0.1)

---

## Target Keywords (Priority)

| Keyword | Monthly Volume | Difficulty | Intent |
|---------|---------------|-----------|--------|
| "private jet charter quote" | 2,400 | Medium | Transactional |
| "get roofing quotes" | 6,600 | High | Transactional |
| "compare HVAC contractors" | 1,900 | Medium | Commercial |
| "AI procurement tool" | 720 | Low | Informational |
| "buy anything online" | 3,200 | Medium | Navigational |

---

## Acceptance Criteria

- [ ] At least 10 category landing pages live and indexed
- [ ] At least 3 city+category pages for Nashville
- [ ] Sitemap.xml submitted to Google Search Console
- [ ] At least 2 blog posts published
- [ ] Organic traffic > 100 sessions/month by end of Month 2
