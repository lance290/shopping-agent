# Affiliate & Integration Configuration

## Affiliate Networks (Env Vars)
Set these in your deployment environment (Railway/Vercel) to activate tracking.

```bash
# Amazon Associates
# Adds ?tag=YOUR_TAG to all Amazon links
AMAZON_AFFILIATE_TAG=buyanything-20

# eBay Partner Network (EPN)
# Adds EPN tracking parameters to eBay links
EBAY_CAMPAIGN_ID=5338901234
EBAY_ROTATION_ID=711-53200-19255-0

# Skimlinks (Universal Fallback)
# Redirects all other merchant links through Skimlinks
SKIMLINKS_PUBLISHER_ID=123456X789012
```

## Social Features
- Likes, Comments, Shares work out of the box (persisted to Postgres).
- No external API keys needed.

## Quote Intent Tracking
- Anonymous quote clicks are logged to backend logs.
- Search: `grep "QuoteIntent" apps/backend/logs/app.log` (or Railway logs).
- Format: `[QuoteIntent] query='caterer' vendor='Local Chef' slug='local-chef-123' ip_hash='a1b2c3...'`

## Demo Scenarios

### Scenario A: Commodity Retail ("Roblox gift cards")
1. Open incognito → `http://localhost:3000/`
2. Search "Roblox gift cards $100"
3. Result: Amazon/eBay/Google Shopping cards appear
4. Click "Buy" → redirects via `/api/out` → lands on retailer
5. **Success**: User buys product, we get affiliate credit.

### Scenario B: Vendor Directory ("Caterer")
1. Open incognito → `http://localhost:3000/`
2. Search "caterer for 50 people"
3. Result: Vendor cards appear (sourced from vendor directory via vector search)
4. Click "Request Quote"
5. Result: Opens vendor website (if available) or `mailto:` with pre-filled template
6. **Success**: User connects with vendor, backend logs intent.

### Scenario C: Viral Loop
1. Show `/quote/[token]` page (public access)
2. Explain: Vendor receives outreach → clicks link → sees "What do YOU need to buy?"
3. Explain: Vendor becomes buyer → uses search → cycle repeats.
