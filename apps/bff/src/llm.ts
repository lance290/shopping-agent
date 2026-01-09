import { google } from '@ai-sdk/google';
import { streamText } from 'ai';
import { z } from 'zod';

const model = google(process.env.GEMINI_MODEL || 'gemini-1.5-flash');
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export const chatHandler = async (messages: any[]): Promise<any> => {
  return streamText({
    model,
    messages,
    system: 'You are a procurement agent. Help users find items and manage their procurement board.',
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
