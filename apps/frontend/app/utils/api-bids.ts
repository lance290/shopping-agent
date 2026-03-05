/**
 * Bid/provenance API types and functions.
 */
import { fetchWithAuth } from './api-core';

// Provenance types for BidWithProvenance
export interface ProvenanceData {
  product_info?: ProductInfo | null;
  matched_features?: string[];
  chat_excerpts?: ChatExcerpt[];
}

export interface ProductInfo {
  title?: string;
  brand?: string;
  specs?: Record<string, unknown>;
  [key: string]: unknown; // Allow additional fields
}

export interface ChatExcerpt {
  role: string;
  content: string;
}

export interface BidWithProvenance {
  id: number;
  price: number;
  currency: string;
  item_title: string;
  item_url: string | null;
  image_url: string | null;
  source: string;
  is_selected: boolean;
  seller?: {
    name: string;
    domain: string | null;
  };
  provenance?: string | null;
  provenance_data?: ProvenanceData | null;
  product_info?: ProductInfo | null;
  matched_features?: string[] | null;
  chat_excerpts?: ChatExcerpt[] | null;
}

// Helper: Fetch bid with provenance data
export const fetchBidWithProvenance = async (bidId: number): Promise<BidWithProvenance | null> => {
  try {
    const res = await fetchWithAuth(`/api/bids/${bidId}?include_provenance=true`, {
      signal: AbortSignal.timeout(5000), // 5 second timeout
    });

    if (!res.ok) {
      if (res.status === 404) {
        console.error('[API] Bid not found:', bidId);
        return null;
      }
      console.error('[API] Fetch bid with provenance failed:', res.status);
      return null;
    }

    const data = await res.json();
    return data as BidWithProvenance;
  } catch (err) {
    if (err instanceof Error && err.name === 'TimeoutError') {
      console.error('[API] Fetch bid with provenance timeout:', bidId);
    } else {
      console.error('[API] Fetch bid with provenance error:', err);
    }
    return null;
  }
};
