import { createOpenAI } from '@ai-sdk/openai';
import { streamText, generateText } from 'ai';
import { z } from 'zod';

// Use OpenRouter for LLM calls
const openrouter = createOpenAI({
  baseURL: 'https://openrouter.ai/api/v1',
  apiKey: process.env.OPENROUTER_API_KEY,
});

export const GEMINI_MODEL_NAME = 'google/gemini-3-flash-preview';
const model = openrouter(GEMINI_MODEL_NAME);
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

const chatPlanSchema = z.object({
  assistant_message: z.string().default(''),
  actions: z
    .array(
      z.discriminatedUnion('type', [
        z.object({
          type: z.literal('create_row'),
          title: z.string(),
          project_id: z.number().nullable().optional(),
          constraints: z.record(z.string(), z.any()).optional(),
          min_price: z.number().optional(),
          max_price: z.number().optional(),
          providers: z.array(z.string()).optional(),
          search_query: z.string().optional(),
        }),
        z.object({
          type: z.literal('update_row'),
          row_id: z.number(),
          title: z.string().optional(),
          constraints: z.record(z.string(), z.any()).optional(),
          min_price: z.number().optional(),
          max_price: z.number().optional(),
          providers: z.array(z.string()).optional(),
          search_query: z.string().optional(),
        }),
        z.object({
          type: z.literal('search'),
          row_id: z.number(),
          query: z.string(),
          providers: z.array(z.string()).optional(),
        }),
        z.object({
          type: z.literal('vendor_outreach'),
          row_id: z.number(),
          category: z.string(),
          vendor_suggestions: z.array(z.string()).optional(),
        }),
      ])
    )
    .default([]),
});

export type ChatPlan = z.infer<typeof chatPlanSchema>;

// Quick title extraction - fast, minimal prompt for instant row creation
export async function extractTitleQuick(userMessage: string): Promise<{ title: string; is_service: boolean; category?: string }> {
  const prompt = `Extract the item/service title from this shopping request. Be concise.

User: "${userMessage}"

Return JSON: {"title": "...", "is_service": true/false, "category": "..." (only if service)}

Examples:
- "I need a laptop for gaming under $1000" -> {"title": "Gaming laptop", "is_service": false}
- "Find me a private jet from NYC to LA" -> {"title": "Private jet NYC to LA", "is_service": true, "category": "private_aviation"}
- "Looking for a plumber in Denver" -> {"title": "Plumber in Denver", "is_service": true, "category": "plumbing"}

JSON only:`;

  try {
    const { text } = await generateText({ model, prompt });
    const cleaned = text.replace(/```json\n?|\n?```/g, '').trim();
    return JSON.parse(cleaned);
  } catch (e) {
    // Fallback: use first 50 chars of user message
    return { title: userMessage.slice(0, 50), is_service: false };
  }
}

// Generic service clarification system - works for any service type
export interface ServiceConstraints {
  extracted: Record<string, unknown>;
  missing_required: string[];
  clarifying_question?: string;
  is_complete: boolean;
}

