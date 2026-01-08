# Infrastructure as Code (IaC) Strategy
## GCP + Railway Deployment Framework for Startup Interns

**Version:** 1.0
**Last Updated:** 2025-11-01
**Status:** Strategy Phase

---

## 🎯 Executive Summary

This framework will enable interns at startups to deploy complete applications (code, databases, microservices) in **less than 2 weeks** using Infrastructure as Code. We're constraining deployments to **GCP** and **Railway** to maintain focus and simplicity.

### **Key Design Principles**
1. **Intern-First**: Every tool choice optimized for learning curve and productivity
2. **Portable**: Docker-based to move between environments seamlessly
3. **Cost-Efficient**: Ephemeral environments + auto-cleanup to minimize spend
4. **Production-Ready**: Templates follow best practices from day one

---

## 📊 Current State Analysis

### **What's Already Built**

✅ **Pulumi-based GCP Deployment**
- Location: `infra/pulumi/index.js`
- Provisions Cloud Run services with automatic scaling
- Manages ephemeral environments per PR branch
- State storage in GCS buckets

✅ **GitHub Actions CI/CD**
- Location: `.github/workflows/pr-env.yml`
- Automatic PR environment creation
- Health checks and readiness validation
- Automated teardown on PR close

✅ **CFOI Development Workflow**
- 14 core workflows for rapid development
- Quality enforcement via git hooks
- AI accountability framework
- Test-driven but "Click-First" methodology

### **What's Missing for Complete IaC**

❌ **Railway Integration**: No Railway deployment templates
❌ **Docker Templates**: No language-specific Dockerfiles
❌ **Database Provisioning**: Limited database-as-code examples
❌ **Multi-Service Orchestration**: No docker-compose for local dev
❌ **Environment Parity**: Dev/staging/prod configuration management
❌ **Secrets Management**: Basic setup but needs standardization
❌ **Monitoring/Observability**: No infrastructure for logging/metrics

---

## 🏗️ Proposed Architecture

### **Three-Tier Deployment Strategy**

```
┌─────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT TARGETS                        │
└─────────────────────────────────────────────────────────────┘

1️⃣ LOCAL DEVELOPMENT (Docker Compose)
   ├── All services run locally
   ├── Hot reload for rapid iteration
   ├── Seed data for testing
   └── No cloud dependencies

2️⃣ EPHEMERAL ENVIRONMENTS (GCP Cloud Run via Pulumi)
   ├── Per-PR automated deployments
   ├── Managed databases (Cloud SQL, etc.)
   ├── Auto-cleanup on PR close
   └── Cost: $0.50-2.00 per environment/day

3️⃣ PRODUCTION (Railway + GCP Hybrid)
   ├── Railway: Primary application hosting
   ├── GCP: Databases, storage, heavy services
   ├── CDN for static assets
   └── Monitoring and alerting
```

### **Why This Hybrid Approach?**

**Railway for Applications** ✅
- Zero-config deployments (perfect for interns)
- Built-in CI/CD from git push
- Automatic HTTPS and domains
- Predictable pricing ($5-20/month per service)
- Excellent for monoliths and microservices

**GCP for Infrastructure** ✅
- Mature database offerings (Cloud SQL, Firestore)
- Better for high-traffic production workloads
- Enterprise-grade security and compliance
- More granular cost control
- Object storage (GCS) and CDN

---

## 🐳 Docker Standardization

### **Multi-Language Docker Templates**

We'll provide **production-ready Dockerfiles** for every common stack:

#### **Node.js/TypeScript (Current Focus)**
```dockerfile
# Multi-stage build for minimal production image
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .
EXPOSE 8080
CMD ["node", "dist/index.js"]
```

#### **Python (Django/Flask/FastAPI)**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:8080"]
```

#### **Go (APIs and Microservices)**
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

#### **Java (Spring Boot)**
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

### **Docker Compose for Local Development**

```yaml
# docker-compose.yml - Full local stack
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

## 🚀 Deployment Workflows

### **1. Local Development** (Day 1 for Interns)

```bash
# One command to start everything
docker-compose up

# Runs: App + Database + Redis + Any other services
# URL: http://localhost:8080
# Hot reload enabled for rapid iteration
```

### **2. PR Environments** (Automatic via GitHub Actions)

