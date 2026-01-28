import Fastify from 'fastify';
import cors from '@fastify/cors';
import fs from 'fs';
import path from 'path';
import { chatHandler, generateAndSaveChoiceFactors, GEMINI_MODEL_NAME, triageProviderQuery } from './llm';

// Manually load .env since we want to avoid dependency issues
try {
  const envPath = path.resolve(__dirname, '../.env');
  if (fs.existsSync(envPath)) {
    const envConfig = fs.readFileSync(envPath, 'utf8');
    envConfig.split('\n').forEach(line => {
      const match = line.match(/^([^#=]+)=(.*)$/);
      if (match) {
        const key = match[1].trim();
        const value = match[2].trim();
        if (key && value.length > 0 && !process.env[key]) {
          process.env[key] = value;
        }
      }
        });
    console.log('Loaded .env configuration from:', envPath);
  }
} catch (e) {
  console.warn('Failed to load .env file:', e);
}

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

function buildBasicChoiceFactors(itemName: string): Array<{
  name: string;
  label: string;
  type: 'number' | 'select' | 'text' | 'boolean';
  options?: string[];
  required: boolean;
}> {
  const normalized = (itemName || '').trim();
  const displayName = normalized.length ? normalized : 'this item';
  const text = normalized.toLowerCase();

  const isBike = /(\bbikes?\b|\bbicycles?\b|mtb|mountain bike|road bike|gravel bike|e-bike|ebike)/i.test(text);
  const isRacquet = /(racquet|racket)/i.test(text);
  const isSocks = /\bsocks?\b/i.test(text);
  const isShoes = /(shoe|shoes|sneaker|sneakers|cleat|cleats)/i.test(text);

  const shared: Array<{
    name: string;
    label: string;
    type: 'number' | 'select' | 'text' | 'boolean';
    options?: string[];
    required: boolean;
  }> = [
    {
      name: 'max_budget',
      label: 'Price Range',
      type: 'number',
      required: false,
    },
    {
      name: 'preferred_brand',
      label: 'Preferred Brand',
      type: 'text',
      required: false,
    },
    {
      name: 'condition',
      label: 'Condition',
      type: 'select',
      options: ['new', 'used', 'either'],
      required: false,
    },
    {
      name: 'shipping_speed',
      label: 'Shipping Speed',
      type: 'select',
      options: ['fastest', 'standard', 'no_rush'],
      required: false,
    },
    {
      name: 'notes',
      label: `Notes (anything specific about ${displayName})`,
      type: 'text',
      required: false,
    },
  ];

  if (isBike) {
    return [
      {
        name: 'bike_size',
        label: 'Bike Size',
        type: 'select',
        options: ['XS', 'S', 'M', 'L', 'XL', 'Not sure'],
        required: false,
      },
      {
        name: 'frame_material',
        label: 'Frame Material',
        type: 'select',
        options: ['carbon', 'aluminum', 'steel', 'titanium', 'either'],
        required: false,
      },
      ...shared,
    ];
  }

  if (isRacquet) {
    return [
      {
        name: 'racquet_size',
        label: 'Racquet Size',
        type: 'select',
        options: ['Adult', 'Junior', 'Not sure'],
        required: false,
      },
      {
        name: 'grip_size',
        label: 'Grip Size',
        type: 'select',
        options: ['4 0/8', '4 1/8', '4 2/8', '4 3/8', '4 4/8', 'Not sure'],
        required: false,
      },
      {
        name: 'racquet_material',
        label: 'Material',
        type: 'select',
        options: ['graphite', 'carbon', 'aluminum', 'wood', 'either'],
        required: false,
      },
      ...shared,
    ];
  }

  if (isSocks) {
    return [
      {
        name: 'sock_size',
        label: 'Size',
        type: 'select',
        options: ['S', 'M', 'L', 'XL', 'Not sure'],
        required: false,
      },
      {
        name: 'sock_material',
        label: 'Material',
        type: 'select',
        options: ['cotton', 'wool', 'synthetic', 'bamboo', 'either'],
        required: false,
      },
      ...shared,
    ];
  }

  if (isShoes) {
    return [
      {
        name: 'shoe_size',
        label: 'Size',
        type: 'text',
        required: false,
      },
      {
        name: 'shoe_material',
        label: 'Material',
        type: 'select',
        options: ['leather', 'synthetic', 'mesh', 'either'],
        required: false,
      },
      ...shared,
    ];
  }

  return shared;
}

export function buildApp() {
  const fastify = Fastify({
    logger: true,
  });

  // Register plugins
  fastify.register(cors, {
    origin: process.env.CORS_ORIGIN || '*',
  });

  fastify.addContentTypeParser(
    /^multipart\/form-data(?:;.*)?$/,
    { parseAs: 'buffer' },
    (req, body, done) => {
      done(null, body);
    }
  );

  async function saveChoiceFactorsToBackend(rowId: number, factors: unknown, authorization?: string) {
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
  }

  function normalizeRefinementText(text: string): { normalized: string; isRefinement: boolean } {
    const raw = (text || '').trim();
    const lower = raw.toLowerCase();

  const patterns: Array<{ re: RegExp; isRefinement: boolean }> = [
    { re: /^i\s+meant\s+/i, isRefinement: true },
    { re: /^actually\s+/i, isRefinement: true },
    { re: /^no\s*,\s*/i, isRefinement: true },
    { re: /^instead\s+/i, isRefinement: true },
    { re: /^change\s+to\s+/i, isRefinement: true },
    { re: /^make\s+it\s+/i, isRefinement: true },
  ];

  for (const p of patterns) {
    if (p.re.test(raw)) {
      const normalized = raw.replace(p.re, '').trim();
      return { normalized: normalized || raw, isRefinement: true };
    }
  }

  if (lower.startsWith('i mean ')) {
    return { normalized: raw.slice('i mean '.length).trim() || raw, isRefinement: true };
  }

    return { normalized: raw, isRefinement: false };
  }

  // Proxy clickout to backend (preserves auth header for user tracking)
  fastify.get('/api/out', async (request, reply) => {
    try {
      const query = request.query as Record<string, string>;
      const params = new URLSearchParams(query).toString();

      const headers: Record<string, string> = {};
      if (request.headers.authorization) {
        headers['Authorization'] = request.headers.authorization;
      }

      const response = await fetch(`${BACKEND_URL}/api/out?${params}`, {
        headers,
        redirect: 'manual', // Don't follow redirect, pass it through
      });

      // Pass through the redirect
      const location = response.headers.get('location');
      if (location) {
        reply.redirect(302, location);
      } else {
        reply.status(response.status).send(await response.text());
      }
    } catch (err) {
      fastify.log.error(err);
      reply.status(500).send({ error: 'Clickout failed' });
    }
  });

  fastify.post('/api/bugs', async (request, reply) => {
  try {
    const headers: Record<string, string> = {};
    const contentType = request.headers['content-type'];
    if (typeof contentType === 'string' && contentType.length > 0) {
      headers['Content-Type'] = contentType;
    }
    if (request.headers.authorization) {
      headers['Authorization'] = request.headers.authorization;
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(`${BACKEND_URL}/api/bugs`, {
        method: 'POST',
        headers,
        body: request.body as any,
        signal: controller.signal,
      } as any);

      const text = await response.text();
      let data: any = null;
      try {
        data = text ? JSON.parse(text) : null;
      } catch {
        data = null;
      }

      reply.status(response.status);
      if (data !== null) {
        reply.send(data);
        return;
      }
      reply.send(text);
    } finally {
      clearTimeout(timeout);
    }
  } catch (err) {
    fastify.log.error(err);
    const msg = err instanceof Error ? err.message : String(err);
    reply.status(502).send({ error: msg || 'Failed to submit bug report' });
  }
});

  fastify.post('/api/search', async (request, reply) => {
  try {
    const body = request.body as any;
    const rowId = body?.rowId;

    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (request.headers.authorization) {
      headers['Authorization'] = request.headers.authorization as string;
    }

    if (rowId) {
      const rowRes = await fetch(`${BACKEND_URL}/rows/${rowId}`, { headers });
      if (!rowRes.ok) {
        const text = await rowRes.text();
        reply.status(rowRes.status).send({ error: text || 'Failed to fetch row' });
        return;
      }
      const row = await rowRes.json() as any;

      let projectTitle: string | null = null;
      if (row?.project_id) {
        const projectsRes = await fetch(`${BACKEND_URL}/projects`, { headers });
        if (projectsRes.ok) {
          const projects = await projectsRes.json();
          if (Array.isArray(projects)) {
            const project = projects.find((p: any) => p?.id === row.project_id);
            if (project?.title) projectTitle = String(project.title);
          }
        }
      }

      const displayQuery = typeof body?.query === 'string' ? body.query : (row?.title || '');
      const providerQuery = await triageProviderQuery({
        displayQuery,
        rowTitle: row?.title,
        projectTitle,
        choiceAnswersJson: row?.choice_answers,
        requestSpecConstraintsJson: row?.request_spec?.constraints,
      });

      const safeProviderQuery = providerQuery || displayQuery;

      await fetch(`${BACKEND_URL}/rows/${rowId}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ provider_query: safeProviderQuery }),
      });

      const response = await fetch(`${BACKEND_URL}/rows/${rowId}/search`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ ...body, query: safeProviderQuery }),
      });
      const data = await response.json();
      reply.status(response.status).send(data);
      return;
    }

    const targetUrl = `${BACKEND_URL}/v1/sourcing/search`;

    const response = await fetch(targetUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
    const data = await response.json();
    return data;
  } catch (err) {
    fastify.log.error(err);
    reply.status(500).send({ error: 'Failed to fetch from backend' });
  }
  });

  fastify.get('/health', async () => {
    return { status: 'ok' };
  });

// Root route
  fastify.get('/', async () => {
    return { message: 'Hello from Fastify!' };
  });

  fastify.post('/api/chat', async (request, reply) => {
  let headersSent = false;
  try {
    const { messages, activeRowId, projectId } = request.body as { messages: any[]; activeRowId?: number; projectId?: number };
    const authorization = request.headers.authorization;

    if (!process.env.GOOGLE_GENERATIVE_AI_API_KEY) {
      reply.raw.writeHead(200, {
        'Content-Type': 'text/plain; charset=utf-8',
        'Transfer-Encoding': 'chunked',
        'Cache-Control': 'no-cache',
      });
      headersSent = true;

      const lastUserMessage = Array.isArray(messages)
        ? [...messages].reverse().find((m: any) => m?.role === 'user')
        : null;

      const userText =
        typeof lastUserMessage?.content === 'string'
          ? lastUserMessage.content
          : typeof lastUserMessage?.content?.text === 'string'
            ? lastUserMessage.content.text
            : '';

      const rawQuery = userText.trim();
      if (!rawQuery) {
        reply.raw.write('No query provided.');
        reply.raw.end();
        return;
      }

      const { normalized: normalizedQuery, isRefinement } = normalizeRefinementText(rawQuery);
      const query = normalizedQuery;

      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (authorization) {
        headers['Authorization'] = authorization as string;
      }

      let rowId: number | undefined = activeRowId;

      // If we have an active row and the user is refining, update the existing row title/spec
      // so backend search uses the updated row.title/spec.item_name.
      if (rowId && isRefinement && query) {
        reply.raw.write(`\n🔄 Updating row #${rowId} to "${query}"...`);
        await fetchJsonWithTimeout(
          `${BACKEND_URL}/rows/${rowId}`,
          {
            method: 'PATCH',
            headers,
            body: JSON.stringify({
              title: query,
              request_spec: {
                item_name: query,
              },
            }),
          },
          15000
        );
        reply.raw.write(' Done!');
      }
      if (!rowId) {
        reply.raw.write(`\n✅ Adding "${query}" to your procurement board...`);

        const createResult = await fetchJsonWithTimeout(
          `${BACKEND_URL}/rows`,
          {
            method: 'POST',
            headers,
            body: JSON.stringify({
              title: query,
              status: 'sourcing',
              project_id: projectId,
              request_spec: {
                item_name: query,
                constraints: JSON.stringify({}),
              },
              choice_answers: JSON.stringify({}),
            }),
          },
          15000
        );

        if (!createResult.ok) {
          const msg =
            createResult.data?.detail ||
            createResult.data?.message ||
            createResult.text ||
            'Backend request failed';
          reply.raw.write(`\n⚠️ Error (${createResult.status}): ${msg}`);
          reply.raw.end();
          return;
        }

        rowId = createResult.data?.id;
        if (!rowId) {
          reply.raw.write(`\n⚠️ Error: Backend returned unexpected response for createRow`);
          reply.raw.end();
          return;
        }

        // Persist deterministic fallback choice factors so the UI can render Options.
        // Fire-and-forget to avoid delaying search.
        saveChoiceFactorsToBackend(rowId, buildBasicChoiceFactors(query), authorization as string | undefined).catch((err) => {
          fastify.log.error({ err, rowId }, 'Failed to save fallback choice_factors');
        });

        reply.raw.write(' Done!');
      }

      reply.raw.write(`\n🔍 Searching for "${query}"...`);

      const searchResult = await fetchJsonWithTimeout(
        `${BACKEND_URL}/rows/${rowId}/search`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({ query }),
        },
        30000
      );

      if (!searchResult.ok) {
        const msg =
          searchResult.data?.detail ||
          searchResult.data?.message ||
          searchResult.text ||
          'Backend request failed';
        reply.raw.write(`\n⚠️ Error (${searchResult.status}): ${msg}`);
        reply.raw.end();
        return;
      }

      const count = Array.isArray(searchResult.data?.results) ? searchResult.data.results.length : 0;
      reply.raw.write(` Found ${count} results!`);
      reply.raw.end();
      return;
    }

    const result = await chatHandler(messages, authorization, activeRowId, projectId);
    
    // Set headers for streaming
    reply.raw.writeHead(200, {
      'Content-Type': 'text/plain; charset=utf-8',
      'Transfer-Encoding': 'chunked',
      'Cache-Control': 'no-cache',
    });
    headersSent = true;
    
    // Use fullStream to capture both text and tool events
    for await (const part of result.fullStream) {
      fastify.log.info({ partType: part.type, part }, 'Stream part received');
      
      if (part.type === 'text-delta') {
        if (part.textDelta) {
          reply.raw.write(part.textDelta);
        }
      } else if (part.type === 'tool-call') {
        // Provide feedback when a tool is called
        // AI SDK uses 'input' not 'args' for tool call parameters
        const toolPart = part as any;
        const input = toolPart.input;
        if (toolPart.toolName === 'createRow') {
          const itemName = input?.item || 'item';
          reply.raw.write(`\n✅ Adding "${itemName}" to your procurement board...`);
        } else if (toolPart.toolName === 'updateRow') {
          const newTitle = input?.title || 'item';
          const rowId = input?.rowId;
          reply.raw.write(`\n🔄 Updating row #${rowId} to "${newTitle}"...`);
        } else if (toolPart.toolName === 'searchListings') {
          const query = input?.query || 'items';
          reply.raw.write(`\n🔍 Searching for "${query}"...`);
        }
      } else if (part.type === 'tool-result') {
        // Provide feedback when tool completes
        const toolResult = part as any;
        // AI SDK uses 'output' not 'result' for tool results
        const output = toolResult.output;
        fastify.log.info({ toolName: toolResult.toolName, output }, 'Processing tool-result');

        if (output?.status === 'error') {
          const msg = output?.message || output?.error || 'Tool failed';
          const code = output?.code ? ` (${output.code})` : '';
          reply.raw.write(`\n⚠️ Error${code}: ${msg}`);
          continue;
        }
        
        if (toolResult.toolName === 'createRow') {
          if (output?.status === 'row_created') {
            reply.raw.write(` Done!`);
          }
        } else if (toolResult.toolName === 'updateRow') {
          if (output?.status === 'row_updated') {
            reply.raw.write(` Done!`);
          }
        } else if (toolResult.toolName === 'searchListings') {
          const count = output?.count || 0;
          fastify.log.info({ count, hasPreview: !!output?.preview }, 'Search results');
          reply.raw.write(` Found ${count} results!`);
          
          // Show preview of top results
          if (output?.preview && output.preview.length > 0) {
            reply.raw.write('\n\nTop matches:');
            for (const item of output.preview) {
              reply.raw.write(`\n• ${item.title} - $${item.price} from ${item.merchant}`);
            }
          }
        }
      } else if (part.type === 'tool-error') {
        // Handle tool errors
        const toolError = part as any;
        fastify.log.error({ toolError }, 'Tool error');
        reply.raw.write(`\n⚠️ Error: ${toolError.error || 'Tool failed'}`);
      }
    }
    
    reply.raw.end();
  } catch (err: any) {
    fastify.log.error('Chat error', err);
    if (!headersSent) {
      reply.status(500).send({ error: 'Chat processing failed' });
    } else {
      reply.raw.write('\n\nError: ' + (err.message || 'Something went wrong'));
      reply.raw.end();
    }
  }
});

// Row Management Proxy
  fastify.get('/api/rows', async (request, reply) => {
  try {
    const headers: Record<string, string> = {};
    if (request.headers.authorization) {
      headers['Authorization'] = request.headers.authorization;
    }

    const result = await fetchJsonWithTimeout(
      `${BACKEND_URL}/rows`,
      { headers },
      8000
    );

    if (result.status === 401) {
      reply.status(401).send({ error: 'Unauthorized' });
      return;
    }

    if (!result.ok) {
      reply.status(result.status).send({
        error: result.data?.detail || result.data?.message || result.text || 'Failed to fetch rows',
      });
      return;
    }

    return result.data;
  } catch (err) {
    fastify.log.error(err);
    const msg = err instanceof Error ? err.message : String(err);
    reply.status(502).send({ error: msg || 'Failed to fetch rows' });
  }
});

  fastify.post('/api/rows', async (request, reply) => {
  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (request.headers.authorization) {
      headers['Authorization'] = request.headers.authorization;
    }

    const result = await fetchJsonWithTimeout(
      `${BACKEND_URL}/rows`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify(request.body),
      },
      8000
    );

    if (result.status === 401) {
      reply.status(401).send({ error: 'Unauthorized' });
      return;
    }

    if (!result.ok) {
      reply.status(result.status).send({
        error: result.data?.detail || result.data?.message || result.text || 'Failed to create row',
      });
      return;
    }

    return result.data;
  } catch (err) {
    fastify.log.error(err);
    const msg = err instanceof Error ? err.message : String(err);
    reply.status(502).send({ error: msg || 'Failed to create row' });
  }
});

  fastify.get('/api/rows/:id', async (request, reply) => {
  try {
    const { id } = request.params as { id: string };
    const headers: Record<string, string> = {};
    if (request.headers.authorization) {
      headers['Authorization'] = request.headers.authorization;
    }

    const result = await fetchJsonWithTimeout(
      `${BACKEND_URL}/rows/${id}`,
      { headers },
      8000
    );

    if (result.status === 401) {
      reply.status(401).send({ error: 'Unauthorized' });
      return;
    }
    if (result.status === 404) {
      reply.status(404).send({ error: 'Row not found' });
      return;
    }

    if (!result.ok) {
      reply.status(result.status).send({
        error: result.data?.detail || result.data?.message || result.text || 'Failed to fetch row',
      });
      return;
    }

    return result.data;
  } catch (err) {
    fastify.log.error(err);
    const msg = err instanceof Error ? err.message : String(err);
    reply.status(502).send({ error: msg || 'Failed to fetch row' });
  }
});

  fastify.delete('/api/rows/:id', async (request, reply) => {
  try {
    const { id } = request.params as { id: string };
    const headers: Record<string, string> = {};
    if (request.headers.authorization) {
      headers['Authorization'] = request.headers.authorization;
    }

    const response = await fetch(`${BACKEND_URL}/rows/${id}`, {
      method: 'DELETE',
      headers,
    });
    
    if (response.status === 401) {
      reply.status(401).send({ error: 'Unauthorized' });
      return;
    }
    if (response.status === 404) {
      reply.status(404).send({ error: 'Row not found' });
      return;
    }
    const data = await response.json();
    return data;
  } catch (err) {
    fastify.log.error(err);
    reply.status(500).send({ error: 'Failed to delete row' });
  }
});

  fastify.patch('/api/rows/:id', async (request, reply) => {
  try {
    const { id } = request.params as { id: string };
    fastify.log.info({ id, body: request.body }, 'Proxying PATCH row request');

    const maybeBody = (request.body || {}) as any;
    if (maybeBody.regenerate_choice_factors === true) {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (request.headers.authorization) {
        headers['Authorization'] = request.headers.authorization;
      }

      const rowRes = await fetch(`${BACKEND_URL}/rows/${id}`, { headers });
      if (rowRes.status === 401) {
        reply.status(401).send({ error: 'Unauthorized' });
        return;
      }
      if (rowRes.status === 404) {
        reply.status(404).send({ error: 'Row not found' });
        return;
      }

      const row = await rowRes.json() as any;

      let constraintsObj: Record<string, any> | undefined;
      const rawConstraints = row?.request_spec?.constraints;
      if (rawConstraints) {
        try {
          constraintsObj = JSON.parse(rawConstraints);
        } catch {
          constraintsObj = undefined;
        }
      }

      let answersObj: Record<string, any> | undefined;
      if (row?.choice_answers) {
        try {
          answersObj = JSON.parse(row.choice_answers);
        } catch {
          answersObj = undefined;
        }
      }

      const merged = { ...(constraintsObj || {}), ...(answersObj || {}) };

      const itemName = row?.title || row?.request_spec?.item_name || 'product';
      if (!process.env.GOOGLE_GENERATIVE_AI_API_KEY) {
        await saveChoiceFactorsToBackend(Number(id), buildBasicChoiceFactors(itemName), request.headers.authorization as string | undefined);
      } else {
        await generateAndSaveChoiceFactors(itemName, Number(id), request.headers.authorization as string | undefined, merged);
      }

      const updatedRes = await fetch(`${BACKEND_URL}/rows/${id}`, { headers });
      const updated = await updatedRes.json();
      reply.status(updatedRes.status).send(updated);
      return;
    }
    
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (request.headers.authorization) {
      headers['Authorization'] = request.headers.authorization;
    }

    const response = await fetch(`${BACKEND_URL}/rows/${id}`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify(request.body),
    });
    
    if (response.status === 401) {
      reply.status(401).send({ error: 'Unauthorized' });
      return;
    }
    if (response.status === 404) {
      reply.status(404).send({ error: 'Row not found' });
      return;
    }
    const data = await response.json();
    return data;
  } catch (err) {
    fastify.log.error(err);
    reply.status(500).send({ error: 'Failed to update row' });
  }
});

