# PRD: Merchant Registry & Priority Matching

## Business Outcome
- **Measurable impact**: Build preferred seller network → higher margins, better buyer experience, defensible marketplace (tied to North Star: multi-seller coverage with quality)
- **Success criteria**: ≥100 registered merchants in 90 days; ≥40% of service quotes from registered merchants; registered merchant quotes have 2x acceptance rate vs cold outreach
- **Target users**: Service providers, local businesses, B2B vendors who want to receive buyer leads

## Scope
- **In-scope**: 
  - Merchant self-registration (no approval required for MVP)
  - Business profile: name, categories, service areas, contact info
  - Category taxonomy for matching
  - Priority matching algorithm (registered > WattData > Amazon/Serp)
  - Merchant dashboard (basic): view incoming RFPs, submitted quotes
  - Merchant notification preferences
- **Out-of-scope**: 
  - Merchant verification/vetting (future: business license, reviews)
  - Subscription tiers (future: premium placement)
  - Inventory management
  - Merchant-initiated listings (they respond to buyer RFPs, not post products)
  - Payment processing for merchants

## User Flow

### Merchant Registration
1. Merchant visits `/merchants/register`
2. Fills profile: business name, email, phone, website
3. Selects service categories (multi-select from taxonomy)
4. Defines service area (zip codes, radius, or regions)
5. Sets notification preferences (email frequency, RFP types)
6. Submits → Account created → Welcome email sent
7. Merchant can update profile anytime

### Priority Matching (Buyer Search)
1. Buyer submits search: "I need a new roof in Austin"
2. System extracts: category=roofing, location=Austin
3. **Matching waterfall**:
   ```
   Layer 1: Registered merchants (category + location match)
     → Immediate RFP notification
     → Quotes appear first in results
   
   Layer 2: WattData outreach (if <5 registered matches)
     → Cold outreach to discovered vendors
   
   Layer 3: Amazon/Serp (always included)
     → Product results for "buy anything"
   ```
4. Results display with source badges: "Verified Partner" vs "Marketplace"

### Merchant RFP Response
1. Registered merchant receives RFP notification (email/in-app)
2. Clicks to view RFP details + choice factors
3. Submits quote via Quote Intake form (same as cold outreach)
4. Quote appears in buyer's row with "Verified Partner" badge

## Business Requirements

### Authentication & Authorization
- **Who needs access?** 
  - Registration: anyone (public form)
  - Merchant dashboard: authenticated merchant
  - Profile updates: merchant (own profile only)
- **What actions are permitted?** 
  - Merchant: register, update profile, view RFPs, submit quotes
  - System: match merchants to RFPs, send notifications
  - Admin: view all merchants, suspend bad actors
- **What data is restricted?** 
  - Merchant contact info visible to buyers only after quote submission
  - RFP details visible only to matched merchants

### Monitoring & Visibility
- **Business metrics**: 
  - Merchant registration rate (signups/week)
  - Merchant activation rate (% who submit ≥1 quote)
  - Registered merchant quote rate (% of RFPs that get registered merchant quotes)
  - Acceptance rate by merchant type (registered vs cold)
- **Operational visibility**: Failed notifications, profile completion rate
- **User behavior tracking**: Which categories have supply gaps

### Billing & Entitlements
- **Monetization** (future):
  - Lead fee: charge merchant per RFP notification
  - Success fee: charge on accepted quotes
  - Premium tier: priority placement, more leads
- **MVP**: Free registration, no fees
- **Usage limits**: 
  - 50 RFP notifications per merchant per day
  - 10 active quotes per merchant

### Data Requirements
- **What must persist?** 
  - Merchant: id, email, business_name, phone, website, categories[], service_areas[], notification_prefs, created_at, status
  - MerchantCategory: merchant_id, category_id
  - MerchantServiceArea: merchant_id, area_type (zip/radius/region), area_value
  - MerchantRFPMatch: merchant_id, row_id, notified_at, viewed_at, quoted_at
- **Retention**: Merchant profiles permanent; match history 2 years
- **Relationships**: 
  - Merchant → Categories (M:M)
  - Merchant → ServiceAreas (1:M)
  - Merchant → SellerQuotes (1:M)
  - MerchantRFPMatch → Row (M:1)

### Performance Expectations
- **Response time**: Merchant matching <500ms; Dashboard load <1s
- **Throughput**: Support 1000 registered merchants; 100 concurrent RFP matches
- **Availability**: 99% for merchant dashboard

