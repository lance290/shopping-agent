import { google } from '@ai-sdk/google';
import { streamText, generateText } from 'ai';
import { z } from 'zod';

const model = google(process.env.GEMINI_MODEL || 'gemini-1.5-flash');
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

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
export async function generateAndSaveChoiceFactors(category: string, rowId: number, authorization?: string, existingConstraints?: Record<string, any>) {
  const constraintsText = existingConstraints ? `\nExisting constraints: ${JSON.stringify(existingConstraints)}` : '';
  
  const factorPrompt = `You are determining the key product specifications (attributes) for purchasing: "${category}"${constraintsText}

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
    
    await fetchJsonWithTimeout(
      `${BACKEND_URL}/rows/${rowId}`,
      {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ choice_factors: JSON.stringify(factors) }),
      },
      15000
    );
    
    return factors;
  } catch (e) {
    console.error("Error generating factors:", e);
    return null;
  }
}

export const chatHandler = async (messages: any[], authorization?: string, activeRowId?: number | null): Promise<any> => {
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
            
            const result = await fetchJsonWithTimeout(
              `${BACKEND_URL}/rows`,
              {
                method: 'POST',
                headers,
                body: JSON.stringify({
                  title: input.item,
                  status: 'sourcing',
                  request_spec: {
                    item_name: input.item,
                    constraints: JSON.stringify(normalizedConstraints)
                  },
                  choice_answers: JSON.stringify(normalizedConstraints)
                }),
              },
              15000
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
            
            return { status: 'row_created', data: { ...data, choice_factors: null } };
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

            const result = await fetchJsonWithTimeout(
              `${BACKEND_URL}/rows/${input.rowId}`,
              {
                method: 'PATCH',
                headers,
                body: JSON.stringify(updateBody),
              },
              15000
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

            const result = await fetchJsonWithTimeout(
              `${BACKEND_URL}/rows/${input.rowId}/search`,
              {
                method: 'POST',
                headers,
                body: JSON.stringify({ query: input.query }),
              },
              30000
            );

            if (!result.ok) {
              return {
                status: 'error',
                code: result.status,
                message: result.data?.message || result.text || 'Backend request failed',
              };
            }

            return result.data;
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
