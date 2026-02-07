import Fastify from 'fastify';
import cors from '@fastify/cors';
import fs from 'fs';
import path from 'path';
import { generateAndSaveChoiceFactors, GEMINI_MODEL_NAME, makeUnifiedDecision, ChatContext, triageProviderQuery } from './llm';
import { extractSearchIntent } from './intent';

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

/**
 * Stream search results from backend, calling onResults for each batch.
 * Returns accumulated results and statuses when complete.
 */
async function streamSearchResults(
  rowId: number,
  searchBody: { query?: string; providers?: string[] },
  headers: Record<string, string>,
  onResults: (data: {
    provider: string;
    results: any[];
    status: any;
    more_incoming: boolean;
    total_results_so_far: number;
  }) => void
): Promise<{ results: any[]; provider_statuses: any[]; user_message?: string }> {
  const url = `${BACKEND_URL}/rows/${rowId}/search/stream`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(searchBody),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Search stream failed: ${response.status} ${text}`);
  }

  const allResults: any[] = [];
  const allStatuses: any[] = [];
  
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body reader');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    
    // Parse SSE events from buffer
    const lines = buffer.split('\n');
    buffer = lines.pop() || ''; // Keep incomplete line in buffer

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          
          if (data.event === 'complete') {
            // Final event - use accumulated statuses
            return {
              results: allResults,
              provider_statuses: data.provider_statuses || allStatuses,
              user_message: data.user_message,
            };
          }
          
          // Incremental results from a provider
          if (data.results) {
            allResults.push(...data.results);
          }
          if (data.status) {
            allStatuses.push(data.status);
          }
          
          // Notify caller of this batch
          onResults({
            provider: data.provider,
            results: data.results || [],
            status: data.status,
            more_incoming: data.more_incoming ?? false,
            total_results_so_far: data.total_results_so_far || allResults.length,
          });
        } catch (e) {
          // Ignore parse errors for incomplete data
        }
      }
    }
  }

  return { results: allResults, provider_statuses: allStatuses, user_message: undefined };
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

  // ── Merchant register pass-through ──────────────────────────────────
  fastify.post('/api/merchants/register', async (request, reply) => {
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (request.headers.authorization) {
        headers['Authorization'] = request.headers.authorization as string;
      }

      const response = await fetch(`${BACKEND_URL}/merchants/register`, {
        method: 'POST',
        headers,
        body: JSON.stringify(request.body),
      });

      const text = await response.text();
      let data: any;
      try {
        data = text ? JSON.parse(text) : null;
      } catch {
        data = null;
      }
      reply.status(data ? response.status : 502).send(data ?? { detail: `Backend error (${response.status})` });
    } catch (err) {
      fastify.log.error(err);
      const msg = err instanceof Error ? err.message : String(err);
      reply.status(502).send({ detail: msg || 'Failed to reach backend' });
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
        const row = (await rowRes.json()) as any;

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

        const clientProvidedQuery =
          typeof body?.query === 'string' && body.query.trim().length > 0;
        const displayQuery = clientProvidedQuery ? body.query : row?.title || '';
        const providerQuery = await triageProviderQuery({
          displayQuery,
          rowTitle: row?.title,
          projectTitle,
          choiceAnswersJson: row?.choice_answers,
          requestSpecConstraintsJson: row?.request_spec?.constraints,
        });

        const safeProviderQuery = providerQuery || displayQuery;
        const intentResult = await extractSearchIntent({
          displayQuery,
          rowTitle: row?.title,
          projectTitle,
          choiceAnswersJson: row?.choice_answers,
          requestSpecConstraintsJson: row?.request_spec?.constraints,
        });

        await fetch(`${BACKEND_URL}/rows/${rowId}`, {
          method: 'PATCH',
          headers,
          body: JSON.stringify({ provider_query: safeProviderQuery }),
        });

        const searchBody: any = {
          search_intent: intentResult.search_intent,
        };
        if (Array.isArray(body?.providers) && body.providers.length > 0) {
          searchBody.providers = body.providers;
        }
        if (clientProvidedQuery) {
          searchBody.query = safeProviderQuery;
        }

        const response = await fetch(`${BACKEND_URL}/rows/${rowId}/search`, {
          method: 'POST',
          headers,
          body: JSON.stringify(searchBody),
        });
        const data = await response.json();
        const responseBody =
          data && typeof data === 'object'
            ? { ...data, search_intent: intentResult.search_intent }
            : { results: data, search_intent: intentResult.search_intent };
        reply.status(response.status).send(responseBody);
        return;
      }

      const targetUrl = `${BACKEND_URL}/v1/sourcing/search`;
      const intentResult = await extractSearchIntent({
        displayQuery: typeof body?.query === 'string' ? body.query : '',
        rowTitle: typeof body?.query === 'string' ? body.query : '',
        projectTitle: null,
        choiceAnswersJson: body?.choice_answers,
        requestSpecConstraintsJson: body?.request_spec?.constraints,
      });

      const response = await fetch(targetUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify({ ...body, search_intent: intentResult.search_intent }),
      });
      const data = await response.json();
      const responseBody =
        data && typeof data === 'object'
          ? { ...data, search_intent: intentResult.search_intent }
          : { results: data, search_intent: intentResult.search_intent };
      reply.status(response.status).send(responseBody);
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

  async function runDeterministicChatFallback(
    input: {
      messages: any[];
      activeRowId?: number;
      projectId?: number;
      authorization?: unknown;
    },
    reply: any,
    headersAlreadySent: boolean
  ) {
    if (!headersAlreadySent) {
      reply.raw.writeHead(200, {
        'Content-Type': 'text/plain; charset=utf-8',
        'Transfer-Encoding': 'chunked',
        'Cache-Control': 'no-cache',
      });
    }

    const { messages, activeRowId, projectId, authorization } = input;

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

    const parsePriceConstraint = (text: string): { min?: number; max?: number; remaining: string } => {
      const raw = (text || '').trim();
      const numberMatches = raw.match(/\$?\s*(\d+(?:\.\d+)?)/g) || [];
      const nums = numberMatches
        .map((m) => Number(String(m).replace(/[^0-9.]/g, '')))
        .filter((n) => Number.isFinite(n));

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
    };

    const priceParsed = parsePriceConstraint(query);
    const hasPriceConstraint = priceParsed.min != null || priceParsed.max != null;
    const queryToUse = priceParsed.remaining || '';
    const isPriceOnly = hasPriceConstraint && !queryToUse;

    const headers: Record<string, string> = { 'Content-Type': 'application/json' };

    const normalizedAuth = Array.isArray(authorization)
      ? authorization[0]
      : authorization;

    let authHeaderValue = typeof normalizedAuth === 'string' ? normalizedAuth : '';

    if (!authHeaderValue) {
      const devEmail =
        process.env.DEV_SESSION_EMAIL ||
        process.env.NEXT_PUBLIC_DEV_SESSION_EMAIL ||
        'test@example.com';

      const minted = await fetchJsonWithTimeout(
        `${BACKEND_URL}/test/mint-session`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: devEmail }),
        },
        8000
      );

      const token = minted.data?.session_token;
      if (minted.ok && typeof token === 'string' && token.length > 0) {
        authHeaderValue = `Bearer ${token}`;
      }
    }

    if (authHeaderValue) {
      headers['Authorization'] = authHeaderValue;
    }

    let rowId: number | undefined = activeRowId;
    let existingRowTitle: string | undefined;

    if (rowId && hasPriceConstraint) {
      const existingRowRes = await fetchJsonWithTimeout(
        `${BACKEND_URL}/rows/${rowId}`,
        { headers },
        8000
      );

      if (existingRowRes.status === 404) {
        rowId = undefined;
      } else if (existingRowRes.ok) {
        if (typeof existingRowRes.data?.title === 'string') {
          existingRowTitle = existingRowRes.data.title;
        }
        let existingAnswers: Record<string, any> = {};
        const rawAnswers = existingRowRes.data?.choice_answers;
        if (rawAnswers) {
          try {
            existingAnswers = JSON.parse(rawAnswers);
          } catch {
            existingAnswers = {};
          }
        }
        if (priceParsed.min != null) {
          existingAnswers.min_price = priceParsed.min;
        }
        if (priceParsed.max != null) {
          existingAnswers.max_price = priceParsed.max;
        }

        reply.raw.write(`\n🔧 Updating price filter...`);
        const patchRes = await fetchJsonWithTimeout(
          `${BACKEND_URL}/rows/${rowId}`,
          {
            method: 'PATCH',
            headers,
            body: JSON.stringify({
              choice_answers: JSON.stringify(existingAnswers),
              ...(isRefinement && queryToUse
                ? {
                    title: queryToUse,
                    request_spec: {
                      item_name: queryToUse,
                    },
                  }
                : {}),
            }),
          },
          15000
        );
        if (!patchRes.ok && patchRes.status === 404) {
          rowId = undefined;
        } else {
          reply.raw.write(' Done!');
        }
      }
    }

    if (rowId && isRefinement && query) {
      if (!isPriceOnly) {
        const nextTitle = hasPriceConstraint && queryToUse ? queryToUse : query;
        reply.raw.write(`\n🔄 Updating row #${rowId} to "${nextTitle}"...`);
        const updateRes = await fetchJsonWithTimeout(
          `${BACKEND_URL}/rows/${rowId}`,
          {
            method: 'PATCH',
            headers,
            body: JSON.stringify({
              title: nextTitle,
              request_spec: {
                item_name: nextTitle,
              },
            }),
          },
          15000
        );
        if (updateRes.status === 404) {
          rowId = undefined;
        } else {
          reply.raw.write(' Done!');
        }
      }
    }

    if (!rowId) {
      if (isPriceOnly) {
        reply.raw.write(`\n⚠️ Price filter requires an active request. Try selecting a request first.`);
        reply.raw.end();
        return;
      }

      const createTitle = hasPriceConstraint && queryToUse ? queryToUse : query;
      reply.raw.write(`\n✅ Adding "${createTitle}" to your procurement board...`);

      const createResult = await fetchJsonWithTimeout(
        `${BACKEND_URL}/rows`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({
            title: createTitle,
            status: 'sourcing',
            project_id: projectId,
            request_spec: {
              item_name: createTitle,
              constraints: JSON.stringify({}),
            },
            choice_answers: JSON.stringify({
              ...(priceParsed.min != null ? { min_price: priceParsed.min } : {}),
              ...(priceParsed.max != null ? { max_price: priceParsed.max } : {}),
            }),
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

      // Emit structured row_created event to update UI immediately
      reply.raw.write(`event: row_created\n`);
      reply.raw.write(`data: ${JSON.stringify({ row: createResult.data })}\n\n`);

      saveChoiceFactorsToBackend(rowId, buildBasicChoiceFactors(createTitle), authHeaderValue).catch((err) => {
        fastify.log.error({ err, rowId }, 'Failed to save fallback choice_factors');
      });

      reply.raw.write(' Done!');
    }

    const searchLabel = hasPriceConstraint && queryToUse ? queryToUse : (isPriceOnly ? 'your request' : query);
    reply.raw.write(`\n🔍 Searching for "${searchLabel}"...`);

    // Emit action_started event to show searching spinner
    reply.raw.write(`event: action_started\n`);
    reply.raw.write(`data: ${JSON.stringify({ type: 'search', row_id: rowId })}\n\n`);

    const searchBody = isPriceOnly && existingRowTitle
      ? { query: existingRowTitle }
      : (hasPriceConstraint && !queryToUse
          ? {}
          : { query: hasPriceConstraint && queryToUse ? queryToUse : query });

    const searchResult = await fetchJsonWithTimeout(
      `${BACKEND_URL}/rows/${rowId}/search`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify(searchBody),
      },
      30000
    );

    if (searchResult.status == 404) {
      reply.raw.write(`\n⚠️ Error (404): Row not found`);
      reply.raw.end();
      return;
    }

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
  }

  // ============================================================================
  // UNIFIED CHAT HANDLER - Single LLM decision point, no heuristics
  // ============================================================================
  fastify.post('/api/chat', async (request, reply) => {
    try {
      const { messages, activeRowId, projectId, pendingClarification } = request.body as {
        messages: any[];
        activeRowId?: number;
        projectId?: number;
        pendingClarification?: {
          partial_constraints: Record<string, unknown>;
          missing_fields: string[];
        };
      };
      const authorization = request.headers.authorization;

      if (!process.env.OPENROUTER_API_KEY) {
        reply.status(500).send({ error: 'LLM not configured - OPENROUTER_API_KEY required' });
        return;
      }

      reply.raw.writeHead(200, {
        'Content-Type': 'text/event-stream; charset=utf-8',
        'Cache-Control': 'no-cache, no-transform',
        'Connection': 'keep-alive',
      });

      const writeEvent = (event: string, data: any) => {
        reply.raw.write(`event: ${event}\n`);
        reply.raw.write(`data: ${JSON.stringify(data ?? null)}\n\n`);
      };

      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (typeof authorization === 'string' && authorization) {
        headers['Authorization'] = authorization;
      }

      // Get last user message
      const lastUserMessage = Array.isArray(messages)
        ? [...messages].reverse().find((m: any) => m?.role === 'user')
        : null;
      const userMessage = typeof lastUserMessage?.content === 'string'
        ? lastUserMessage.content
        : typeof lastUserMessage?.content?.text === 'string'
          ? lastUserMessage.content.text
          : '';

      // Build conversation history for LLM context
      const conversationHistory = (messages || [])
        .filter((m: any) => m?.role === 'user' || m?.role === 'assistant')
        .map((m: any) => ({
          role: m.role as 'user' | 'assistant',
          content: typeof m.content === 'string' ? m.content : m.content?.text || '',
        }));

      // Fetch active row info if present
      let activeRow: ChatContext['activeRow'] = null;
      if (activeRowId) {
        const rowRes = await fetchJsonWithTimeoutRetry(
          `${BACKEND_URL}/rows/${activeRowId}`,
          { headers },
          20000, 1, 500
        );
        if (rowRes.ok && rowRes.data) {
          const choiceAnswers = rowRes.data.choice_answers ? JSON.parse(rowRes.data.choice_answers) : {};
          activeRow = {
            id: activeRowId,
            title: rowRes.data.title || '',
            constraints: choiceAnswers,
            // Read from actual row columns, NOT from choiceAnswers
            is_service: rowRes.data.is_service === true,
            service_category: rowRes.data.service_category || null,
          };
        }
      }

      // Fetch project info if present
      let activeProject: ChatContext['activeProject'] = null;
      if (projectId) {
        const projRes = await fetchJsonWithTimeoutRetry(
          `${BACKEND_URL}/projects/${projectId}`,
          { headers },
          20000, 1, 500
        );
        if (projRes.ok && projRes.data) {
          activeProject = { id: projectId, title: projRes.data.title || '' };
        }
      }

      // Helper: extract title from conversation when LLM returns default
      const extractTitleFromConversation = (): string => {
        // Find first user message that looks like a request
        for (const msg of conversationHistory) {
          if (msg.role === 'user' && msg.content.length > 3 && msg.content.length < 100) {
            // Capitalize first letter
            return msg.content.charAt(0).toUpperCase() + msg.content.slice(1);
          }
        }
        return userMessage.charAt(0).toUpperCase() + userMessage.slice(1);
      };

      // === SINGLE LLM DECISION ===
      fastify.log.info({ msg: 'Making unified decision', userMessage, activeRowId, pendingClarification: !!pendingClarification });
      
      const decision = await makeUnifiedDecision({
        userMessage,
        conversationHistory,
        activeRow,
        activeProject,
        pendingClarification: pendingClarification || null,
      });

      const intent = decision.intent;
      const action = decision.action;
      
      fastify.log.info({ 
        msg: 'Decision made', 
        actionType: action.type, 
        intent: { what: intent.what, category: intent.category, search_query: intent.search_query },
      });

      // Send assistant message
      writeEvent('assistant_message', { text: decision.message });

      // === INTENT-DRIVEN HELPERS ===
      const isService = intent.category === 'service';
      const serviceCategory = intent.service_type;
      const title = intent.what.charAt(0).toUpperCase() + intent.what.slice(1);
      const searchQuery = intent.search_query;
      const constraints = intent.constraints || {};

      // === HANDLE EACH ACTION TYPE ===

      if (action.type === 'ask_clarification') {
        // Need more info - store intent for next turn
        writeEvent('needs_clarification', {
          type: 'clarification',
          service_type: serviceCategory,
          title: title,
          partial_constraints: { 
            ...constraints, 
            title,
            what: intent.what,
            is_service: isService,
            service_category: serviceCategory,
            search_query: searchQuery,
          },
          missing_fields: action.missing_fields,
        });
        writeEvent('done', {});
        reply.raw.end();
        return;
      }

      if (action.type === 'disambiguate') {
        // Ambiguous query — present options to user (PRD 02)
        writeEvent('disambiguate', {
          options: (action as any).options,
          title: title,
        });
        writeEvent('done', {});
        reply.raw.end();
        return;
      }

      if (action.type === 'context_switch') {
        // User switched topics - create NEW row with NEW intent
        writeEvent('action_started', { type: 'create_row', title });
        const createRes = await fetchJsonWithTimeoutRetry(
          `${BACKEND_URL}/rows`,
          {
            method: 'POST',
            headers,
            body: JSON.stringify({
              title,
              status: 'sourcing',
              project_id: projectId ?? undefined,
              is_service: isService,
              service_category: serviceCategory,
              request_spec: { item_name: title, constraints: JSON.stringify(constraints) },
              choice_answers: JSON.stringify(constraints),
            }),
          },
          20000, 1, 500
        );

        if (!createRes.ok || !createRes.data?.id) {
          writeEvent('error', { message: createRes.data?.detail || 'Failed to create row' });
          reply.raw.end();
          return;
        }

        const rowId = Number(createRes.data.id);
        writeEvent('context_switch', { row: createRes.data });

        // Generate choice factors - pass isService for service-specific fields
        await generateAndSaveChoiceFactors(title, rowId, authorization, constraints, isService, serviceCategory);
        try {
          const updatedRowRes = await fetchJsonWithTimeoutRetry(
            `${BACKEND_URL}/rows/${rowId}`,
            { headers },
            15000, 1, 500
          );
          if (updatedRowRes.ok && updatedRowRes.data) {
            writeEvent('factors_updated', { row: updatedRowRes.data });
          } else {
            writeEvent('factors_updated', { row_id: rowId });
          }
        } catch (err: any) {
          fastify.log.warn({ err, rowId }, 'Failed to load row after factors update');
          writeEvent('factors_updated', { row_id: rowId });
        }

        // Use intent.search_query - NEVER conversation artifacts
        const ctxSearchQuery = searchQuery;
        writeEvent('action_started', { type: 'search', row_id: rowId, query: ctxSearchQuery });
        try {
          const final = await streamSearchResults(rowId, { query: ctxSearchQuery }, headers, (batch) => {
            writeEvent('search_results', {
              row_id: rowId,
              results: batch.results,
              provider_statuses: [batch.status],
              more_incoming: batch.more_incoming,
              provider: batch.provider,
            });
          });
          if (final.user_message) {
            writeEvent('search_results', {
              row_id: rowId,
              results: [],
              more_incoming: false,
              user_message: final.user_message,
            });
          }
        } catch (err: any) {
          writeEvent('error', { message: err?.message || 'Search failed' });
        }

        writeEvent('done', {});
        reply.raw.end();
        return;
      }

      if (action.type === 'create_row') {
        // New request - use intent for everything
        fastify.log.info({ msg: 'CREATE_ROW', isService, serviceCategory, searchQuery });

        writeEvent('action_started', { type: 'create_row', title });
        const createRes = await fetchJsonWithTimeoutRetry(
          `${BACKEND_URL}/rows`,
          {
            method: 'POST',
            headers,
            body: JSON.stringify({
              title,
              status: 'sourcing',
              project_id: projectId ?? undefined,
              is_service: isService,
              service_category: serviceCategory || null,
              request_spec: { item_name: title, constraints: JSON.stringify(constraints) },
              choice_answers: JSON.stringify(constraints),
            }),
          },
          20000, 1, 500
        );

        if (!createRes.ok || !createRes.data?.id) {
          writeEvent('error', { message: createRes.data?.detail || 'Failed to create row' });
          reply.raw.end();
          return;
        }

        const rowId = Number(createRes.data.id);
        writeEvent('row_created', { row: createRes.data });

        // Generate choice factors - pass isService for service-specific fields
        await generateAndSaveChoiceFactors(title, rowId, authorization, constraints, isService, serviceCategory);
        try {
          const updatedRowRes = await fetchJsonWithTimeoutRetry(
            `${BACKEND_URL}/rows/${rowId}`,
            { headers },
            15000, 1, 500
          );
          if (updatedRowRes.ok && updatedRowRes.data) {
            writeEvent('factors_updated', { row: updatedRowRes.data });
          } else {
            writeEvent('factors_updated', { row_id: rowId });
          }
        } catch (err: any) {
          fastify.log.warn({ err, rowId }, 'Failed to load row after factors update');
          writeEvent('factors_updated', { row_id: rowId });
        }

        // For services, fetch vendors. For products, search.
        if (isService && serviceCategory) {
          writeEvent('action_started', { type: 'fetch_vendors', row_id: rowId, category: serviceCategory });
          try {
            const vendorRes = await fetchJsonWithTimeoutRetry(
              `${BACKEND_URL}/outreach/vendors/${serviceCategory}`,
              { headers },
              15000, 1, 500
            );
            if (vendorRes.ok && vendorRes.data?.vendors && Array.isArray(vendorRes.data.vendors)) {
              const vendors = vendorRes.data.vendors;
              writeEvent('vendors_loaded', {
                row_id: rowId,
                category: serviceCategory,
                vendors,
              });
              // Persist vendors as bids so they survive page reload
              try {
                await fetchJsonWithTimeoutRetry(
                  `${BACKEND_URL}/outreach/rows/${rowId}/vendors`,
                  {
                    method: 'POST',
                    headers: { ...headers, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ category: serviceCategory, vendors }),
                  },
                  10000, 1, 500
                );
              } catch (persistErr: any) {
                fastify.log.warn({ err: persistErr }, 'Failed to persist vendors as bids');
              }
            } else {
              fastify.log.warn({ status: vendorRes.status, category: serviceCategory }, 'Vendor fetch returned non-ok or non-array');
            }
          } catch (err: any) {
            fastify.log.error({ err }, 'Failed to fetch vendors');
          }
        } else if (isService && !serviceCategory) {
          fastify.log.warn({ title }, 'Service but no category - using search_query from intent');
          writeEvent('action_started', { type: 'search', row_id: rowId, query: searchQuery });
          try {
            const final = await streamSearchResults(rowId, { query: searchQuery }, headers, (batch) => {
              writeEvent('search_results', {
                row_id: rowId,
                results: batch.results,
                provider_statuses: [batch.status],
                more_incoming: batch.more_incoming,
                provider: batch.provider,
              });
            });
            if (final.user_message) {
              writeEvent('search_results', {
                row_id: rowId,
                results: [],
                more_incoming: false,
                user_message: final.user_message,
              });
            }
          } catch (err: any) {
            writeEvent('error', { message: err?.message || 'Search failed' });
          }
        } else {
          // Product search for non-services - use intent.search_query
          writeEvent('action_started', { type: 'search', row_id: rowId, query: searchQuery });
          try {
            const final = await streamSearchResults(rowId, { query: searchQuery }, headers, (batch) => {
              writeEvent('search_results', {
                row_id: rowId,
                results: batch.results,
                provider_statuses: [batch.status],
                more_incoming: batch.more_incoming,
                provider: batch.provider,
              });
            });
            if (final.user_message) {
              writeEvent('search_results', {
                row_id: rowId,
                results: [],
                more_incoming: false,
                user_message: final.user_message,
              });
            }
          } catch (err: any) {
            writeEvent('error', { message: err?.message || 'Search failed' });
          }
        }

        writeEvent('done', {});
        reply.raw.end();
        return;
      }

      if (action.type === 'update_row') {
        // Refine existing row - use intent for constraints and search
        if (!activeRowId) {
          writeEvent('error', { message: 'No active row to update' });
          reply.raw.end();
          return;
        }

        const updateBody: any = {};
        const titleChanged = (activeRow?.title || '').trim().toLowerCase() !== title.trim().toLowerCase();
        const nextConstraints = titleChanged
          ? { ...constraints }
          : { ...(activeRow?.constraints || {}), ...constraints };
        if (titleChanged) {
          updateBody.title = title;
          updateBody.reset_bids = true;
          updateBody.request_spec = {
            item_name: title,
            constraints: JSON.stringify(nextConstraints),
          };
          updateBody.choice_answers = JSON.stringify(nextConstraints);
        } else if (Object.keys(constraints).length > 0) {
          updateBody.choice_answers = JSON.stringify(nextConstraints);
          updateBody.request_spec = {
            item_name: activeRow?.title || title,
            constraints: JSON.stringify(nextConstraints),
          };
        }

        writeEvent('action_started', { type: 'update_row', row_id: activeRowId });
        await fetchJsonWithTimeoutRetry(
          `${BACKEND_URL}/rows/${activeRowId}`,
          { method: 'PATCH', headers, body: JSON.stringify(updateBody) },
          20000, 1, 500
        );
        try {
          const updatedRowRes = await fetchJsonWithTimeoutRetry(
            `${BACKEND_URL}/rows/${activeRowId}`,
            { headers },
            15000, 1, 500
          );
          if (updatedRowRes.ok && updatedRowRes.data) {
            writeEvent('row_updated', { row: updatedRowRes.data });
          } else {
            writeEvent('row_updated', { row_id: activeRowId });
          }
        } catch (err: any) {
          fastify.log.warn({ err, rowId: activeRowId }, 'Failed to load row after update');
          writeEvent('row_updated', { row_id: activeRowId });
        }

        // Use intent category, fall back to activeRow for service detection
        const rowIsService = isService || activeRow?.is_service;
        const rowServiceCategory = serviceCategory || activeRow?.service_category;

        if (titleChanged || Object.keys(constraints).length > 0) {
          await generateAndSaveChoiceFactors(title, activeRowId, authorization, nextConstraints, rowIsService, rowServiceCategory);
          try {
            const updatedRowRes = await fetchJsonWithTimeoutRetry(
              `${BACKEND_URL}/rows/${activeRowId}`,
              { headers },
              15000, 1, 500
            );
            if (updatedRowRes.ok && updatedRowRes.data) {
              writeEvent('factors_updated', { row: updatedRowRes.data });
            } else {
              writeEvent('factors_updated', { row_id: activeRowId });
            }
          } catch (err: any) {
            fastify.log.warn({ err, rowId: activeRowId }, 'Failed to load row after factors update');
            writeEvent('factors_updated', { row_id: activeRowId });
          }
        }

        if (rowIsService && rowServiceCategory) {
          writeEvent('action_started', { type: 'fetch_vendors', row_id: activeRowId, category: rowServiceCategory });
          try {
            const vendorRes = await fetchJsonWithTimeoutRetry(
              `${BACKEND_URL}/outreach/vendors/${rowServiceCategory}`,
              { headers },
              15000, 1, 500
            );
            if (vendorRes.ok && vendorRes.data?.vendors && Array.isArray(vendorRes.data.vendors)) {
              const vendors = vendorRes.data.vendors;
              writeEvent('vendors_loaded', {
                row_id: activeRowId,
                category: rowServiceCategory,
                vendors,
              });
              // Persist vendors as bids so they survive page reload
              try {
                await fetchJsonWithTimeoutRetry(
                  `${BACKEND_URL}/outreach/rows/${activeRowId}/vendors`,
                  {
                    method: 'POST',
                    headers: { ...headers, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ category: rowServiceCategory, vendors }),
                  },
                  10000, 1, 500
                );
              } catch (persistErr: any) {
                fastify.log.warn({ err: persistErr }, 'Failed to persist vendors as bids');
              }
            }
          } catch (err: any) {
            fastify.log.error({ err }, 'Failed to fetch vendors for update_row');
          }
        } else if (searchQuery) {
          // Use intent.search_query for products
          writeEvent('action_started', { type: 'search', row_id: activeRowId, query: searchQuery });
          try {
            const final = await streamSearchResults(activeRowId, { query: searchQuery }, headers, (batch) => {
              writeEvent('search_results', {
                row_id: activeRowId,
                results: batch.results,
                provider_statuses: [batch.status],
                more_incoming: batch.more_incoming,
                provider: batch.provider,
              });
            });
            if (final.user_message) {
              writeEvent('search_results', {
                row_id: activeRowId,
                results: [],
                more_incoming: false,
                user_message: final.user_message,
              });
            }
          } catch (err: any) {
            writeEvent('error', { message: err?.message || 'Search failed' });
          }
        }

        writeEvent('done', {});
        reply.raw.end();
        return;
      }

      if (action.type === 'search') {
        // Just search on existing row - use intent.search_query
        if (!activeRowId) {
          writeEvent('error', { message: 'No active row to search' });
          reply.raw.end();
          return;
        }

        writeEvent('action_started', { type: 'search', row_id: activeRowId, query: searchQuery });
        try {
          const final = await streamSearchResults(activeRowId, { query: searchQuery }, headers, (batch) => {
            writeEvent('search_results', {
              row_id: activeRowId,
              results: batch.results,
              provider_statuses: [batch.status],
              more_incoming: batch.more_incoming,
              provider: batch.provider,
            });
          });
          if (final.user_message) {
            writeEvent('search_results', {
              row_id: activeRowId,
              results: [],
              more_incoming: false,
              user_message: final.user_message,
            });
          }
        } catch (err: any) {
          writeEvent('error', { message: err?.message || 'Search failed' });
        }

        writeEvent('done', {});
        reply.raw.end();
        return;
      }

      if (action.type === 'vendor_outreach') {
        // Service request - use intent.service_type for category
        if (!activeRowId) {
          writeEvent('error', { message: 'No active row for vendor outreach' });
          reply.raw.end();
          return;
        }

        const category = serviceCategory || activeRow?.service_category || 'service';
        writeEvent('action_started', { type: 'vendor_outreach', row_id: activeRowId, category });
        writeEvent('vendor_outreach', { row_id: activeRowId, category });
        writeEvent('done', {});
        reply.raw.end();
        return;
      }

      // Fallback - should not reach here
      writeEvent('done', {});
      reply.raw.end();
    } catch (err: any) {
      fastify.log.error({ err }, 'Chat error');
      try {
        reply.raw.write(`event: error\n`);
        reply.raw.write(`data: ${JSON.stringify({ message: err?.message || 'Chat processing failed' })}\n\n`);
      } catch {}
      reply.raw.end();
    }
  });