export async function extractServiceConstraints(
  userMessage: string, 
  serviceType: string,
  existingConstraints?: Record<string, unknown>
): Promise<ServiceConstraints> {
  const existingText = existingConstraints && Object.keys(existingConstraints).length > 0
    ? `\n\nAlready collected: ${JSON.stringify(existingConstraints)}`
    : '';

  const prompt = `You are analyzing a service request to determine what information is needed.

Service type: "${serviceType}"
User message: "${userMessage}"${existingText}

Your task:
1. Extract any concrete details from the user's message (dates, locations, quantities, preferences, etc.)
2. Determine what essential information is still missing to fulfill this request
3. If anything is missing, write a natural, friendly clarifying question

Return JSON:
{
  "extracted": {
    // key-value pairs of info found in the message
    // Use snake_case keys like "departure_date", "num_guests", "location", etc.
  },
  "missing_required": [
    // Array of plain English descriptions of what's still needed
    // e.g., "departure date", "number of guests", "preferred location"
  ],
  "clarifying_question": "A natural question to ask for the missing info (or null if complete)",
  "is_complete": true/false
}

Examples:
- Private jet, "from SAN to EWR" -> extracted: {from_airport: "SAN", to_airport: "EWR"}, missing: ["departure date", "number of passengers"]
- Catering, "party for 50 on Saturday" -> extracted: {num_guests: 50, event_date: "Saturday"}, missing: ["venue/delivery location", "dietary restrictions"]
- Photography, "wedding next June" -> extracted: {event_type: "wedding", event_month: "June"}, missing: ["exact date", "venue location", "hours needed"]

Be practical - only ask for info that's truly essential to get a quote. Don't over-ask.

JSON only:`;

  try {
    const { text } = await generateText({ model, prompt });
    const cleaned = text.replace(/```json\n?|\n?```/g, '').trim();
    const parsed = JSON.parse(cleaned);
    
    return {
      extracted: parsed.extracted || {},
      missing_required: Array.isArray(parsed.missing_required) ? parsed.missing_required : [],
      clarifying_question: parsed.clarifying_question || undefined,
      is_complete: parsed.is_complete ?? (parsed.missing_required?.length === 0),
    };
  } catch (e) {
    console.error('Failed to extract service constraints:', e);
    return { 
      extracted: {}, 
      missing_required: [], 
      is_complete: true // Don't block on extraction failure
    };
  }
}

// Check if user is switching context (asking about something completely different)
export async function isContextSwitch(
  userMessage: string, 
  currentServiceType: string
): Promise<boolean> {
  const prompt = `Is this user message continuing a conversation about "${currentServiceType}", or are they switching to a completely different topic?

User message: "${userMessage}"

Return JSON: {"is_switch": true/false, "reason": "brief explanation"}

Examples:
- currentServiceType: "private jet charter", message: "Feb 13, 7 people" -> {"is_switch": false, "reason": "providing requested details"}
- currentServiceType: "private jet charter", message: "actually, let's look for dinner reservations" -> {"is_switch": true, "reason": "explicitly changing topic"}
- currentServiceType: "catering", message: "vegetarian options please" -> {"is_switch": false, "reason": "adding dietary info to catering request"}

JSON only:`;

  try {
    const { text } = await generateText({ model, prompt });
    const cleaned = text.replace(/```json\n?|\n?```/g, '').trim();
    const parsed = JSON.parse(cleaned);
    return parsed.is_switch === true;
  } catch (e) {
    return false; // Default to continuing context on error
  }
}

