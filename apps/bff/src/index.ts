import Fastify from 'fastify';
import cors from '@fastify/cors';

const fastify = Fastify({
  logger: true,
});

// Register plugins
fastify.register(cors, {
  origin: process.env.CORS_ORIGIN || '*',
});

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

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

// Proxy search to backend (supports per-row search with constraints)
fastify.post('/api/search', async (request, reply) => {
  try {
    const body = request.body as any;
    const rowId = body?.rowId;

    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (request.headers.authorization) {
      headers['Authorization'] = request.headers.authorization as string;
    }

    const targetUrl = rowId
      ? `${BACKEND_URL}/rows/${rowId}/search`
      : `${BACKEND_URL}/v1/sourcing/search`;

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
  return {
    status: 'ok',
    timestamp: new Date().toISOString(),
    service: 'fastify-app',
    version: '0.1.0',
  };
});

// Root route
fastify.get('/', async () => {
  return { message: 'Hello from Fastify!' };
});

// Chat API
import { chatHandler, generateAndSaveChoiceFactors } from './llm';

fastify.post('/api/chat', async (request, reply) => {
  let headersSent = false;
  try {
    const { messages, activeRowId } = request.body as { messages: any[]; activeRowId?: number };
    const authorization = request.headers.authorization;
    const result = await chatHandler(messages, authorization, activeRowId);
    
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
        reply.raw.write(part.textDelta);
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
    
    const response = await fetch(`${BACKEND_URL}/rows`, { headers });
    
    if (response.status === 401) {
      reply.status(401).send({ error: 'Unauthorized' });
      return;
    }
    
    const data = await response.json();
    return data;
  } catch (err) {
    fastify.log.error(err);
    reply.status(500).send({ error: 'Failed to fetch rows' });
  }
});

fastify.post('/api/rows', async (request, reply) => {
  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (request.headers.authorization) {
      headers['Authorization'] = request.headers.authorization;
    }

    const response = await fetch(`${BACKEND_URL}/rows`, {
      method: 'POST',
      headers,
      body: JSON.stringify(request.body),
    });
    
    if (response.status === 401) {
      reply.status(401).send({ error: 'Unauthorized' });
      return;
    }
    
    const data = await response.json();
    return data;
  } catch (err) {
    fastify.log.error(err);
    reply.status(500).send({ error: 'Failed to create row' });
  }
});

fastify.get('/api/rows/:id', async (request, reply) => {
  try {
    const { id } = request.params as { id: string };
    const headers: Record<string, string> = {};
    if (request.headers.authorization) {
      headers['Authorization'] = request.headers.authorization;
    }

    const response = await fetch(`${BACKEND_URL}/rows/${id}`, { headers });
    
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
    reply.status(500).send({ error: 'Failed to fetch row' });
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

      await generateAndSaveChoiceFactors(row?.title || row?.request_spec?.item_name || 'product', Number(id), request.headers.authorization as string | undefined, merged);

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

// Start server
const start = async () => {
  try {
    const port = parseInt(process.env.PORT || '8080', 10);
    await fastify.listen({ port, host: '0.0.0.0' });
    fastify.log.info(`🚀 Server listening on port ${port}`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();
