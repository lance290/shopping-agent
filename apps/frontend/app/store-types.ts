/**
 * Store types and interfaces — extracted from store.ts.
 * Pure type definitions with no runtime dependencies.
 */

export interface Offer {
  title: string;
  price: number | null;
  currency: string;
  merchant: string;
  url: string;
  image_url: string | null;
  rating: number | null;
  reviews_count: number | null;
  shipping_info: string | null;
  source: string;
  // New fields
  merchant_domain?: string;
  click_url?: string;
  match_score?: number;
  bid_id?: number;
  is_selected?: boolean;
  is_liked?: boolean;
  liked_at?: string; // ISO timestamp when liked
  comment_preview?: string;
  matched_features?: string[];
  // Vendor/service provider fields
  description?: string;
  is_service_provider?: boolean;
  vendor_email?: string;
  vendor_name?: string;
  vendor_company?: string;
  like_count?: number;
  comment_count?: number;
  outreach_status?: 'contacted' | 'quoted' | 'pending';
}

export type ProviderStatusType = 'ok' | 'error' | 'timeout' | 'exhausted' | 'rate_limited';

export interface ProviderStatusSnapshot {
  provider_id: string;
  status: ProviderStatusType;
  result_count: number;
  latency_ms?: number;
  message?: string;
}

export interface Bid {
  id: number;
  price: number | null;
  currency: string;
  item_title: string;
  item_url: string | null;
  image_url: string | null;
  source: string;
  is_selected: boolean;
  combined_score?: number | null;
  is_liked?: boolean;
  liked_at?: string | null;
  is_service_provider?: boolean;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  seller?: {
    name: string;
    domain: string | null;
    description?: string;
    tagline?: string;
  };
}

export interface Row {
  id: number;
  title: string;
  status: string;
  budget_max: number | null;
  currency: string;
  choice_factors?: string;   // JSON string
  choice_answers?: string;   // JSON string
  chat_history?: string;     // JSON string of chat messages
  bids?: Bid[];              // Persisted bids from DB
  project_id?: number | null;
  last_engaged_at?: number;  // Client-side timestamp for ordering
  is_service?: boolean;      // True if this is a service request (not a product)
  service_category?: string; // e.g., "private_aviation", "catering"
  desire_tier?: string;      // commodity, considered, service, bespoke, high_value, advisory
  selected_providers?: string; // JSON string: {"amazon": true, "serpapi": false, ...}
  ui_schema?: Record<string, unknown> | null;  // SDUI schema (JSONB from backend)
  ui_schema_version?: number;                   // 0 = no schema, increments on rebuild
}

export interface Project {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export type OfferSortMode = 'original' | 'price_asc' | 'price_desc';

// Social features
export interface CommentData {
  id: number;
  user_id: number;
  body: string;
  created_at: string;
}

export interface BidSocialData {
  bid_id: number;
  like_count: number;
  is_liked: boolean;
  comment_count: number;
  comments: CommentData[];
}

export interface ChoiceFactor {
  name: string;
  label: string;
  type: 'number' | 'select' | 'multiselect' | 'text' | 'boolean';
  options?: string[];
  required: boolean;
}