// Generate optimized search query for providers
export async function generateSearchQuery(title: string, constraints?: Record<string, any>): Promise<string> {
  const constraintsText = constraints ? ` with constraints: ${JSON.stringify(constraints)}` : '';
  const prompt = `Generate an optimized search query for shopping providers (Amazon, Google Shopping, etc).

Item: "${title}"${constraintsText}

Return ONLY the search query string, no quotes, no explanation. Keep it concise (max 8 words).`;

  try {
    const { text } = await generateText({ model, prompt });
    return text.trim().replace(/^["']|["']$/g, '');
  } catch (e) {
    return title;
  }
}

export async function generateChatPlan(input: {
  messages: any[];
  activeRowId?: number | null;
  projectId?: number | null;
  activeRowTitle?: string | null;
  projectTitle?: string | null;
}): Promise<ChatPlan> {
  if (!process.env.OPENROUTER_API_KEY) {
    throw new Error('LLM not configured - OPENROUTER_API_KEY required');
  }

  const lastUserMessage = Array.isArray(input.messages)
    ? [...input.messages].reverse().find((m: any) => m?.role === 'user')
    : null;

  const userText =
    typeof lastUserMessage?.content === 'string'
      ? lastUserMessage.content
      : typeof lastUserMessage?.content?.text === 'string'
        ? lastUserMessage.content.text
        : '';

  const activeRowId = input.activeRowId ?? null;
  const activeRowTitle = (input.activeRowTitle || '').trim();
  const projectTitle = (input.projectTitle || '').trim();

  const prompt = `You are the planner for a shopping/procurement app.

You MUST output a SINGLE JSON object and nothing else.

Inputs:
- User message: ${JSON.stringify(userText || '')}
- Active row id: ${activeRowId === null ? 'null' : String(activeRowId)}
- Active row title (if any): ${JSON.stringify(activeRowTitle)}
- Project title (if any): ${JSON.stringify(projectTitle)}

Your job:
- Produce an assistant message for the user.
- Produce a list of backend actions to execute.

Hard requirements:
- NO tool-calling. Only output JSON.
- NO explanations, markdown, or extra text.
- Always choose exactly one of:
  - create_row (for new item requests)
  - update_row (for refinements when active_row_id is present)
  - search (only if you are NOT changing the row, but want to refresh results)

Rules:
- If active_row_id is present and the user is refining constraints (price/color/size/etc), use update_row with row_id=active_row_id.
- For any update_row or create_row, include constraints as a key-value JSON object when the user expressed constraints (EXCEPT price).
- Price constraints MUST be expressed ONLY via min_price/max_price numeric fields:
  - "over $50" -> min_price: 50
  - "under $50" -> max_price: 50
  - "$25-$75" -> min_price: 25 and max_price: 75
  - Do NOT put price info into "constraints".
- If you create_row or update_row, you SHOULD also include either:
  - search_query (preferred) on that same action, OR
  - a follow-up search action.
- For SERVICE requests (private jets, roofing, HVAC, contractors, catering, etc.) where the user needs quotes from vendors rather than products to buy:
  - Use vendor_outreach action instead of search
  - Set category to: "private_aviation", "roofing", "hvac", "catering", etc.
  - Optionally suggest vendor names the user might want to contact
  - Say something like "Let me reach out to vendors for quotes..."

Schema:
{
  "assistant_message": string,
  "actions": [
    {
      "type": "create_row",
      "title": string,
      "project_id"?: number|null,
      "constraints"?: object,
      "min_price"?: number,
      "max_price"?: number,
      "providers"?: string[],
      "search_query"?: string
    }
    | {
      "type": "update_row",
      "row_id": number,
      "title"?: string,
      "constraints"?: object,
      "min_price"?: number,
      "max_price"?: number,
      "providers"?: string[],
      "search_query"?: string
    }
    | {
      "type": "search",
      "row_id": number,
      "query": string,
      "providers"?: string[]
    }
    | {
      "type": "vendor_outreach",
      "row_id": number,
      "category": string,
      "vendor_suggestions"?: string[]
    }
  ]
}`;

  const { text } = await generateText({ model, prompt });
  const cleaned = String(text || '').replace(/```json\n?|\n?```/g, '').trim();
  const parsed = JSON.parse(cleaned);
  return chatPlanSchema.parse(parsed);
}

export async function triageProviderQuery(params: {
  displayQuery: string;
  rowTitle?: string | null;
  projectTitle?: string | null;
  choiceAnswersJson?: string | null;
  requestSpecConstraintsJson?: string | null;
}): Promise<string> {
  const displayQuery = (params.displayQuery || '').trim();
  const rowTitle = (params.rowTitle || '').trim();
  const projectTitle = (params.projectTitle || '').trim();

  const heuristic = () => {
    const text = displayQuery || rowTitle;
    if (!text) return '';

    let q = text;
    q = q.replace(/\$\s*\d+(?:\.\d+)?/g, '');
    q = q.replace(/\b(over|under|below|above)\s*\$?\s*\d+(?:\.\d+)?\b/gi, '');
    q = q.replace(/\b\d+\s*\+\b/g, '');
    q = q.replace(/\$\s*\d+(?:\.\d+)?\s*(and\s*up|\+|or\s*more|and\s*above)\b/gi, '');
    q = q.replace(/\b(and\s*up|or\s*more|and\s*above)\b/gi, '');
    q = q.replace(/[()]/g, ' ');
    q = q.replace(/\s+/g, ' ').trim();
    return q;
  };

  if (!process.env.OPENROUTER_API_KEY) {
    return heuristic();
  }

  const prompt = `You are generating a concise search query to send to shopping providers (Amazon/Google Shopping/eBay).

Input:
- Display query (what user sees): ${JSON.stringify(displayQuery)}
- Row title: ${JSON.stringify(rowTitle)}
- Project title: ${JSON.stringify(projectTitle)}
- choice_answers JSON (may include min_price/max_price): ${JSON.stringify(params.choiceAnswersJson || '')}
- request_spec.constraints JSON: ${JSON.stringify(params.requestSpecConstraintsJson || '')}

Goal:
- Output a provider_query that maximizes product relevance.
- Do NOT include price phrases like "$50 and up", "over $50", "under $50", "50+", "or more" in provider_query.
- Keep it short (2-6 words), only the core product/category.
- If the project title helps disambiguate meaning, use it ONLY as context to choose the right meaning; do not include project title in provider_query.

Return JSON ONLY:
{"provider_query":"..."}`;

  try {
    const { text } = await generateText({ model, prompt });
    const cleaned = text.replace(/```json\n?|\n?```/g, '').trim();
    const parsed = JSON.parse(cleaned);
    const q = typeof parsed?.provider_query === 'string' ? parsed.provider_query.trim() : '';
    return q || heuristic();
  } catch {
    return heuristic();
  }
}

async function fetchJsonWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number
): Promise<{ ok: boolean; status: number; data: any; text: string }> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...init, signal: controller.signal });
    const text = await res.text();
    let data: any = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = null;
    }
    return { ok: res.ok, status: res.status, data, text };
  } finally {
    clearTimeout(timeout);
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function isRetryableFetchError(err: unknown): boolean {
  if (!err) return false;
  const name = (err as any)?.name;
  if (name === 'AbortError') return true;
  const message = (err as any)?.message;
  if (typeof message === 'string' && message.toLowerCase().includes('fetch failed')) return true;
  if (typeof message === 'string' && message.toLowerCase().includes('connect timeout')) return true;
  return false;
}

async function fetchJsonWithTimeoutRetry(
  url: string,
  init: RequestInit,
  timeoutMs: number,
  retries: number,
  retryDelayMs: number
): Promise<{ ok: boolean; status: number; data: any; text: string }> {
  let lastErr: unknown = null;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await fetchJsonWithTimeout(url, init, timeoutMs);
    } catch (err) {
      lastErr = err;
      if (attempt >= retries || !isRetryableFetchError(err)) {
        throw err;
      }
      await sleep(retryDelayMs);
    }
  }
  throw lastErr;
}

