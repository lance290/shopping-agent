# Neo4j (Graph Database) Setup

Use a graph database when relationships drive your product (recommendations,
knowledge graphs, fraud detection). This guide focuses on **Neo4j AuraDB** but
the checklist also applies to self-hosted deployments.

---

## 1. Create an AuraDB Instance

1. Sign in at <https://console.neo4j.io/>.
2. Create a **Free** database to get started.
3. Pick the region closest to your application.
4. Record the **bolt URI**, **username**, and **password** displayed after creation.

> For self-managed clusters (Docker, Kubernetes), ensure Bolt and HTTPS ports
> are reachable from Cloud Run or your VPC.

---

## 2. Configure Environment Variables

Update `.env` (and secrets) with the connection details:

```bash
NEO4J_URI=neo4j+s://<random-id>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=change-me-now
```

For on-prem instances, the URI typically looks like `bolt://hostname:7687`.

---

## 3. Driver Installation

Install the official driver inside your application:

```bash
npm install neo4j-driver
```

Create a shared driver module:

```ts
import neo4j from 'neo4j-driver';

export const driver = neo4j.driver(
  process.env.NEO4J_URI!,
  neo4j.auth.basic(process.env.NEO4J_USER!, process.env.NEO4J_PASSWORD!)
);
```

Close the driver on shutdown to avoid connection leaks.

---

## 4. Local Testing

Install Neo4j Desktop or run Docker for quick local experiments:

```bash
docker run -it \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/change-me-now \
  neo4j:5.13
```

Update `.env.local` to point to `bolt://localhost:7687` when running locally.

---

## 5. Security & Maintenance

- Rotate credentials regularly.
- Limit exposed IP ranges (AuraDB supports access lists).
- Enable point-in-time recovery (paid tiers).
- Capture decision notes in `.cfoi/branches/<branch>/DECISIONS.md`.

---

## 6. Integrating with Pulumi (Optional)

Pulumi does not yet provide a first-class Neo4j resource provider. For AuraDB,
provision manually and treat credentials as secrets. If you self-host on GCP,
use Compute Engine or GKE resources in `infra/pulumi/index.js` and expose Bolt
via internal load balancers.

