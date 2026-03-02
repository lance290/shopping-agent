# Redis Setup (Cache, Sessions, Queues)

Redis provides sub-millisecond reads and is perfect for caching, rate limiting,
background jobs, and session storage. Pick a managed provider to avoid running
stateful infrastructure yourself.

---

## 1. Choose a Provider

| Option             | When to use                                             |
|--------------------|---------------------------------------------------------|
| **Redis Cloud**    | Fast setup, global regions, generous free tier          |
| **GCP Memorystore**| Tight integration with Cloud Run, private VPC access    |
| **Upstash**        | HTTP-based, usage-based pricing, serverless friendly    |

The connection string format differs slightly per provider but all map cleanly
to `REDIS_URL` in `.env`.

---

## 2. Provision Redis Cloud (Example)

1. Sign in at <https://app.redislabs.com/>.
2. Create a **Fixed** plan with the smallest memory size.
3. Choose a region that matches your application.
4. Enable TLS (preferred) and record the **Public Endpoint**.
5. Create a database password if not generated automatically.

Set `.env`:

```bash
REDIS_URL=rediss://default:<password>@redis-12345.c12.us-east-1-3.ec2.cloud.redislabs.com:12345
```

---

## 3. GCP Memorystore (VPC-only)

Memorystore is private by default. To connect from Cloud Run you need a VPC
connector:

1. Create a **Serverless VPC Connector** in `us-central1`.
2. Provision a Redis instance in Memorystore (Basic Tier is enough).
3. Add the connector to your Cloud Run service (Pulumi or console).
4. Use the private IP in `REDIS_URL`, e.g., `redis://10.0.0.5:6379`.

Update `infra/pulumi/index.js` if you want Pulumi to create the connector and
attach it automatically.

---

## 4. Client Configuration

Install a client in your application:

```bash
npm install redis
```

```ts
import { createClient } from 'redis';

export const redis = createClient({ url: process.env.REDIS_URL });
redis.on('error', (err) => console.error('Redis error', err));
await redis.connect();
```

Remember to `await redis.quit()` during shutdown and in tests.

---

## 5. Env & Secrets

- Store `REDIS_URL` in your secret manager (`SECRETS_MANAGEMENT.md`).
- Add a GitHub secret if CI needs to hit Redis (e.g., integration tests).
- Document Redis usage in `.cfoi/branches/<branch>/DECISIONS.md` so everyone
  knows which features rely on it.

---

## 6. Monitoring

Most providers expose dashboards for memory usage, connections, and latency.
Set up alerts for:

- Memory > 80%
- Evictions
- Connection limits

Small proactive tweaks keep caches healthy and prevent production surprises.