// Project Management Proxy
  fastify.get('/api/projects', async (request, reply) => {
  try {
    const headers: Record<string, string> = {};
    if (request.headers.authorization) {
      headers['Authorization'] = request.headers.authorization;
    }

    const result = await fetchJsonWithTimeout(
      `${BACKEND_URL}/projects`,
      { headers },
      8000
    );

    if (result.status === 401) {
      reply.status(401).send({ error: 'Unauthorized' });
      return;
    }

    if (!result.ok) {
      reply.status(result.status).send({
        error: result.data?.detail || result.data?.message || result.text || 'Failed to fetch projects',
      });
      return;
    }

    return result.data;
  } catch (err) {
    fastify.log.error(err);
    reply.status(502).send({ error: 'Failed to fetch projects' });
  }
});

  fastify.post('/api/projects', async (request, reply) => {
  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (request.headers.authorization) {
      headers['Authorization'] = request.headers.authorization;
    }

    const result = await fetchJsonWithTimeout(
      `${BACKEND_URL}/projects`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify(request.body),
      },
      8000
    );

    if (result.status === 401) {
      reply.status(401).send({ error: 'Unauthorized' });
      return;
    }

    if (!result.ok) {
      reply.status(result.status).send({
        error: result.data?.detail || result.data?.message || result.text || 'Failed to create project',
      });
      return;
    }

    return result.data;
  } catch (err) {
    fastify.log.error(err);
    reply.status(502).send({ error: 'Failed to create project' });
  }
});

  fastify.delete('/api/projects/:id', async (request, reply) => {
  try {
    const { id } = request.params as { id: string };
    const headers: Record<string, string> = {};
    if (request.headers.authorization) {
      headers['Authorization'] = request.headers.authorization;
    }

    const response = await fetch(`${BACKEND_URL}/projects/${id}`, {
      method: 'DELETE',
      headers,
    });
    
    if (response.status === 401) {
      reply.status(401).send({ error: 'Unauthorized' });
      return;
    }
    if (response.status === 404) {
      reply.status(404).send({ error: 'Project not found' });
      return;
    }
    const data = await response.json();
    return data;
  } catch (err) {
    fastify.log.error(err);
    reply.status(500).send({ error: 'Failed to delete project' });
  }
});

