# Database & Data Store Overview

Most MVPs use at least one persistent store. This overview helps you pick the
right guide for your use case and capture the environment variables referenced
throughout the framework (`env.example`).

---

## Primary SQL Database

- **Recommended**: Cloud SQL for PostgreSQL or a managed PostgreSQL provider
  such as Neon or Supabase.
- Follow [`SERVICES_POSTGRES.md`](./SERVICES_POSTGRES.md) for provisioning,
  connection strings, and migrations.

Use when you need:

- Structured relational data
- Strong consistency guarantees
- Reporting / analytics friendly schema

---

## Document Store (MongoDB)

- Great for schemaless or rapidly evolving data models.
- Follow [`SERVICES_MONGODB.md`](./SERVICES_MONGODB.md) to configure MongoDB
  Atlas and populate `MONGODB_URI`.

---

## Graph Database (Neo4j)

- Useful when relationships are first-class (recommendations, social graphs).
- See [`SERVICES_NEO4J.md`](./SERVICES_NEO4J.md) for Aura DB setup or on-prem.

---

## Caching / Session Store (Redis)

- Ideal for rate limiting, background jobs, realtime leaderboards.
- Follow [`SERVICES_REDIS.md`](./SERVICES_REDIS.md) to configure Redis Cloud or
  GCP Memorystore.

---

## Decision Checklist

| Requirement                         | Recommended Guide                  |
|------------------------------------|------------------------------------|
| CRUD app, transactions             | [`SERVICES_POSTGRES.md`](./SERVICES_POSTGRES.md) |
| Flexible schema, JSON documents    | [`SERVICES_MONGODB.md`](./SERVICES_MONGODB.md)   |
| Relationship heavy, traversals     | [`SERVICES_NEO4J.md`](./SERVICES_NEO4J.md)       |
| Low latency caching or queues      | [`SERVICES_REDIS.md`](./SERVICES_REDIS.md)       |

You can mix and match — just keep environment variables in `.env` aligned with
the guides above.

---

## Infrastructure as Code

Store connection details securely (see [`SECRETS_MANAGEMENT.md`](./SECRETS_MANAGEMENT.md))
and add provisioning steps to `infra/pulumi` if you need fully automated
environments. For MVP velocity, it is often enough to provision managed services
manually, capture credentials in secrets, and refine the IaC later.

