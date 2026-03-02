# IaC Quick Reference Guide
**GCP + Railway Deployment Framework**

*Extracted from strategy docs - all actionable content, zero fluff*

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│           HYBRID DEPLOYMENT STRATEGY             │
└─────────────────────────────────────────────────┘

Railway (Application Layer)
├── Web apps, APIs, workers
├── Zero-config deployments
├── $5-20/month per service
└── Perfect for intern productivity

         ↕️ Secure API connections

GCP (Infrastructure Layer)
├── Databases (Cloud SQL, Firestore)
├── Storage (GCS + CDN)
├── Cache (Memorystore Redis)
└── Enterprise-grade scalability
```

**Three-Tier Strategy:**
1. **Local:** Docker Compose (zero cloud costs)
2. **Ephemeral:** GCP Cloud Run via Pulumi (per-PR environments)
3. **Production:** Railway + GCP hybrid

---

## Docker Templates

### Python (Django/Flask/FastAPI)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:8080"]
```

### Go (APIs and Microservices)

```dockerfile
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.* ./
RUN go mod download
COPY . .
RUN go build -o main .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/main /main
EXPOSE 8080
CMD ["/main"]
```

### Java (Spring Boot)

```dockerfile
FROM eclipse-temurin:17-jdk-alpine AS builder
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN ./mvnw package -DskipTests

FROM eclipse-temurin:17-jre-alpine
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 8080
CMD ["java", "-jar", "app.jar"]
```

### Docker Compose (Full Local Stack)

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/app_dev
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./src:/app/src  # Hot reload
    depends_on:
      - db
      - redis

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=app_dev
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

---

## Pulumi Module Structure

```
infra/pulumi/
├── index.js              # Main orchestration
├── modules/
│   ├── cloud-run.js      # Cloud Run service
│   ├── cloud-sql.js      # Managed PostgreSQL
│   ├── firestore.js      # NoSQL database
│   ├── redis.js          # Memorystore Redis
│   ├── storage.js        # GCS buckets + CDN
│   └── secrets.js        # Secret Manager
├── stacks/
│   ├── dev.yaml
│   ├── staging.yaml
│   └── production.yaml
└── package.json
```

### Cloud SQL Module Example

```javascript
// infra/pulumi/modules/cloud-sql.js
const gcp = require("@pulumi/gcp");

exports.createPostgres = (name, config) => {
  const instance = new gcp.sql.DatabaseInstance(name, {
    databaseVersion: "POSTGRES_15",
    region: config.region,
    settings: {
      tier: config.tier || "db-f1-micro",
      diskSize: config.diskSize || 10,
      backupConfiguration: {
        enabled: true,
        startTime: "03:00"
      },
      ipConfiguration: {
        ipv4Enabled: true,
        authorizedNetworks: config.allowedIPs || []
      }
    },
    deletionProtection: config.production || false
  });

  const database = new gcp.sql.Database(`${name}-db`, {
    instance: instance.name,
    name: config.databaseName || "app"
  });

  return {
    instance,
    database,
    connectionName: instance.connectionName
  };
};
```

---

## Railway Configuration

### railway.json

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "node dist/index.js",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Railway CLI Workflow

```bash
# 1. Login
railway login

# 2. Link to project (or create new)
railway link [project-id]

# 3. Set environment variables
railway vars --env production < .env.production

# 4. Deploy
railway up

# 5. Open in browser
railway open
```

---

## Database Decision Matrix

| Use Case | Local Dev | Ephemeral (PR) | Production |
|----------|-----------|----------------|------------|
| **SQL (Postgres)** | Docker | Cloud SQL | Railway Postgres |
| **NoSQL (Mongo)** | Docker | MongoDB Atlas | Railway MongoDB |
| **Graph (Neo4j)** | Docker | Neo4j Aura | Neo4j Aura |
| **Cache (Redis)** | Docker | Memorystore | Railway Redis |
| **Search (Elastic)** | Docker | Elastic Cloud | Elastic Cloud |

---

## Cost Estimates

### Per-Project Production Costs

| Component | Monthly Cost |
|-----------|-------------|
| Railway services (5 services) | $25 |
| GCP Cloud SQL (db-f1-micro) | $7 |
| GCP Storage + CDN | $5 |
| GCP Redis (optional) | $40 |
| **Total (typical)** | **$35-75** |

