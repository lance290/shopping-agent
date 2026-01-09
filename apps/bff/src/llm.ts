import { google } from '@ai-sdk/google';
import { streamText } from 'ai';
import { z } from 'zod';

const model = google(process.env.GEMINI_MODEL || 'gemini-1.5-flash');
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export const chatHandler = async (messages: any[]): Promise<any> => {
  return streamText({
    model,
    messages,
    system: `You are a procurement agent. Help users find items and manage their procurement board.

IMPORTANT RULES:
1. When a user asks for a NEW item (like "I need Montana State shirts"), call createRow ONCE then searchListings.
2. When a user REFINES their search (like "under $50", "XXL", "actually make it a sweatshirt"), do NOT create a new row. Just call searchListings with the updated/refined query that combines all their requirements.
3. ALWAYS call searchListings to show results - combine the original item with any refinements into one search query.

Examples of refinements (do NOT create new rows):
- "under $50" → search for "[previous item] under $50"
- "XXL" → search for "[previous item] XXL"  
- "actually I need a sweatshirt" → search for "[previous item] sweatshirt"
- "blue color" → search for "[previous item] blue"

Only create a new row when the user asks for a completely different item.`,
    tools: {
      createRow: {
        description: 'Create a new procurement row for an item',
        inputSchema: z.object({
          item: z.string().describe('The name of the item to buy'),
          constraints: z.record(z.string(), z.string()).optional().describe('Key-value constraints like size, color, budget'),
        }),
        execute: async (input: { item: string; constraints?: Record<string, string> }) => {
          try {
            const response = await fetch(`${BACKEND_URL}/rows`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                title: input.item,
                status: 'sourcing',
                request_spec: {
                  item_name: input.item,
                  constraints: JSON.stringify(input.constraints || {})
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
      searchListings: {
        description: 'Search for existing listings for a row',
        inputSchema: z.object({
          query: z.string().describe('The search query'),
        }),
        execute: async (input: { query: string }) => {
          try {
            const response = await fetch(`${BACKEND_URL}/v1/sourcing/search`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ query: input.query })
            });
            const data = await response.json() as any;
            return { status: 'results_found', count: data.results?.length || 0, preview: data.results?.slice(0, 3) };
          } catch (e) {
            return { status: 'error', error: String(e) };
          }
        },
      },
    },
  });
};
