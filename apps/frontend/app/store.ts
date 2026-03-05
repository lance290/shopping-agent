// Types extracted to store-types.ts — re-exported for backward compatibility
export type {
  Offer,
  ProviderStatusType,
  ProviderStatusSnapshot,
  Bid,
  Row,
  Project,
  OfferSortMode,
  CommentData,
  BidSocialData,
  ChoiceFactor,
} from './store-types';

import type { Offer, Bid, Row, ChoiceFactor } from './store-types';

// Helper to convert DB Bid to Offer
export function mapBidToOffer(bid: Bid, rowId?: number): Offer {
  const contactEmail = bid.contact_email ?? undefined;
  const itemEmail = bid.item_url?.startsWith('mailto:')
    ? bid.item_url.replace('mailto:', '')
    : undefined;
  const parsedName = bid.item_title.match(/Contact: (.*)\)/)?.[1];
  
  let parsedProvenance: Record<string, unknown> = {};
  if (typeof (bid as unknown as Record<string, unknown>).provenance === 'string' && (bid as unknown as Record<string, unknown>).provenance) {
    try {
      parsedProvenance = JSON.parse((bid as unknown as Record<string, unknown>).provenance as string);
    } catch { }
  }
  
  let clickUrl = `/api/out?url=${encodeURIComponent(bid.item_url || '')}&bid_id=${bid.id}`;
  if (rowId) clickUrl += `&row_id=${rowId}`;
  if (bid.source) clickUrl += `&source=${encodeURIComponent(bid.source)}`;

  return {
    // Extract contact name if stored in title, and clean up the displayed title
    title: bid.item_title.replace(/ \(Contact: .*\)/, ''),
    price: bid.price,
    currency: bid.currency,
    merchant: bid.seller?.name || 'Unknown',
    url: bid.item_url || '#',
    image_url: bid.image_url,
    rating: null, // Not persisted yet
    reviews_count: null,
    shipping_info: null,
    source: bid.source,
    merchant_domain: bid.seller?.domain || undefined,
    click_url: clickUrl,
    match_score: typeof bid.combined_score === 'number' ? bid.combined_score : undefined,
    bid_id: bid.id,
    is_selected: bid.is_selected,
    is_liked: bid.is_liked,
    liked_at: bid.liked_at ?? undefined,
    is_service_provider: bid.is_service_provider === true,
    vendor_company: bid.seller?.name, // Use seller name as company for service providers
    vendor_name: bid.contact_name || parsedName, // Prefer explicit contact name
    vendor_email: contactEmail || itemEmail, // Prefer explicit email
    description: bid.seller?.description || bid.seller?.tagline || undefined,
    matched_features: Array.isArray(parsedProvenance?.matched_features)
      ? parsedProvenance.matched_features
      : (Array.isArray((bid as unknown as Record<string, unknown>).matched_features) ? (bid as unknown as Record<string, unknown>).matched_features as string[] : []),
  };
}

// Helper to parse factors
export function parseChoiceFactors(row: Row): ChoiceFactor[] {
  if (!row.choice_factors) return [];
  try {
    const parsed = JSON.parse(row.choice_factors);
    if (Array.isArray(parsed)) return parsed;
    if (parsed !== null && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return Object.entries(parsed).map(([name, value]) => ({
        name,
        ...(value as Record<string, unknown>),
      })) as ChoiceFactor[];
    }
    return [];
  } catch {
    return [];
  }
}

export function parseChoiceAnswers(row: Row): Record<string, unknown> {
  if (!row.choice_answers) return {};
  try {
    const parsed = JSON.parse(row.choice_answers);
    if (parsed !== null && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    // Ignore parse errors
  }
  return {};
}

export { useShoppingStore } from './store-state';
