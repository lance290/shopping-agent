import { google } from '@ai-sdk/google';
import { streamText } from 'ai';
import { z } from 'zod';

const model = google(process.env.GEMINI_MODEL || 'gemini-1.5-flash');
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

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
   - Call createRow ONCE, then searchListings with the new row's ID

3. When calling updateRow:
   - Build a NEW title with ALL constraints: "red Montana State shirts under $50 XXL"
   - Include constraints object: {"color":"red", "max_price":"50", "size":"XXL"}

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
          constraints: z.record(z.string(), z.union([z.string(), z.number()])).optional().describe('Initial constraints for the new item'),
        }),
        execute: async (input: { item: string; constraints?: Record<string, string | number> }) => {
          try {
            // Convert all constraint values to strings
            const normalizedConstraints: Record<string, string> = {};
            if (input.constraints) {
              for (const [key, value] of Object.entries(input.constraints)) {
                normalizedConstraints[key] = String(value);
              }
            }
            
            const headers: Record<string, string> = { 'Content-Type': 'application/json' };
            if (authorization) {
              headers['Authorization'] = authorization;
            }
            
            const response = await fetch(`${BACKEND_URL}/rows`, {
              method: 'POST',
              headers,
              body: JSON.stringify({
                title: input.item,
                status: 'sourcing',
                request_spec: {
                  item_name: input.item,
                  constraints: JSON.stringify(normalizedConstraints)
                }
              })
            });
            const data = await response.json() as any;
            return { status: 'row_created', data };
          } catch (e) {
            return { status: 'error', error: String(e) };
          }
        },
      },
      updateRow: {
        description: 'UPDATE an existing row when user refines their search (price, color, size, etc). ALWAYS use this instead of createRow for refinements. Call this BEFORE searchListings.',
        inputSchema: z.object({
          rowId: z.number().describe('The ID of the active row to update - use the CURRENT ACTIVE ROW ID from system context'),
          title: z.string().describe('The NEW title with ALL accumulated constraints, e.g. "red Montana State shirts under $50"'),
          constraints: z.record(z.string(), z.string()).optional().describe('All constraints as key-value pairs: {"color":"red", "max_price":"50"}'),
        }),
        execute: async (input: { rowId: number; title: string; constraints?: Record<string, string> }) => {
          try {
            const headers: Record<string, string> = { 'Content-Type': 'application/json' };
            if (authorization) {
              headers['Authorization'] = authorization;
            }

            const updateBody: any = { title: input.title };
            if (input.constraints) {
              updateBody.request_spec = {
                item_name: input.title,
                constraints: JSON.stringify(input.constraints),
              };
            }

            const response = await fetch(`${BACKEND_URL}/rows/${input.rowId}`, {
              method: 'PATCH',
              headers,
              body: JSON.stringify(updateBody),
            });
            const data = await response.json() as any;
            return { status: 'row_updated', row_id: input.rowId, data };
          } catch (e) {
            return { status: 'error', error: String(e) };
          }
        },
      },
      searchListings: {
        description: 'Search for existing listings for a row. The search uses the row\'s stored constraints.',
        inputSchema: z.object({
          query: z.string().describe('The search query (usually the row title)'),
          rowId: z.number().describe('Row ID to scope the search - REQUIRED for proper constraint handling'),
        }),
        execute: async (input: { query: string; rowId: number }) => {
          try {
            const headers: Record<string, string> = { 'Content-Type': 'application/json' };
            if (authorization) {
              headers['Authorization'] = authorization;
            }

            const response = await fetch(`${BACKEND_URL}/rows/${input.rowId}/search`, {
              method: 'POST',
              headers,
              body: JSON.stringify({ query: input.query })
            });
            const data = await response.json() as any;
            return { status: 'results_found', row_id: input.rowId, count: data.results?.length || 0, preview: data.results?.slice(0, 3) };
          } catch (e) {
            return { status: 'error', error: String(e) };
          }
        },
      },
    },
  });
};