const constraintValueSchema = z.union([
  z.string(),
  z.number(),
  z.boolean(),
  z.array(z.union([z.string(), z.number(), z.boolean()])),
]);

function normalizeConstraintValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map(v => String(v)).join(', ');
  }
  return String(value);
}

// Helper to generate and save choice factors
export async function generateAndSaveChoiceFactors(itemDescription: string, rowId: number, authorization?: string, existingConstraints?: Record<string, any>) {
  const constraintsText = existingConstraints ? `\nExisting constraints: ${JSON.stringify(existingConstraints)}` : '';
  
  const factorPrompt = `You are determining the key product specifications (attributes) for purchasing: "${itemDescription}"${constraintsText}

Return a JSON array of 3-6 key specifications. Each spec should have:
- name: lowercase_snake_case identifier (MUST match keys in existing constraints if present)
- label: Human-readable label (e.g. "Screen Size", "Budget")
- type: "number" | "select" | "text" | "boolean"
- options: array of strings (only for "select" type)
- required: boolean

Example for "laptop":
[
  {"name": "budget", "label": "Max Budget", "type": "number", "required": true},
  {"name": "primary_use", "label": "Primary Use", "type": "select", "options": ["gaming", "work", "school", "general"], "required": true},
  {"name": "screen_size", "label": "Screen Size", "type": "select", "options": ["13 inch", "15 inch", "17 inch"], "required": false}
]

Example for "private jet charter" or any flight/travel service:
[
  {"name": "from_airport", "label": "Departure Airport", "type": "text", "required": true},
  {"name": "to_airport", "label": "Arrival Airport", "type": "text", "required": true},
  {"name": "departure_date", "label": "Departure Date", "type": "text", "required": true},
  {"name": "passengers", "label": "Passengers", "type": "number", "required": true},
  {"name": "time_earliest", "label": "Earliest Departure", "type": "text", "required": false},
  {"name": "time_latest", "label": "Latest Departure", "type": "text", "required": false}
]

IMPORTANT: If "Existing constraints" are provided, you MUST include a spec definition for each constraint key so the UI can display it.

Return ONLY the JSON array, no explanation.`;

  try {
    const { text } = await generateText({
      model,
      prompt: factorPrompt,
    });
    
    let factors;
    try {
      // Handle potential markdown code blocks in response
      const cleanedText = text.replace(/```json\n?|\n?```/g, '').trim();
      factors = JSON.parse(cleanedText);
    } catch (e) {
      console.error("Failed to parse factors JSON:", text);
      return null;
    }

    if (Array.isArray(factors)) {
      factors = factors.map((f: any) => {
        if (f?.type === 'select') {
          const options = Array.isArray(f.options)
            ? f.options.filter((o: any) => typeof o === 'string' && o.trim().length > 0)
            : [];

          if (options.length === 0) {
            const { options: _options, ...rest } = f;
            return { ...rest, type: 'text' };
          }

          return { ...f, options };
        }

        return f;
      });
    }
    
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (authorization) {
      headers['Authorization'] = authorization;
    }
    
    await fetchJsonWithTimeoutRetry(
      `${BACKEND_URL}/rows/${rowId}`,
      {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ choice_factors: JSON.stringify(factors) }),
      },
      20000,
      1,
      500
    );
    
    return factors;
  } catch (e) {
    console.error("Error generating factors:", e);
    return null;
  }
}

