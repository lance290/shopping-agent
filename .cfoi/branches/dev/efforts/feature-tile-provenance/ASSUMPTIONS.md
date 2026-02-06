# Assumptions - feature-tile-provenance

## A1: Provider raw data is limited
`NormalizedResult.raw_data` only contains `{provider_id}`. Provenance is built from structured fields (rating, shipping_info, reviews_count, match_score) rather than raw provider payloads.

## A2: Chat excerpts are optional
Many bids won't have relevant chat context. The panel gracefully handles null/empty chat_excerpts.

## A3: Provenance is append-only
Once provenance is set on a bid, subsequent updates enrich (don't strip) the data.

## A4: Service provider bids are out of scope
WattData bids are created in `routes/outreach.py`, bypass normalization, and use VendorContactModal.

## A5: No analytics tracking in this effort
Panel open tracking / click heatmaps are deferred to a follow-up effort.
