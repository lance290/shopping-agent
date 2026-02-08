import { createGoogleGenerativeAI } from '@ai-sdk/google';
import { generateText } from 'ai';
import { z } from 'zod';
import type { ExtractSearchIntentResult, SearchIntent } from '../types';
import { GEMINI_MODEL_NAME } from '../llm';

// Use Google Gemini directly (lazy-init: env may not be loaded at import time)
const getGeminiApiKey = () => process.env.GOOGLE_GENERATIVE_AI_API_KEY || process.env.GEMINI_API_KEY || '';
let _google: ReturnType<typeof createGoogleGenerativeAI> | null = null;
function getGoogle() {
  if (!_google) {
    _google = createGoogleGenerativeAI({
      apiKey: getGeminiApiKey(),
    });
  }
  return _google;
}
const getModel = () => getGoogle()(GEMINI_MODEL_NAME);

const featureValueSchema = z.union([
  z.string(),
  z.number(),
  z.boolean(),
  z.array(z.union([z.string(), z.number(), z.boolean()])),
]);

const searchIntentSchema = z.object({
  product_category: z.string(),
  taxonomy_version: z.string().nullable().optional(),
  category_path: z.array(z.string()).default([]),
  product_name: z.string().nullable().optional(),
  brand: z.string().nullable().optional(),
  model: z.string().nullable().optional(),
  min_price: z.number().nullable().optional(),
  max_price: z.number().nullable().optional(),
  price_flexibility: z.enum(['strict', 'flexible', 'unknown']).nullable().optional(),
  condition: z.enum(['new', 'used', 'refurbished']).nullable().optional(),
  features: z.record(z.string(), featureValueSchema).default({}),
  keywords: z.array(z.string()).default([]),
  exclude_keywords: z.array(z.string()).default([]),
  confidence: z.number().min(0).max(1).default(0),
  raw_input: z.string().default(''),
});

type ExtractParams = {
  displayQuery: string;
  rowTitle?: string | null;
  projectTitle?: string | null;
  choiceAnswersJson?: string | null;
  requestSpecConstraintsJson?: string | null;
};