// Row Management Proxy
  fastify.get('/api/rows', async (request, reply) => {
  try {
    const headers: Record<string, string> = {};
    if (request.headers.authorization) {
      headers['Authorization'] = request.headers.authorization;
    }

    const result = await fetchJsonWithTimeoutRetry(
      `${BACKEND_URL}/rows`,
      { headers },
      20000,
      1,
      500
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
      const rowIsService = row?.is_service === true;
      const rowServiceCategory = row?.service_category || null;
      if (!process.env.GOOGLE_GENERATIVE_AI_API_KEY) {
        await saveChoiceFactorsToBackend(Number(id), buildBasicChoiceFactors(itemName), request.headers.authorization as string | undefined);
      } else {
        await generateAndSaveChoiceFactors(itemName, Number(id), request.headers.authorization as string | undefined, merged, rowIsService, rowServiceCategory);
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

    const result = await fetchJsonWithTimeoutRetry(
      `${BACKEND_URL}/projects`,
      { headers },
      20000,
      1,
      500
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

  // ============== LIKES ROUTES ==============
  fastify.post('/api/likes', async (request, reply) => {
    try {
      const authHeader = request.headers.authorization;
      const response = await fetch(`${BACKEND_URL}/likes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authHeader ? { Authorization: authHeader } : {}),
        },
        body: JSON.stringify(request.body),
      });
      const data = await response.json();
      reply.status(response.status).send(data);
    } catch (err) {
      fastify.log.error(err);
      reply.status(500).send({ error: 'Failed to create like' });
    }
  });

  fastify.delete('/api/likes', async (request, reply) => {
    try {
      const { row_id, bid_id, offer_url } = request.query as { row_id?: string; bid_id?: string; offer_url?: string };
      const authHeader = request.headers.authorization;
      const params = new URLSearchParams();
      if (row_id) params.set('row_id', row_id);
      if (bid_id) params.set('bid_id', bid_id);
      if (offer_url) params.set('offer_url', offer_url);
      const response = await fetch(`${BACKEND_URL}/likes?${params.toString()}`, {
        method: 'DELETE',
        headers: authHeader ? { Authorization: authHeader } : {},
      });
      const data = await response.json();
      reply.status(response.status).send(data);
    } catch (err) {
      fastify.log.error(err);
      reply.status(500).send({ error: 'Failed to delete like' });
    }
  });

  fastify.get('/api/likes', async (request, reply) => {
    try {
      const { row_id, bid_id } = request.query as { row_id?: string; bid_id?: string };
      const authHeader = request.headers.authorization;
      const params = new URLSearchParams();
      if (row_id) params.set('row_id', row_id);
      if (bid_id) params.set('bid_id', bid_id);
      const response = await fetch(`${BACKEND_URL}/likes?${params.toString()}`, {
        headers: authHeader ? { Authorization: authHeader } : {},
      });
      const data = await response.json();
      reply.status(response.status).send(data);
    } catch (err) {
      fastify.log.error(err);
      reply.status(500).send({ error: 'Failed to fetch likes' });
    }
  });

  fastify.get('/api/likes/counts', async (request, reply) => {
    try {
      const { row_id } = request.query as { row_id?: string };
      const authHeader = request.headers.authorization;
      const params = new URLSearchParams();
      if (row_id) params.set('row_id', row_id);
      const response = await fetch(`${BACKEND_URL}/likes/counts?${params.toString()}`, {
        headers: authHeader ? { Authorization: authHeader } : {},
      });
      const data = await response.json();
      reply.status(response.status).send(data);
    } catch (err) {
      fastify.log.error(err);
      reply.status(500).send({ error: 'Failed to fetch like counts' });
    }
  });

  // ============== COMMENTS ROUTES ==============
  fastify.post('/api/comments', async (request, reply) => {
    try {
      const authHeader = request.headers.authorization;
      const response = await fetch(`${BACKEND_URL}/comments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authHeader ? { Authorization: authHeader } : {}),
        },
        body: JSON.stringify(request.body),
      });
      const data = await response.json();
      reply.status(response.status).send(data);
    } catch (err) {
      fastify.log.error(err);
      reply.status(500).send({ error: 'Failed to create comment' });
    }
  });

  fastify.get('/api/comments', async (request, reply) => {
    try {
      const { row_id, bid_id } = request.query as { row_id?: string; bid_id?: string };
      const authHeader = request.headers.authorization;
      const params = new URLSearchParams();
      if (row_id) params.set('row_id', row_id);
      if (bid_id) params.set('bid_id', bid_id);
      const url = `${BACKEND_URL}/comments?${params.toString()}`;
      const response = await fetch(url, {
        headers: authHeader ? { Authorization: authHeader } : {},
      });
      const data = await response.json();
      reply.status(response.status).send(data);
    } catch (err) {
      fastify.log.error(err);
      reply.status(500).send({ error: 'Failed to fetch comments' });
    }
  });

  fastify.delete('/api/comments/:commentId', async (request, reply) => {
    try {
      const { commentId } = request.params as { commentId: string };
      const authHeader = request.headers.authorization;
      const response = await fetch(`${BACKEND_URL}/comments/${commentId}`, {
        method: 'DELETE',
        headers: authHeader ? { Authorization: authHeader } : {},
      });
      const data = await response.json();
      reply.status(response.status).send(data);
    } catch (err) {
      fastify.log.error(err);
      reply.status(500).send({ error: 'Failed to delete comment' });
    }
  });

  // Outreach Proxy - Vendor endpoints
  fastify.get('/api/outreach/vendors/:category', async (request, reply) => {
    try {
      const { category } = request.params as { category: string };
      const response = await fetch(`${BACKEND_URL}/outreach/vendors/${category}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await response.json();
      reply.status(response.status).send(data);
    } catch (err) {
      fastify.log.error(err);
      reply.status(500).send({ error: 'Failed to get vendors' });
    }
  });

  fastify.get('/api/outreach/check-service', async (request, reply) => {
    try {
      const query = (request.query as { query?: string }).query || '';
      const response = await fetch(`${BACKEND_URL}/outreach/check-service?query=${encodeURIComponent(query)}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await response.json();
      reply.status(response.status).send(data);
    } catch (err) {
      fastify.log.error(err);
      reply.status(500).send({ error: 'Failed to check service' });
    }
  });

  // Outreach Proxy - Row triggers
  fastify.post('/api/outreach/rows/:rowId/trigger', async (request, reply) => {
    try {
      const { rowId } = request.params as { rowId: string };
      const response = await fetch(`${BACKEND_URL}/outreach/rows/${rowId}/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request.body),
      });
      const data = await response.json();
      reply.status(response.status).send(data);
    } catch (err) {
      fastify.log.error(err);
      reply.status(500).send({ error: 'Failed to trigger outreach' });
    }
  });

  fastify.get('/api/outreach/rows/:rowId/status', async (request, reply) => {
    try {
      const { rowId } = request.params as { rowId: string };
      const response = await fetch(`${BACKEND_URL}/outreach/rows/${rowId}/status`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await response.json();
      reply.status(response.status).send(data);
    } catch (err) {
      fastify.log.error(err);
      reply.status(500).send({ error: 'Failed to get outreach status' });
    }
  });

  // Quotes Proxy (for seller quote intake - no auth required)
  fastify.get('/api/quotes/form/:token', async (request, reply) => {
    try {
      const { token } = request.params as { token: string };
      const response = await fetch(`${BACKEND_URL}/quotes/form/${token}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await response.json();
      reply.status(response.status).send(data);
    } catch (err) {
      fastify.log.error(err);
      reply.status(500).send({ error: 'Failed to load quote form' });
    }
  });

  fastify.post('/api/quotes/submit/:token', async (request, reply) => {
    try {
      const { token } = request.params as { token: string };
      const response = await fetch(`${BACKEND_URL}/quotes/submit/${token}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request.body),
      });
      const data = await response.json();
      reply.status(response.status).send(data);
    } catch (err) {
      fastify.log.error(err);
      reply.status(500).send({ error: 'Failed to submit quote' });
    }
  });

  fastify.post('/api/quotes/:quoteId/select', async (request, reply) => {
    try {
      const { quoteId } = request.params as { quoteId: string };
      const query = request.query as Record<string, string>;
      const params = new URLSearchParams(query).toString();
      const url = `${BACKEND_URL}/quotes/${quoteId}/select${params ? '?' + params : ''}`;
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await response.json();
      reply.status(response.status).send(data);
    } catch (err) {
      fastify.log.error(err);
      reply.status(500).send({ error: 'Failed to select quote' });
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
