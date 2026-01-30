export type PriceFlexibility = 'strict' | 'flexible' | 'unknown';
export type ConditionType = 'new' | 'used' | 'refurbished';
export type FeatureValue = string | number | boolean | Array<string | number | boolean>;

export interface SearchIntent {
  product_category: string;
  taxonomy_version?: string | null;
  category_path: string[];
  product_name?: string | null;
  brand?: string | null;
  model?: string | null;
  min_price?: number | null;
  max_price?: number | null;
  price_flexibility?: PriceFlexibility | null;
  condition?: ConditionType | null;
  features: Record<string, FeatureValue>;
  keywords: string[];
  exclude_keywords: string[];
  confidence: number;
  raw_input: string;
}

export interface ExtractSearchIntentResult {
  search_intent: SearchIntent;
  source: 'llm' | 'heuristic';
  error?: string;
}
