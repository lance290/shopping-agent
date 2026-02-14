/**
 * Shared types used across all stores
 */

export interface Offer {
  title: string;
  price: number;
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
  // Vendor/service provider fields
  is_service_provider?: boolean;
  vendor_email?: string;
  vendor_name?: string;
  vendor_company?: string;
  like_count?: number;
  comment_count?: number;
}

export interface Bid {
  id: number;
  price: number;
  currency: string;
  item_title: string;
  item_url: string | null;
  image_url: string | null;
  source: string;
  is_selected: boolean;
  is_liked?: boolean;
  liked_at?: string | null;
  is_service_provider?: boolean;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  seller?: {
    name: string;
    domain: string | null;
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
}

export interface Project {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export type ProviderStatusType = 'ok' | 'error' | 'timeout' | 'exhausted' | 'rate_limited';

export interface ProviderStatusSnapshot {
  provider_id: string;
  status: ProviderStatusType;
  result_count: number;
  latency_ms?: number;
  message?: string;
}

export type OfferSortMode = 'original' | 'price_asc' | 'price_desc';

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
