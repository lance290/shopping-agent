import Fastify from 'fastify';
import cors from '@fastify/cors';
import fs from 'fs';
import path from 'path';
import { generateAndSaveChoiceFactors, GEMINI_MODEL_NAME, triageProviderQuery, generateChatPlan } from './llm';
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

      saveChoiceFactorsToBackend(rowId, buildBasicChoiceFactors(createTitle), authHeaderValue).catch((err) => {
        fastify.log.error({ err, rowId }, 'Failed to save fallback choice_factors');
      });

      reply.raw.write(' Done!');
    }

    const searchLabel = hasPriceConstraint && queryToUse ? queryToUse : (isPriceOnly ? 'your request' : query);
    reply.raw.write(`\n🔍 Searching for "${searchLabel}"...`);

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

  fastify.post('/api/chat', async (request, reply) => {
  try {
    const { messages, activeRowId, projectId } = request.body as {
      messages: any[];
      activeRowId?: number;
      projectId?: number;
    };
    const authorization = request.headers.authorization;

    if (!process.env.GOOGLE_GENERATIVE_AI_API_KEY) {
      reply.status(500).send({ error: 'LLM not configured' });
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

    let activeRowTitle: string | null = null;
    let projectTitle: string | null = null;
    if (activeRowId) {
      const rowRes = await fetchJsonWithTimeoutRetry(
        `${BACKEND_URL}/rows/${activeRowId}`,
        { headers },
        20000,
        1,
        500
      );
      if (rowRes.ok && typeof rowRes.data?.title === 'string') {
        activeRowTitle = rowRes.data.title;
      }
    }
    if (projectId) {
      const projRes = await fetchJsonWithTimeoutRetry(
        `${BACKEND_URL}/projects/${projectId}`,
        { headers },
        20000,
        1,
        500
      );
      if (projRes.ok && typeof projRes.data?.title === 'string') {
        projectTitle = projRes.data.title;
      }
    }

    const plan = await generateChatPlan({
      messages,
      activeRowId: activeRowId ?? null,
      projectId: projectId ?? null,
      activeRowTitle,
      projectTitle,
    });

    writeEvent('assistant_message', { text: plan.assistant_message || '' });

    let lastRowId: number | null = activeRowId ?? null;
    for (const action of plan.actions || []) {
      if (action.type === 'create_row') {
        const constraints = action.constraints && typeof action.constraints === 'object' ? action.constraints : {};
        const choiceAnswers: Record<string, any> = { ...constraints };
        if (typeof action.min_price === 'number' && Number.isFinite(action.min_price)) {
          choiceAnswers.min_price = action.min_price;
        }
        if (typeof action.max_price === 'number' && Number.isFinite(action.max_price)) {
          choiceAnswers.max_price = action.max_price;
        }
        const title = action.title;
        writeEvent('action_started', { type: 'create_row', title });
        const createRes = await fetchJsonWithTimeoutRetry(
          `${BACKEND_URL}/rows`,
          {
            method: 'POST',
            headers,
            body: JSON.stringify({
              title,
              status: 'sourcing',
              project_id: action.project_id ?? projectId ?? undefined,
              request_spec: {
                item_name: title,
                constraints: JSON.stringify(constraints),
              },
              choice_answers: JSON.stringify(choiceAnswers),
            }),
          },
          20000,
          1,
          500
        );
        if (!createRes.ok || !createRes.data?.id) {
          writeEvent('error', { message: createRes.data?.detail || createRes.data?.message || createRes.text || 'Failed to create row' });
          reply.raw.end();
          return;
        }
        lastRowId = Number(createRes.data.id);
        writeEvent('row_created', { row: createRes.data });

        if (typeof action.search_query === 'string' && action.search_query.trim().length > 0) {
          writeEvent('action_started', { type: 'search', row_id: lastRowId, query: action.search_query });
          const searchRes = await fetchJsonWithTimeoutRetry(
            `${BACKEND_URL}/rows/${lastRowId}/search`,
            {
              method: 'POST',
              headers,
              body: JSON.stringify({ query: action.search_query, providers: action.providers }),
            },
            30000,
            1,
            500
          );
          if (!searchRes.ok) {
            writeEvent('error', { message: searchRes.data?.detail || searchRes.data?.message || searchRes.text || 'Search failed' });
            reply.raw.end();
            return;
          }
          writeEvent('search_results', { row_id: lastRowId, results: searchRes.data?.results || [], provider_statuses: searchRes.data?.provider_statuses });
        }
      } else if (action.type === 'update_row') {
        const constraints = action.constraints && typeof action.constraints === 'object' ? action.constraints : undefined;
        const updateBody: any = {};
        if (typeof action.title === 'string' && action.title.trim().length > 0) {
          updateBody.title = action.title;
          updateBody.request_spec = {
            item_name: action.title,
            constraints: JSON.stringify(constraints || {}),
          };
        }

        const choiceAnswers: Record<string, any> = constraints ? { ...constraints } : {};
        if (typeof action.min_price === 'number' && Number.isFinite(action.min_price)) {
          choiceAnswers.min_price = action.min_price;
        }
        if (typeof action.max_price === 'number' && Number.isFinite(action.max_price)) {
          choiceAnswers.max_price = action.max_price;
        }
        if (Object.keys(choiceAnswers).length > 0) {
          updateBody.choice_answers = JSON.stringify(choiceAnswers);
        }

        writeEvent('action_started', { type: 'update_row', row_id: action.row_id });
        const updateRes = await fetchJsonWithTimeoutRetry(
          `${BACKEND_URL}/rows/${action.row_id}`,
          {
            method: 'PATCH',
            headers,
            body: JSON.stringify(updateBody),
          },
          20000,
          1,
          500
        );
        if (!updateRes.ok) {
          writeEvent('error', { message: updateRes.data?.detail || updateRes.data?.message || updateRes.text || 'Failed to update row' });
          reply.raw.end();
          return;
        }
        lastRowId = action.row_id;
        writeEvent('row_updated', { row: updateRes.data });

        if (typeof action.search_query === 'string' && action.search_query.trim().length > 0) {
          writeEvent('action_started', { type: 'search', row_id: lastRowId, query: action.search_query });
          const searchRes = await fetchJsonWithTimeoutRetry(
            `${BACKEND_URL}/rows/${lastRowId}/search`,
            {
              method: 'POST',
              headers,
              body: JSON.stringify({ query: action.search_query, providers: action.providers }),
            },
            30000,
            1,
            500
          );
          if (!searchRes.ok) {
            writeEvent('error', { message: searchRes.data?.detail || searchRes.data?.message || searchRes.text || 'Search failed' });
            reply.raw.end();
            return;
          }
          writeEvent('search_results', { row_id: lastRowId, results: searchRes.data?.results || [], provider_statuses: searchRes.data?.provider_statuses });
        }
      } else if (action.type === 'search') {
        const rowId = action.row_id;
        writeEvent('action_started', { type: 'search', row_id: rowId, query: action.query });
        const searchRes = await fetchJsonWithTimeoutRetry(
          `${BACKEND_URL}/rows/${rowId}/search`,
          {
            method: 'POST',
            headers,
            body: JSON.stringify({ query: action.query, providers: action.providers }),
          },
          30000,
          1,
          500
        );
        if (!searchRes.ok) {
          writeEvent('error', { message: searchRes.data?.detail || searchRes.data?.message || searchRes.text || 'Search failed' });
          reply.raw.end();
          return;
        }
        lastRowId = rowId;
        writeEvent('search_results', { row_id: rowId, results: searchRes.data?.results || [], provider_statuses: searchRes.data?.provider_statuses });
      }
    }

    writeEvent('done', { row_id: lastRowId });
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
