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

// Proxy search to backend
fastify.post('/api/search', async (request, reply) => {
  try {
    const response = await fetch(`${BACKEND_URL}/v1/sourcing/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request.body),
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
import { chatHandler } from './llm';

fastify.post('/api/chat', async (request, reply) => {
  try {
    const { messages } = request.body as { messages: any[] };
    const result = await chatHandler(messages);
    return result.toDataStreamResponse();
  } catch (err) {
    fastify.log.error(err);
    reply.status(500).send({ error: 'Chat processing failed' });
  }
});

// Row Management Proxy
fastify.get('/api/rows', async (request, reply) => {
  try {
    const response = await fetch(`${BACKEND_URL}/rows`);
    const data = await response.json();
    return data;
  } catch (err) {
    fastify.log.error(err);
    reply.status(500).send({ error: 'Failed to fetch rows' });
  }
});

fastify.post('/api/rows', async (request, reply) => {
  try {
    const response = await fetch(`${BACKEND_URL}/rows`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request.body),
    });
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
    const response = await fetch(`${BACKEND_URL}/rows/${id}`);
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