export const chatHandler = async (
  messages: any[],
  authorization?: string,
  activeRowId?: number | null,
  projectId?: number | null
): Promise<any> => {
  // Build context about active row for the LLM
  const activeRowInstruction = activeRowId 
    ? `\n\n⚠️ CRITICAL: There is an ACTIVE ROW with ID ${activeRowId}. 
For ANY refinement (price, color, size, style changes), you MUST:
1. Call updateRow with rowId=${activeRowId} first
2. Then call searchListings with rowId=${activeRowId}
DO NOT call createRow - the row already exists!`
    : '\n\nNo active row. For new items, call createRow first.';

  return streamText({
    model,
    messages,
    system: `You are a procurement agent. Help users find items and manage their procurement board.

⚠️ CRITICAL RULES - FOLLOW EXACTLY:

1. REFINEMENTS (user adds constraints to existing search):
   - Examples: "under $50", "only red ones", "XXL", "make it blue", "cheaper", "different color"
   - These are NOT new items - they modify the current search
   - You MUST call updateRow FIRST, then searchListings
   - NEVER call createRow for refinements

2. NEW ITEMS (user asks for completely different product):
   - Examples: "I need Montana State shirts", "find me a laptop", "search for headphones"
   - Call createRow ONCE. This will automatically generate choice factors.
   - Then call searchListings with the new row's ID immediately if the user provided enough detail.

3. When calling updateRow:
   - Build a NEW title with ALL constraints: "red Montana State shirts under $50 XXL"
   - Include constraints object: {"color":"red", "max_price":"50", "size":"XXL"}

WORKFLOW FOR NEW REQUESTS:
1. When user asks for a new item, call createRow first.
2. Specifications will be generated automatically based on your item description.
3. If the user's request was specific (e.g. "I need a blue hoodie under $50"), the system will pre-fill these values.
4. Proceed to searchListings.

WORKFLOW FOR REFINEMENTS:
1. If user changes requirements, call updateRow then searchListings.
2. The UI handles specific field edits, you handle chat-based refinements.

REFINEMENT DETECTION:
- "under $X" / "less than" / "cheaper" → REFINEMENT (price)
- "red/blue/green/only X color" → REFINEMENT (color)  
- "size X" / "XXL/large/small" → REFINEMENT (size)
- "actually" / "instead" / "change to" → REFINEMENT
- Short phrases without product names → likely REFINEMENT
${activeRowInstruction}`,
    tools: {
      createRow: {
        description: 'Create a NEW procurement row for a COMPLETELY DIFFERENT item. DO NOT use this for refinements like price/color/size changes - use updateRow instead.',
        inputSchema: z.object({
          item: z.string().describe('The name of the NEW item to buy (not a refinement of existing search)'),
          constraints: z.record(z.string(), constraintValueSchema).optional().describe('Initial constraints for the new item'),
        }),
        execute: async (input: { item: string; constraints?: Record<string, unknown> }) => {
          try {
            // Convert all constraint values to strings
            const normalizedConstraints: Record<string, string> = {};
            if (input.constraints) {
              for (const [key, value] of Object.entries(input.constraints)) {
                normalizedConstraints[key] = normalizeConstraintValue(value);
              }
            }
            
            const headers: Record<string, string> = { 'Content-Type': 'application/json' };
            if (authorization) {
              headers['Authorization'] = authorization;
            }
            
            const result = await fetchJsonWithTimeoutRetry(
              `${BACKEND_URL}/rows`,
              {
                method: 'POST',
                headers,
                body: JSON.stringify({
                  title: input.item,
                  status: 'sourcing',
                  project_id: projectId || undefined,
                  request_spec: {
                    item_name: input.item,
                    constraints: JSON.stringify(normalizedConstraints)
                  },
                  choice_answers: JSON.stringify(normalizedConstraints)
                }),
              },
              20000,
              1,
              500
            );

            if (!result.ok) {
              return {
                status: 'error',
                code: result.status,
                message: result.data?.message || result.text || 'Backend request failed',
              };
            }

            const data = result.data as any;
            if (!data?.id) {
              return {
                status: 'error',
                code: 502,
                message: 'Backend returned unexpected response for createRow',
                data,
              };
            }
            
            // Fire-and-forget choice factor generation to avoid blocking the UI
            // The frontend will poll for these updates
            generateAndSaveChoiceFactors(input.item, data.id, authorization, normalizedConstraints).catch(err => {
              console.error(`[Background] Failed to generate factors for row ${data.id}:`, err);
            });
            
            // Auto-trigger search since AI SDK v6 doesn't support multi-step tool calls
            const searchHeaders: Record<string, string> = { 'Content-Type': 'application/json' };
            if (authorization) {
              searchHeaders['Authorization'] = authorization;
            }
            
            const searchResult = await fetchJsonWithTimeoutRetry(
              `${BACKEND_URL}/rows/${data.id}/search`,
              {
                method: 'POST',
                headers: searchHeaders,
                body: JSON.stringify({ query: input.item }),
              },
              30000,
              1,
              500
            );
            
            const searchCount = searchResult.ok && searchResult.data?.results 
              ? searchResult.data.results.length 
              : 0;
            
            return { 
              status: 'row_created_and_searched', 
              rowId: data.id,
              searchCount,
              message: searchCount > 0 
                ? `Created row and found ${searchCount} results for "${input.item}".`
                : `Created row for "${input.item}". Search returned no results - try refining your query.`,
              data: { ...data, choice_factors: null } 
            };
          } catch (e) {
            const msg = e instanceof Error ? e.message : String(e);
            return { status: 'error', message: msg };
          }
        },
      },
      updateRow: {
        description: 'UPDATE an existing row when user refines their search (price, color, size, etc). ALWAYS use this instead of createRow for refinements. Call this BEFORE searchListings.',
        inputSchema: z.object({
          rowId: z.number().describe('The ID of the active row to update - use the CURRENT ACTIVE ROW ID from system context'),
          title: z.string().describe('The NEW title with ALL accumulated constraints, e.g. "red Montana State shirts under $50"'),
          constraints: z.record(z.string(), constraintValueSchema).optional().describe('All constraints as key-value pairs: {"color":"red", "max_price":"50"}'),
        }),
        execute: async (input: { rowId: number; title: string; constraints?: Record<string, unknown> }) => {
          try {
            const headers: Record<string, string> = { 'Content-Type': 'application/json' };
            if (authorization) {
              headers['Authorization'] = authorization;
            }

            const updateBody: any = { title: input.title };
            if (input.constraints) {
              const normalizedConstraints: Record<string, string> = {};
              for (const [key, value] of Object.entries(input.constraints)) {
                normalizedConstraints[key] = normalizeConstraintValue(value);
              }

              updateBody.request_spec = {
                item_name: input.title,
                constraints: JSON.stringify(normalizedConstraints),
              };

              updateBody.choice_answers = JSON.stringify(normalizedConstraints);
            }

            const result = await fetchJsonWithTimeoutRetry(
              `${BACKEND_URL}/rows/${input.rowId}`,
              {
                method: 'PATCH',
                headers,
                body: JSON.stringify(updateBody),
              },
              20000,
              1,
              500
            );

            if (!result.ok) {
              return {
                status: 'error',
                code: result.status,
                message: result.data?.message || result.text || 'Backend request failed',
              };
            }

            return { status: 'row_updated', data: result.data };
          } catch (e) {
            const msg = e instanceof Error ? e.message : String(e);
            return { status: 'error', message: msg };
          }
        },
      },
      searchListings: {
        description: 'Search for existing listings for a row. The search uses the row\'s stored constraints.',
        inputSchema: z.object({
          rowId: z.number().describe('Row ID to scope the search - REQUIRED for proper constraint handling'),
          query: z.string().describe('The search query (usually the row title)'),
        }),
        execute: async (input: { rowId: number; query: string }) => {
          try {
            const headers: Record<string, string> = { 'Content-Type': 'application/json' };
            if (authorization) {
              headers['Authorization'] = authorization;
            }

            const searchResult = await fetchJsonWithTimeoutRetry(
              `${BACKEND_URL}/rows/${input.rowId}/search`,
              {
                method: 'POST',
                headers,
                body: JSON.stringify({ query: input.query }),
              },
              30000,
              1,
              500
            );

            if (!searchResult.ok) {
              return {
                status: 'error',
                code: searchResult.status,
                message: searchResult.data?.message || searchResult.text || 'Backend request failed',
              };
            }

            return searchResult.data;
          } catch (e) {
            const msg = e instanceof Error ? e.message : String(e);
            return { status: 'error', message: msg };
          }
        },
      },
      getChoiceFactors: {
        description: 'Get relevant choice factors for a product category. Call this if you need to regenerate factors.',
        inputSchema: z.object({
          category: z.string().describe('The product category, e.g., "laptop", "wedding venue", "car"'),
          rowId: z.number().describe('The row ID to associate factors with'),
        }),
        execute: async (input: { category: string; rowId: number }) => {
          try {
            const factors = await generateAndSaveChoiceFactors(input.category, input.rowId, authorization);
            
            if (!factors) {
               return { status: 'error', error: 'Failed to generate factors' };
            }
            
            return { 
              status: 'factors_generated', 
              row_id: input.rowId, 
              factors,
              next_action: 'Ask the user about these factors one at a time'
            };
          } catch (e) {
            return { status: 'error', error: String(e) };
          }
        },
      },
      saveChoiceAnswer: {
        description: 'Save a user\'s answer to a choice factor question. Call this when the user answers a question about their requirements.',
        inputSchema: z.object({
          rowId: z.number().describe('The row ID'),
          factorName: z.string().describe('The factor name (e.g., "budget", "primary_use")'),
          answer: z.union([z.string(), z.number(), z.boolean()]).describe('The user\'s answer'),
        }),
        execute: async (input: { rowId: number; factorName: string; answer: string | number | boolean }) => {
          try {
            const headers: Record<string, string> = { 'Content-Type': 'application/json' };
            if (authorization) {
              headers['Authorization'] = authorization;
            }
            
            const rowRes = await fetch(`${BACKEND_URL}/rows/${input.rowId}`, { headers });
            const row = await rowRes.json() as any;
            
            let answers: Record<string, any> = {};
            if (row.choice_answers) {
              try {
                answers = JSON.parse(row.choice_answers);
              } catch {}
            }
            
            answers[input.factorName] = input.answer;
            
            await fetch(`${BACKEND_URL}/rows/${input.rowId}`, {
              method: 'PATCH',
              headers,
              body: JSON.stringify({ choice_answers: JSON.stringify(answers) }),
            });
            
            return { 
              status: 'answer_saved', 
              row_id: input.rowId, 
              factor: input.factorName,
              answers 
            };
          } catch (e) {
            return { status: 'error', error: String(e) };
          }
        },
      },
    },
  });
};