```
git push origin feature/user-auth
↓
GitHub Actions triggers
↓
Pulumi provisions GCP Cloud Run
↓
Docker image built and deployed
↓
PR comment with live URL
↓
Tests run against live environment
↓
Merge PR → Auto-cleanup
```

**Cost:** ~$1.50 per PR (typically 1-3 days)

### **3. Production Deployment** (Railway)

```bash
# Option A: Railway CLI (recommended for interns)
railway login
railway init
railway up

# Option B: Git integration (automatic)
git push origin main
# Railway auto-deploys from main branch
```

**Railway Advantages:**
- Zero configuration for most frameworks
- Automatic environment variables from Railway UI
- Built-in monitoring and logs
- One-click database provisioning
- Preview environments for branches

---

## 📦 Pulumi Strategy

### **Why Pulumi Over Terraform?**

✅ **Better for Interns**
- Use TypeScript/Python (familiar languages)
- No new DSL to learn (vs HCL)
- Better IDE support and type checking

✅ **Better for This Framework**
- Already have working Pulumi setup
- Easier to template and generate
- Native support for all GCP services
- State management simpler (GCS bucket)

✅ **Aligned with Roadmap**
- Google deprecating Cloud Deployment Manager (Dec 2025)
- Pulumi has same-day provider updates
- Active community and startup-friendly

### **Pulumi Module Structure**

```
infra/
├── pulumi/
│   ├── index.js                 # Main orchestration
│   ├── modules/
│   │   ├── cloud-run.js         # Cloud Run service
│   │   ├── cloud-sql.js         # Managed PostgreSQL
│   │   ├── firestore.js         # NoSQL database
│   │   ├── redis.js             # Memorystore Redis
│   │   ├── storage.js           # GCS buckets + CDN
│   │   └── secrets.js           # Secret Manager
│   ├── stacks/
│   │   ├── dev.yaml             # Development config
│   │   ├── staging.yaml         # Staging config
│   │   └── production.yaml      # Production config
│   └── package.json
```

### **Pulumi Templates for Common Patterns**

**Pattern 1: Simple Web App**
- Cloud Run + Cloud SQL (Postgres)
- GCS bucket for uploads
- Secret Manager for API keys

**Pattern 2: Microservices**
- Multiple Cloud Run services
- Firestore for shared state
- Pub/Sub for async messaging

**Pattern 3: API + Worker**
- Cloud Run for API
- Cloud Tasks for job queue
- Redis for caching

---

## 🔧 Railway Integration

### **New Railway Module** (To Be Built)

```
infra/
├── railway/
│   ├── railway.json             # Railway config
│   ├── templates/
│   │   ├── web-app.json         # Web application
│   │   ├── api.json             # REST/GraphQL API
│   │   ├── worker.json          # Background worker
│   │   └── cron.json            # Scheduled jobs
│   └── README.md
```

### **Railway Configuration** (railway.json)

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

### **Railway CLI Workflows**

```bash
# Workflow: /deploy-railway
# Auto-generated commands for interns

# 1. Login to Railway
railway login

# 2. Link to project (or create new)
railway link [project-id]

# 3. Set environment variables from .env
railway vars --env production < .env.production

# 4. Deploy current branch
railway up

# 5. Open in browser
railway open
```

---

## 💾 Database Strategy

### **Database Decision Matrix**

| Use Case | Local Dev | Ephemeral (PR) | Production |
|----------|-----------|----------------|------------|
| **SQL (Postgres)** | Docker | Cloud SQL | Railway Postgres |
| **NoSQL (Mongo)** | Docker | MongoDB Atlas | Railway MongoDB |
| **Graph (Neo4j)** | Docker | Neo4j Aura | Neo4j Aura |
| **Cache (Redis)** | Docker | Memorystore | Railway Redis |
| **Search (Elastic)** | Docker | Elastic Cloud | Elastic Cloud |

### **Pulumi Database Modules**

#### **Cloud SQL (PostgreSQL)**
```javascript
// infra/pulumi/modules/cloud-sql.js
const gcp = require("@pulumi/gcp");

exports.createPostgres = (name, config) => {
  const instance = new gcp.sql.DatabaseInstance(name, {
    databaseVersion: "POSTGRES_15",
    region: config.region,
    settings: {
      tier: config.tier || "db-f1-micro", // Free tier
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
    connectionName: instance.connectionName,
    connectionString: pulumi.interpolate`postgresql://${config.user}:${config.password}@/${config.databaseName}?host=/cloudsql/${instance.connectionName}`
  };
};
```

#### **Railway Postgres** (via CLI)
```bash
# Provision from Railway CLI
railway add postgres