// ============ AUTH PROXY ROUTES ============

  fastify.post('/api/auth/start', async (request, reply) => {
  try {
    const response = await fetch(`${BACKEND_URL}/auth/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request.body),
    });
    const data = await response.json();
    reply.status(response.status).send(data);
  } catch (err) {
    fastify.log.error(err);
    reply.status(500).send({ error: 'Failed to start auth' });
  }
});

  fastify.post('/api/auth/verify', async (request, reply) => {
  try {
    const response = await fetch(`${BACKEND_URL}/auth/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request.body),
    });
    const data = await response.json();
    reply.status(response.status).send(data);
  } catch (err) {
    fastify.log.error(err);
    reply.status(500).send({ error: 'Failed to verify auth' });
  }
});

  fastify.get('/api/auth/me', async (request, reply) => {
  try {
    const authHeader = request.headers.authorization;
    const response = await fetch(`${BACKEND_URL}/auth/me`, {
      method: 'GET',
      headers: authHeader ? { Authorization: authHeader } : {},
    });
    const data = await response.json();
    reply.status(response.status).send(data);
  } catch (err) {
    fastify.log.error(err);
    reply.status(500).send({ error: 'Failed to check auth' });
  }
});

  fastify.post('/api/auth/logout', async (request, reply) => {
  try {
    const authHeader = request.headers.authorization;
    const response = await fetch(`${BACKEND_URL}/auth/logout`, {
      method: 'POST',
      headers: authHeader ? { Authorization: authHeader } : {},
    });
    const data = await response.json();
    reply.status(response.status).send(data);
  } catch (err) {
    fastify.log.error(err);
    reply.status(500).send({ error: 'Failed to logout' });
  }
});

  return fastify;
}

