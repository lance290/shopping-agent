import { google } from '@ai-sdk/google';
import { streamText } from 'ai';
import { z } from 'zod';

const model = google(process.env.GEMINI_MODEL || 'gemini-1.5-flash');
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export const chatHandler = async (messages: any[], authorization?: string, activeRowId?: number | null): Promise<any> => {
  // Build context about active row for the LLM
  const activeRowContext = activeRowId ? `\n\nCURRENT ACTIVE ROW ID: ${activeRowId}. When refining the current search, use updateRow with this row_id to update the title and constraints, then call searchListings with this row_id.` : '';

  return streamText({
    model,
    messages,
    system: `You are a procurement agent. Help users find items and manage their procurement board.

IMPORTANT RULES:
1. When a user asks for a NEW item (like "I need Montana State shirts"), call createRow ONCE then searchListings with the new row's ID.
2. When a user REFINES their search (like "under $50", "XXL", "blue color"), call updateRow FIRST to update the row's title and constraints, then call searchListings with the row_id.
3. ALWAYS include the row_id when calling searchListings so results are scoped to that row.
4. When updating a row, build a NEW title that reflects ALL accumulated constraints (e.g., "blue Montana State shirts under $50").

Examples of refinements (use updateRow then searchListings):
- User says "under $50" → updateRow with title="[item] under $50", constraints={"max_price":"50"}, then searchListings with row_id
- User says "blue color" → updateRow with title="blue [item]", constraints={"color":"blue"}, then searchListings with row_id
- User says "XXL" → updateRow with title="[item] XXL", constraints={"size":"XXL"}, then searchListings with row_id

Only create a new row when the user asks for a completely different item.${activeRowContext}`,
    tools: {
      createRow: {
        description: 'Create a new procurement row for an item',
        inputSchema: z.object({
          item: z.string().describe('The name of the item to buy'),
          constraints: z.record(z.string(), z.union([z.string(), z.number()])).optional().describe('Key-value constraints like size, color, budget'),
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
        description: 'Update an existing row with new title and/or constraints. Call this BEFORE searchListings when refining a search.',
        inputSchema: z.object({
          rowId: z.number().describe('The ID of the row to update'),
          title: z.string().describe('The new title reflecting all accumulated constraints'),
          constraints: z.record(z.string(), z.string()).optional().describe('Updated constraints object'),
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