### Ephemeral PR Environments

- **Per PR:** $0.50-2.00/day (GCP Cloud Run)
- **Typical:** 3-5 active PRs
- **Monthly:** ~$50-100 (auto-cleanup on PR close)

---

## Implementation Checklist

### Week 1: Docker Foundation
- [ ] Python Dockerfile template
- [ ] Go Dockerfile template
- [ ] Java Dockerfile template
- [ ] docker-compose.yml for full stack
- [ ] Docker onboarding documentation

### Week 2: Railway Integration
- [ ] Railway configuration templates (web-app.json, api.json, worker.json, cron.json)
- [ ] `/deploy-railway` workflow
- [ ] Railway CLI wrapper scripts
- [ ] Railway database provisioning guide
- [ ] Test deployment walkthrough video

### Week 3: Pulumi Enhancement
- [ ] Refactor Pulumi into modules
- [ ] cloud-sql.js module
- [ ] storage.js module (GCS + CDN)
- [ ] secrets.js module (Secret Manager)
- [ ] `/provision` workflow command

### Week 4: GCP + Railway Hybrid
- [ ] Connection patterns (Railway → GCP services)
- [ ] VPC peering configuration
- [ ] Secrets sync scripts (GCP ↔ Railway)
- [ ] Hybrid deployment guide

### Week 5: Observability
- [ ] Structured logging setup (Winston/Pino)
- [ ] Sentry integration
- [ ] Cloud Monitoring dashboards
- [ ] Alerting policies (error rate, resource usage)

### Week 6: Documentation
- [ ] Video 1: Local development with Docker Compose (10 min)
- [ ] Video 2: Deploy to Railway (8 min)
- [ ] Video 3: Database provisioning (12 min)
- [ ] Video 4: Production readiness checklist (15 min)
- [ ] Interactive tutorial scripts
- [ ] Troubleshooting guides

---

## Secrets Management

### Local Development (.env.local)
```bash
DATABASE_URL=postgresql://localhost:5432/app_dev
REDIS_URL=redis://localhost:6379
API_KEY=test_key_12345
```

### Production (GCP Secret Manager via Pulumi)
```javascript
const secret = new gcp.secretmanager.Secret("api-key", {
  secretId: "api-key",
  replication: { automatic: {} }
});

const version = new gcp.secretmanager.SecretVersion("api-key-v1", {
  secret: secret.id,
  secretData: config.requireSecret("apiKey")
});
```

### Railway Secrets (via CLI)
```bash
railway vars set API_KEY=prod_key_67890
railway vars set DATABASE_URL=postgresql://...
```

---

## Deployment Workflows

### Local → PR → Production

```
┌──────────────┐
│ Local Dev    │  docker-compose up
│ (Docker)     │  URL: http://localhost:8080
└──────────────┘
        ↓
┌──────────────┐
│ PR Env       │  git push → GitHub Actions → Pulumi
│ (GCP)        │  Auto-comment with live URL
└──────────────┘  Auto-cleanup on merge/close
        ↓
┌──────────────┐
│ Production   │  railway up (or git push main)
│ (Railway)    │  Apps on Railway, DBs on GCP
└──────────────┘
```

---

## Intern Success Metrics

### Time to First Deployment
- **Goal:** < 30 minutes (clone → live URL)
- **Current baseline:** ~2 hours

### Learning Curve
- **Day 1:** Deploy app locally with Docker Compose
- **Day 2:** Deploy to Railway
- **Week 1:** Provision databases
- **Week 2:** Ship to production with monitoring

### Cost Management
- **Target:** < $200/month per project
- **Auto-cleanup:** 100% of ephemeral environments
- **Budget alerts:** $100, $150, $200 thresholds

---

## Reference Links

- Existing Node.js template: `infra/docker/templates/nodejs/`
- Existing Pulumi setup: `infra/pulumi/index.js`
- Full strategy (archive): `docs/strategy/IAC_STRATEGY.md`
- Implementation plan (archive): `docs/strategy/IMPLEMENTATION_PLAN.md`
- Next-stage plan: `docs/strategy/IAC_NEXT_STAGE.md`

---

**This is your working reference. The verbose strategy docs are archived for historical context only.**