# Connection string auto-injected as $DATABASE_URL
```

### **Migration Strategy**

```
tools/
├── db/
│   ├── migrate.sh               # Run migrations
│   ├── seed.sh                  # Seed data
│   ├── migrations/              # SQL migration files
│   │   ├── 001_initial.sql
│   │   ├── 002_add_users.sql
│   │   └── ...
│   └── seeds/                   # Seed data (JSON/SQL)
│       ├── dev.sql
│       ├── staging.sql
│       └── test.sql
```

---

## 🔐 Secrets Management

### **Three-Layer Secrets Strategy**

#### **Layer 1: Local Development** (.env.local)
```bash
# .env.local (gitignored)
DATABASE_URL=postgresql://localhost:5432/app_dev
REDIS_URL=redis://localhost:6379
API_KEY=test_key_12345
```

#### **Layer 2: CI/CD** (GitHub Secrets)
```yaml
# .github/workflows/pr-env.yml
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  API_KEY: ${{ secrets.API_KEY }}
```

#### **Layer 3: Production** (GCP Secret Manager + Railway)

**GCP Secret Manager** (via Pulumi)
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

**Railway Secrets** (via UI or CLI)
```bash
railway vars set API_KEY=prod_key_67890
railway vars set DATABASE_URL=postgresql://...
```

### **Secrets Template** (env.example)
```bash
# env.example - Committed to git as documentation

# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Cache
REDIS_URL=redis://host:6379

# Authentication
JWT_SECRET=your-secret-key-here
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_CLIENT_ID=your-client-id

# External APIs
SENDGRID_API_KEY=your-sendgrid-key
STRIPE_SECRET_KEY=sk_test_...

# Cloud Storage
GCS_BUCKET_NAME=your-bucket-name
GCS_SERVICE_ACCOUNT_KEY=base64-encoded-key

