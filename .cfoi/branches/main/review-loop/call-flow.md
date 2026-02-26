# Call Flow - eBay Integration & Webhook

## Webhook Flow
[eBay] -> GET /api/webhooks/ebay/account-deletion -> `ebay_account_deletion_webhook` (routes/webhooks.py)
  -> Calculates SHA-256 hash using `challenge_code`, `verification_token`, `endpoint`
  -> Returns `challengeResponse` to eBay

[eBay] -> POST /api/webhooks/ebay/account-deletion -> `ebay_account_deletion_webhook` (routes/webhooks.py)
  -> Acknowledges receipt with 200 OK (no user data to delete yet)

## Sourcing Flow
[Client] -> search -> `SourcingRepository.search` -> `EbayBrowseProvider.search` (sourcing/repository.py)
  -> `_get_access_token` (fetches OAuth token via client_credentials grant)
  -> GET /buy/browse/v1/item_summary/search
  -> Parses response into `SearchResult` objects

## Integration Points to Verify
- [ ] Token generation in `EbayBrowseProvider`: Does the scope match requirements?
- [ ] Webhook endpoint: Does `exact_endpoint` exactly match what eBay calls?
- [ ] Webhook hash: Is the concatenation order exactly `challengeCode` + `verificationToken` + `endpoint`?
