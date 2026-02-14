/**
 * Centralized type definitions for Shopping Agent
 *
 * This file consolidates all type definitions to eliminate 'any' types
 * and provide better type safety throughout the application.
 */

// ============================================================================
// CHOICE FACTORS & ANSWERS
// ============================================================================

export type ChoiceFactorType =
  | 'text'
  | 'number'
  | 'boolean'
  | 'select'
  | 'multiselect'
  | 'price_range';

export interface ChoiceFactor {
  name: string;
  type: ChoiceFactorType;
  label?: string;
  options?: string[];
  required?: boolean;
  description?: string;
}

export type ChoiceAnswerValue = string | number | boolean | string[];

export type ChoiceAnswers = Record<string, ChoiceAnswerValue>;

// ============================================================================
// VENDOR & SERVICE PROVIDER
// ============================================================================

export interface VendorData {
  title?: string;
  vendor_company?: string;
  vendor_name?: string;
  vendor_email?: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  merchant?: string;
  merchant_domain?: string;
  price?: number;
  currency?: string;
  url?: string;
  image_url?: string | null;
  source?: string;
}

// ============================================================================
// SEARCH & API RESPONSES
// ============================================================================

export interface RawSearchResult {
  title?: string;
  price?: number | string;
  currency?: string;
  merchant?: string;
  url?: string;
  image_url?: string | null;
  rating?: number | null;
  reviews_count?: number | null;
  shipping_info?: string | null;
  source?: string;
  merchant_domain?: string;
  click_url?: string;
  match_score?: number;
  bid_id?: number;
  is_selected?: boolean;
  is_liked?: boolean;
  liked_at?: string;
  is_service_provider?: boolean;
  vendor_email?: string;
  vendor_name?: string;
  vendor_company?: string;
  like_count?: number;
  comment_count?: number;
}

export interface SearchRequestBody {
  rowId?: number;
  query?: string;
  providers?: string[];
}

// ============================================================================
// LIKES
// ============================================================================

export interface Like {
  id: number;
  bid_id: number;
  row_id: number;
  user_id: number;
  created_at: string;
}

export interface LikeToggleResponse {
  is_liked: boolean;
  like_count?: number;
  bid_id: number;
}

// ============================================================================
// DIAGNOSTICS
// ============================================================================

export interface DiagnosticDetails {
  [key: string]: unknown;
}

export interface DiagnosticEntry {
  timestamp: number;
  category: string;
  message: string;
  details?: DiagnosticDetails;
  severity?: 'info' | 'warn' | 'error';
}

// ============================================================================
// SHARE RESOURCES
// ============================================================================

export type ShareResourceType = 'project' | 'row' | 'tile' | 'bid';

// Use discriminated union for type-safe resource data
export type ShareResourceData =
  | { type: 'row'; data: import('../store').Row }
  | { type: 'project'; data: import('../store').Project }
  | { type: 'bid'; data: import('../store').Bid }
  | { type: 'tile'; data: unknown };

// ============================================================================
// PRODUCT INFO & SPECS
// ============================================================================

export type ProductSpecValue = string | number | boolean;

export interface ProductSpecs {
  [key: string]: ProductSpecValue;
}

export interface ProductInfo {
  title?: string;
  brand?: string;
  specs?: ProductSpecs;
  // Specific optional fields instead of index signature
  model?: string;
  sku?: string;
  description?: string;
  category?: string;
}

// ============================================================================
// CHAT & MESSAGES
// ============================================================================

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: number;
}

// ============================================================================
// OUTREACH
// ============================================================================

export interface OutreachData {
  email?: string;
  phone?: string;
  preferred_contact?: 'email' | 'phone';
  message?: string;
  vendors?: string[];
  sent_at?: string;
}

// ============================================================================
// ERROR TYPES
// ============================================================================

export interface ApiError {
  error: string;
  message: string;
  detail?: string;
  status?: number;
}

export class ApiException extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string
  ) {
    super(message);
    this.name = 'ApiException';
  }
}

// ============================================================================
// UTILITY TYPES
// ============================================================================

/**
 * Makes all properties of T required and non-nullable
 */
export type Required<T> = {
  [P in keyof T]-?: NonNullable<T[P]>;
};

/**
 * Extract non-null values from a type
 */
export type NonNullableFields<T> = {
  [P in keyof T]: NonNullable<T[P]>;
};

/**
 * JSON-safe type (can be serialized to JSON)
 */
export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

/**
 * Type guard for checking if a value is a valid JSON value
 */
export function isJsonValue(value: unknown): value is JsonValue {
  if (value === null) return true;

  const type = typeof value;
  if (type === 'string' || type === 'number' || type === 'boolean') {
    return true;
  }

  if (Array.isArray(value)) {
    return value.every(isJsonValue);
  }

  if (type === 'object') {
    return Object.values(value as object).every(isJsonValue);
  }

  return false;
}