function parseJsonObject(value?: string | null): Record<string, any> {
  if (!value) return {};
  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function slugifyCategory(value: string): string {
  const trimmed = value.trim().toLowerCase();
  if (!trimmed) return 'unknown';
  return trimmed.replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
}

function parsePriceConstraint(text: string): { min?: number; max?: number; remaining: string } {
  const raw = (text || '').trim();
  const numberMatches = raw.match(/\$?\s*(\d+(?:\.\d+)?)/g) || [];
  const nums = numberMatches
    .map(m => Number(String(m).replace(/[^0-9.]/g, '')))
    .filter(n => Number.isFinite(n));

  let min: number | undefined;
  let max: number | undefined;
  const lower = raw.toLowerCase();

  if (nums.length >= 2 && /\b(to|-)\b/.test(lower)) {
    min = Math.min(nums[0], nums[1]);
    max = Math.max(nums[0], nums[1]);
  } else if (nums.length >= 1) {
    const n = nums[0];
    if (/(\bover\b|\babove\b|\bmore\b|\bminimum\b|\bat\s*least\b)/i.test(lower)) {
      min = n;
    } else if (/(\bunder\b|\bbelow\b|\bless\b|\bmaximum\b|\bat\s*most\b)/i.test(lower)) {
      max = n;
    } else {
      max = n;
    }
  }

  const remaining = raw
    .replace(/\$\s*\d+(?:\.\d+)?/g, '')
    .replace(/\b(over|under|below|above|more|less|at\s+least|at\s+most)\b/gi, '')
    .replace(/\b(to)\b/gi, '')
    .replace(/[-–—]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return { min, max, remaining };
}

function extractKeywords(text: string): string[] {
  const tokens = text
    .toLowerCase()
    .split(/[^a-z0-9]+/g)
    .map(token => token.trim())
    .filter(token => token.length > 1);

  return Array.from(new Set(tokens));
}

function normalizeFeatureValue(value: unknown): SearchIntent['features'][string] {
  if (Array.isArray(value)) {
    return value.map(item => String(item));
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return value;
  }
  return String(value ?? '');
}

function buildHeuristicIntent(params: ExtractParams): ExtractSearchIntentResult {
  const rawInput = params.displayQuery || params.rowTitle || '';
  const constraints = parseJsonObject(params.requestSpecConstraintsJson);
  const choices = parseJsonObject(params.choiceAnswersJson);
  const priceFromText = parsePriceConstraint(rawInput);

  const minPrice =
    typeof choices.min_price === 'number'
      ? choices.min_price
      : typeof constraints.min_price === 'number'
        ? constraints.min_price
        : priceFromText.min;
  const maxPrice =
    typeof choices.max_price === 'number'
      ? choices.max_price
      : typeof constraints.max_price === 'number'
        ? constraints.max_price
        : priceFromText.max;

  const cleanedQuery = priceFromText.remaining || rawInput;
  const productName = cleanedQuery || params.rowTitle || rawInput;
  const productCategory = slugifyCategory(productName);
  const keywords = extractKeywords(productName);

  const features: Record<string, SearchIntent['features'][string]> = {};
  Object.entries(constraints).forEach(([key, value]) => {
    features[key] = normalizeFeatureValue(value);
  });
  Object.entries(choices).forEach(([key, value]) => {
    if (key === 'min_price' || key === 'max_price') return;
    if (features[key] === undefined) {
      features[key] = normalizeFeatureValue(value);
    }
  });

  const intent: SearchIntent = {
    product_category: productCategory || 'unknown',
    taxonomy_version: 'v2',
    category_path: productCategory && productCategory !== 'unknown' ? [productCategory] : [],
    product_name: productName || null,
    brand: typeof constraints.brand === 'string' ? constraints.brand : null,
    model: typeof constraints.model === 'string' ? constraints.model : null,
    min_price: minPrice ?? null,
    max_price: maxPrice ?? null,
    price_flexibility: minPrice || maxPrice ? 'strict' : 'unknown',
    condition: null,
    features,
    keywords,
    exclude_keywords: [],
    confidence: 0.2,
    raw_input: rawInput,
  };

  return { search_intent: intent, source: 'heuristic' };
}

async function extractIntentWithLlm(params: ExtractParams): Promise<SearchIntent> {
  const prompt = `You are extracting a structured SearchIntent JSON for a procurement search.

Output JSON ONLY. No extra text.

Inputs:
- display_query: ${JSON.stringify(params.displayQuery || '')}
- row_title: ${JSON.stringify(params.rowTitle || '')}
- project_title: ${JSON.stringify(params.projectTitle || '')}
- choice_answers_json: ${JSON.stringify(params.choiceAnswersJson || '')}
- request_spec_constraints_json: ${JSON.stringify(params.requestSpecConstraintsJson || '')}

Schema:
${JSON.stringify(searchIntentSchema.shape, null, 2)}

Rules:
- product_category is required and should be a concise slug (e.g. "running_shoes").
- min_price/max_price should be numbers if present.
- features should include non-price constraints.
- keywords should be short, lower-case tokens.
- confidence should be 0-1.
`;

  const { text } = await generateText({ model: getModel(), prompt });
  const cleaned = String(text || '').replace(/```json\n?|\n?```/g, '').trim();
  const parsed = JSON.parse(cleaned);
  return searchIntentSchema.parse(parsed);
}

export async function extractSearchIntent(params: ExtractParams): Promise<ExtractSearchIntentResult> {
  if (!process.env.GOOGLE_GENERATIVE_AI_API_KEY && !process.env.GEMINI_API_KEY) {
    return buildHeuristicIntent(params);
  }

  try {
    const intent = await extractIntentWithLlm(params);
    return { search_intent: intent, source: 'llm' };
  } catch (err) {
    const fallback = buildHeuristicIntent(params);
    const message = err instanceof Error ? err.message : String(err);
    return { ...fallback, error: message };
  }
}