async function isPortAlreadyInUse(port: number): Promise<boolean> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 1500);
  try {
    const res = await fetch(`http://127.0.0.1:${port}/health`, {
      method: 'GET',
      signal: controller.signal,
    });
    return res.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timeout);
  }
}

// Start server
const start = async () => {
  try {
    const fastify = buildApp();
    const port = parseInt(process.env.PORT || '8080', 10);
    if (await isPortAlreadyInUse(port)) {
      fastify.log.warn(
        `BFF already running on port ${port}. Skipping duplicate start to avoid conflicts.`
      );
      process.exit(0);
    }

    await fastify.listen({ port, host: '0.0.0.0' }, (err, address) => {
      if (err) {
        if ((err as NodeJS.ErrnoException).code === 'EADDRINUSE') {
          fastify.log.warn(
            `Port ${port} already in use. Another BFF instance is likely running.`
          );
          process.exit(0);
        }
        fastify.log.error(err);
        process.exit(1);
      }
      fastify.log.info(`Server listening at ${address}`);
      const llmEnabled = Boolean(process.env.GOOGLE_GENERATIVE_AI_API_KEY);
      fastify.log.info(
        {
          llmEnabled,
          geminiModel: GEMINI_MODEL_NAME,
        },
        llmEnabled ? 'LLM mode enabled (Gemini)' : 'LLM mode disabled (fallback)'
      );
      fastify.log.info(`🚀 Server listening on port ${port}`);
    });
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
};

if (require.main === module) {
  start();
}