### UX & Accessibility
- **Standards**: 
  - Clean registration flow (<2 min to complete)
  - Category picker with search/filter
  - Service area map visualization (nice-to-have)
  - Mobile-friendly dashboard
- **Accessibility**: Forms fully accessible; proper labels
- **Devices**: Desktop + mobile

### Privacy, Security & Compliance
- **Regulations**: 
  - Business data collection: include privacy notice
  - GDPR: merchant can delete account and all data
  - CAN-SPAM: RFP notifications include unsubscribe
- **Data protection**: 
  - Merchant emails not shared with other merchants
  - Phone numbers only shared after quote acceptance
- **Audit trails**: Log all profile changes, RFP notifications

## Category Taxonomy (Initial)

```yaml
services:
  home:
    - roofing
    - hvac
    - plumbing
    - electrical
    - landscaping
    - cleaning
    - painting
    - remodeling
  auto:
    - repair
    - detailing
    - towing
  professional:
    - legal
    - accounting
    - consulting
    - marketing
  travel:
    - private_aviation
    - charter
    - luxury_travel
  events:
    - catering
    - photography
    - venues
    - entertainment

products:
  # For future merchant product listings
  # MVP: products come from Amazon/Serp
```

## Priority Matching Algorithm

```python
def match_merchants(search_intent):
    """
    Returns merchants ordered by priority for RFP notification.
    """
    category = search_intent.category
    location = search_intent.location
    
    # Layer 1: Registered merchants
    registered = Merchant.query.filter(
        Merchant.status == 'active',
        Merchant.categories.contains(category),
        Merchant.serves_location(location)
    ).order_by(
        Merchant.response_rate.desc(),  # Favor responsive merchants
        Merchant.created_at.asc()       # Tie-breaker: tenure
    ).limit(20)
    
    if len(registered) >= 5:
        return registered, skip_wattdata=True
    
    # Layer 2: WattData (if insufficient registered)
    wattdata_vendors = wattdata.query(category, location, limit=20-len(registered))
    
    return registered + wattdata_vendors, skip_wattdata=False

def display_results(bids, registered_merchant_ids):
    """
    Order results with registered merchant quotes first.
    """
    registered_bids = [b for b in bids if b.merchant_id in registered_merchant_ids]
    other_bids = [b for b in bids if b.merchant_id not in registered_merchant_ids]
    
    return registered_bids + other_bids  # Registered first, then others
```

## Source Badges

| Source | Badge | Display |
|--------|-------|---------|
| Registered Merchant | ✓ Verified Partner | Green checkmark |
| WattData Outreach | Local Vendor | Blue location pin |
| Amazon | Amazon | Amazon logo |
| Google/Serp | Web Result | Globe icon |

## Dependencies
- **Upstream**: 
  - Category taxonomy (define before launch)
  - Quote Intake (merchants use same form)
  - Email notification service
- **Downstream**: 
  - WattData Outreach (skipped if sufficient registered merchants)
  - Search results display (badge rendering)
  - Merchant dashboard

## Risks & Mitigations
- **Low merchant signup** → Outreach to vendors who submit quotes via cold outreach; incentivize registration
- **Spam registrations** → Email verification; manual review queue for suspicious patterns
- **Category mismatch** → Allow free-text category suggestions; review and expand taxonomy
- **Geographic gaps** → Show buyers when no local merchants available; encourage WattData fallback
- **Quality concerns** → Future: add reviews, verification badges, response time metrics

## Acceptance Criteria (Business Validation)
- [ ] Merchant can register with business profile (<2 min)
- [ ] Merchant receives RFP notifications for matching categories/locations
- [ ] Merchant can submit quote from notification link
- [ ] Registered merchant quotes display "Verified Partner" badge
- [ ] Registered merchant quotes appear before cold outreach quotes
- [ ] Buyer search still includes Amazon/Serp results (always)
- [ ] Merchant can update profile and notification preferences
- [ ] Merchant can view submitted quotes in dashboard

## Traceability
- **Parent PRD**: docs/prd/phase2/PRD.md
- **Product North Star**: .cfoi/branches/dev/product-north-star.md
- **Related**: prd-quote-intake.md, prd-wattdata-outreach.md

---
**Note:** This is the foundation for a preferred seller network. Future iterations add verification, reviews, subscription tiers, and merchant-initiated product listings.
