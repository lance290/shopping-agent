/**
 * Utility functions for store operations
 */

import { Bid, Offer, Row, ChoiceFactor } from './types';

export function getOfferStableKey(offer: Offer): string {
  if (offer.bid_id) return `bid:${offer.bid_id}`;

  const extractInnerUrl = (u: string): string | null => {
    if (!u) return null;

    if (u.startsWith('/api/clickout') || u.startsWith('/api/out')) {
      try {
        const parsed = new URL(u, typeof window !== 'undefined' ? window.location.origin : 'http://localhost');
        const inner = parsed.searchParams.get('url');
        return inner ? decodeURIComponent(inner) : null;
      } catch {
        return null;
      }
    }

    if (u.startsWith('http://') || u.startsWith('https://')) return u;
    return null;
  };

  const canonical = extractInnerUrl(offer.url) || extractInnerUrl(offer.click_url || '');
  if (canonical) return `url:${canonical}`;
  if (offer.url) return `raw:${offer.url}`;
  return `fallback:${offer.title}-${offer.merchant}-${offer.price}`;
}

// Helper to convert DB Bid to Offer
export function mapBidToOffer(bid: Bid): Offer {
  const contactEmail = bid.contact_email ?? undefined;
  const itemEmail = bid.item_url?.startsWith('mailto:')
    ? bid.item_url.replace('mailto:', '')
    : undefined;
  const parsedName = bid.item_title.match(/Contact: (.*)\)/)?.[1];

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
    click_url: `/api/clickout?url=${encodeURIComponent(bid.item_url || '')}`,
    bid_id: bid.id,
    is_selected: bid.is_selected,
    is_liked: bid.is_liked,
    liked_at: bid.liked_at ?? undefined,
    is_service_provider: bid.is_service_provider === true,
    vendor_company: bid.seller?.name, // Use seller name as company for service providers
    vendor_name: bid.contact_name || parsedName, // Prefer explicit contact name
    vendor_email: contactEmail || itemEmail, // Prefer explicit email
  };
}

// Helper to parse factors
export function parseChoiceFactors(row: Row): any[] {
  if (!row.choice_factors) return [];
  try {
    const parsed = JSON.parse(row.choice_factors);
    if (Array.isArray(parsed)) return parsed;
    if (parsed && typeof parsed === 'object') {
      return Object.entries(parsed).map(([name, value]) => ({
        name,
        ...(value as Record<string, any>),
      }));
    }
    return [];
  } catch {
    return [];
  }
}

export function parseChoiceAnswers(row: Row): Record<string, any> {
  if (!row.choice_answers) return {};
  try {
    return JSON.parse(row.choice_answers);
  } catch {
    return {};
  }
}

export function shouldForceNewRow(params: {
  message: string;
  activeRowTitle?: string | null;
  aggressiveness: number;
}): boolean {
  const msg = (params.message || '').toLowerCase().trim();
  const activeTitle = (params.activeRowTitle || '').toLowerCase().trim();
  const aggressiveness = Math.max(0, Math.min(100, params.aggressiveness));

  if (!msg || !activeTitle) return false;

  if (aggressiveness < 60) return false;

  const refinementRegex = /\b(over|under|below|above|cheaper|more|less|budget|price)\b|\$\s*\d+|\b\d+\s*(usd|dollars)\b/;
  if (refinementRegex.test(msg)) return false;

  const aWords = new Set(activeTitle.split(/\s+/).filter((w) => w.length > 2));
  const mWords = msg.split(/\s+/).filter((w) => w.length > 2);
  const overlap = mWords.filter((w) => aWords.has(w)).length;
  const denom = Math.max(1, Math.min(aWords.size, mWords.length));
  const similarity = overlap / denom;

  const normalized = (aggressiveness - 60) / 40;
  const threshold = 0.1 + normalized * 0.4;
  return similarity < threshold;
}