# Monitoring
SENTRY_DSN=https://...
```

---

## 📊 Cost Estimation

### **Monthly Cost Breakdown** (Per Project)

#### **Development (Local Only)**
- **Cost:** $0
- Docker Compose on laptop

#### **Ephemeral Environments (GCP)**
- **Per PR:** $0.50 - $2.00/day
- **Typical:** 3-5 active PRs at once
- **Monthly:** ~$50-100 (with auto-cleanup)

#### **Production (Railway + GCP)**

**Railway Tier** (Recommended: Developer Plan)
- **Base:** $5/month per service
- **Typical Setup:**
  - 1 Web App: $5
  - 1 API: $5
  - 1 Worker: $5
  - 1 Postgres: $5 (500 MB)
  - 1 Redis: $5 (100 MB)
- **Total:** ~$25/month

**GCP Services** (For Heavy Lifting)
- Cloud SQL (db-f1-micro): $7/month
- Cloud Storage: $0.02/GB/month
- Memorystore Redis (1GB): $40/month
- **Total:** ~$50/month

**Grand Total:** $75-150/month for production MVP

---

## 🛠️ Implementation Roadmap

### **Phase 1: Docker Foundation** (Week 1)
- [ ] Create language-specific Dockerfile templates
- [ ] Build docker-compose.yml for full local stack
- [ ] Document Docker best practices for interns
- [ ] Add Docker workflows to `/implement` command

### **Phase 2: Railway Integration** (Week 2)
- [ ] Create Railway configuration templates
- [ ] Build `/deploy-railway` workflow
- [ ] Document Railway environment setup
- [ ] Create Railway database provisioning guide

### **Phase 3: Pulumi Enhancement** (Week 3)
- [ ] Refactor Pulumi into reusable modules
- [ ] Add database provisioning (Cloud SQL, Firestore)
- [ ] Create multi-service orchestration templates
- [ ] Build `/provision` workflow for infrastructure

### **Phase 4: GCP + Railway Hybrid** (Week 4)
- [ ] Design connection patterns (Railway → GCP services)
- [ ] Create VPC and networking templates
- [ ] Build secrets synchronization tools
- [ ] Document hybrid deployment strategy

### **Phase 5: Monitoring & Observability** (Week 5)
- [ ] Add logging aggregation (Cloud Logging)
- [ ] Set up error tracking (Sentry integration)
- [ ] Create dashboard templates (Cloud Monitoring)
- [ ] Build alerting for production issues

### **Phase 6: Intern Documentation** (Week 6)
- [ ] Create video walkthrough (15-20 min)
- [ ] Build interactive tutorial (deploy first app)
- [ ] Write troubleshooting guide
- [ ] Create architecture decision records (ADRs)

---

## 🎓 Intern Success Metrics

### **Time to First Deployment**
- **Goal:** < 30 minutes from clone to live URL
- **Current:** ~2 hours (manual setup required)
- **Target:** One command (`./deploy.sh`)

### **Learning Curve**
- **Day 1:** Understand Docker basics
- **Day 2:** Deploy first app locally
- **Day 3:** Create first PR environment
- **Week 2:** Deploy to Railway production
- **Week 3:** Provision databases and services

### **Cost Management**
- **Goal:** < $200/month per intern project
- **Auto-cleanup:** 100% of ephemeral envs destroyed
- **Budget alerts:** Email at $100, $150, $200

---

## 🔄 Migration Path (Existing Projects)

### **For Projects Using Terraform**
```bash
# Option 1: Keep Terraform, add Railway for apps
# Option 2: Migrate to Pulumi gradually
pulumi import [terraform resources]
```

### **For Projects Using Heroku**
```bash
# Railway is Heroku-compatible
railway login
railway link [heroku-app-name]
railway up  # Migrates automatically
```

### **For Projects on Raw GCP**
```bash
# Existing GCP → Pulumi
pulumi import gcp:cloudrun/service:Service my-service projects/[project]/locations/[region]/services/[name]
```

---

## 📚 Reference Architecture

### **Example: SaaS Starter Kit**

```
Project Structure:
├── apps/
│   ├── web/                     # Next.js frontend
│   ├── api/                     # Node.js REST API
│   └── worker/                  # Background jobs
├── packages/
│   ├── database/                # Prisma ORM + migrations
│   ├── ui/                      # Shared components
│   └── config/                  # Shared config
├── infra/
│   ├── pulumi/                  # GCP infrastructure
│   │   ├── index.js
│   │   ├── modules/
│   │   └── stacks/
│   └── railway/                 # Railway configs
│       ├── web.json
│       ├── api.json
│       └── worker.json
├── docker-compose.yml           # Local development
├── Dockerfile.web               # Web app image
├── Dockerfile.api               # API image
└── Dockerfile.worker            # Worker image

Deployment Strategy:
├── Local: docker-compose up
├── PR Envs: GCP Cloud Run (via Pulumi)
└── Production: Railway (web, api, worker) + GCP (databases)
```

---

## 🎯 Next Steps

### **Immediate Actions** (This Sprint)
1. **Review this strategy** with team and stakeholders
2. **Validate Railway** as production platform (test deploy)
3. **Choose starter stack** (Node.js + Postgres recommended)
4. **Create first Docker template** for reference app

### **This Week**
1. Build `docker-compose.yml` for local development
2. Create Railway deployment workflow
3. Document Docker best practices
4. Test full cycle: local → PR → Railway

### **This Month**
1. Complete Pulumi modularization
2. Build database provisioning templates
3. Create intern onboarding tutorial
4. Deploy 2-3 pilot projects using new framework

---

## ❓ Open Questions

1. **Railway vs GCP Cloud Run for production?**
   - Current thinking: Railway for ease, GCP for scale
   - Need to test performance and cost at 10k+ users

2. **Multi-region from day 1?**
   - Adds complexity for interns
   - Recommend: Single region → Multi-region in Week 4+

3. **Kubernetes needed?**
   - Probably not for MVP stage
   - Railway + Cloud Run handle scaling well
   - Defer K8s until post-Series A

4. **Database migration tools?**
   - Prisma? Flyway? Liquibase? Raw SQL?
   - Recommend: Prisma for TypeScript, Alembic for Python

---

## 📝 Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-01 | Claude | Initial strategy document |

---

**Ready to build?** Let's start with Phase 1: Docker Foundation. 🚀
