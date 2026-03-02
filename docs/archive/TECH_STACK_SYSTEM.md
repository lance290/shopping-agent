# Tech Stack Deployment System

**Compose any combination of technologies and deploy to GCP/Railway with Pulumi.**

## Overview

This system provides:
1. **Modular technology templates** (NextJS, NestJS, Fastify, Svelte)
2. **Tech-aware Pulumi configuration** (compose any stack)
3. **Automated deployment** (GCP Cloud Run + Railway)

## Available Technologies

### Frontend
- **nextjs** - Next.js 15 with App Router + TypeScript
- **svelte** - SvelteKit with TypeScript
- **react-vite** - React + Vite (coming soon)

### Backend
- **nestjs** - NestJS with TypeScript + validation
- **fastify** - Fastify with TypeScript + performance
- **nodejs** - Generic Node.js + TypeScript

### Databases
- **postgres** - PostgreSQL (Cloud SQL)
- **redis** - Redis (Memorystore)
- **mongodb** - MongoDB Atlas
- **neo4j** - Neo4j (coming soon)

## Quick Start

### 1. List Available Options

```bash
# See all preset combinations
node infra/pulumi/config-tech-stack.js list-presets

# See all available technologies
node infra/pulumi/config-tech-stack.js list-tech
```

### 2. Generate Stack Configuration

**Option A: Use a preset**
```bash
node infra/pulumi/config-tech-stack.js generate nextjs-nestjs dev
```

**Option B: Custom composition**
```bash
node infra/pulumi/config-tech-stack.js custom dev \
  --frontend=nextjs \
  --backend=fastify \
  --postgres \
  --redis
```

### 3. Deploy with Pulumi

```bash
cd infra/pulumi
pulumi stack select dev
pulumi up
```

## Available Presets

| Preset | Frontend | Backend | Databases |
|--------|----------|---------|-----------|
| `nextjs-nestjs` | Next.js | NestJS | PostgreSQL |
| `nextjs-fastify` | Next.js | Fastify | PostgreSQL |
| `svelte-nestjs` | Svelte | NestJS | PostgreSQL |
| `svelte-fastify` | Svelte | Fastify | PostgreSQL |
| `api-nestjs` | None | NestJS | PostgreSQL + Redis |
| `api-fastify` | None | Fastify | PostgreSQL + Redis |
| `nextjs-only` | Next.js | None | None |
| `svelte-only` | Svelte | None | None |

## Template Structure

Each technology template includes:
- ✅ **Dockerfile** - Multi-stage optimized build
- ✅ **Health check** - `/health` endpoint
- ✅ **TypeScript** - Strict type checking
- ✅ **Production ready** - Security hardened
- ✅ **Docker optimized** - Minimal image size
- ✅ **Cloud Run compatible** - Railway + GCP

## Directory Structure

```
infra/
├── docker/
│   └── templates/
│       ├── nextjs/          # Next.js 15 + App Router
│       ├── nestjs/          # NestJS + validation
│       ├── fastify/         # Fastify + performance
│       ├── svelte/          # SvelteKit
│       └── nodejs/          # Generic Node.js
├── pulumi/
│   ├── config-tech-stack.js # Tech-aware config generator
│   ├── index-tech-stack.js  # Tech-aware deployment
│   ├── config-monorepo.js   # Legacy generic config
│   └── index-monorepo.js    # Legacy generic deployment
└── railway/
    └── templates/           # Railway-specific configs
```

## Usage Examples

### Example 1: Full-Stack SaaS

```bash
# Next.js frontend + NestJS backend + PostgreSQL + Redis
node infra/pulumi/config-tech-stack.js custom production \
  --frontend=nextjs \
  --backend=nestjs \
  --postgres \
  --redis
```

### Example 2: API Service

```bash
# Fastify API + PostgreSQL + Redis
node infra/pulumi/config-tech-stack.js generate api-fastify staging
```

### Example 3: Static Frontend

```bash
# Svelte frontend only (SSR or static)
node infra/pulumi/config-tech-stack.js generate svelte-only dev
```

### Example 4: Custom Combo

```bash
# Svelte + Fastify + PostgreSQL + MongoDB + Redis
node infra/pulumi/config-tech-stack.js custom dev \
  --frontend=svelte \
  --backend=fastify \
  --postgres \
  --mongodb \
  --redis
```

## Configuration Management

### View Current Config

```bash
node infra/pulumi/config-tech-stack.js get-config dev
```

### Modify Config

```bash
# Update PostgreSQL tier
pulumi config set postgresTier db-g1-small

# Update frontend resources
pulumi config set frontendCpu 2000m
pulumi config set frontendMemory 1Gi
```

## Deployment Workflow

1. **Generate config** → Creates `Pulumi.<stack>.yaml`
2. **Review settings** → Check resources and costs
3. **Deploy infrastructure** → `pulumi up`
4. **Build & push images** → Docker images to GCR
5. **Access services** → URLs exported by Pulumi

## Cost Estimation

```bash
# Rough monthly cost estimate
node infra/pulumi/config-monorepo.js estimate-cost dev
```

**Typical costs:**
- Frontend (Cloud Run): $0 - $50/mo
- Backend (Cloud Run): $0 - $100/mo
- PostgreSQL (f1-micro): $10 - $50/mo
- Redis (Basic 1GB): $7 - $30/mo
- **Total**: ~$20 - $200/mo depending on traffic

## Integration with /bootup

The `/bootup` workflow will use this system to:
1. Ask user for tech preferences
2. Generate Pulumi config
3. Copy appropriate templates
4. Initialize git + CFOI
5. Create docker-compose for local dev
6. Provide deployment commands

## Extending the System

### Add a New Technology

1. Create template in `infra/docker/templates/<tech>/`
2. Add entry to `techOptions` in `config-tech-stack.js`
3. Add Docker image mapping in `index-tech-stack.js`
4. Create preset combinations

### Add Database Support

1. Add to `techOptions.databases` in `config-tech-stack.js`
2. Add provisioning logic in `index-tech-stack.js`
3. Update presets to include new database

## Next Steps

1. ✅ NextJS, NestJS, Fastify, Svelte templates created
2. ✅ Tech-aware Pulumi configuration system built
3. ⏳ Integrate with `/bootup` workflow
4. ⏳ Add Railway deployment support
5. ⏳ Add more frontend options (React-Vite, Angular)
6. ⏳ Add more backend options (Go, Rust)
7. ⏳ Add observability templates

## See Also

- `infra/docker/templates/*/README.md` - Individual tech docs
- `infra/pulumi/README-monorepo.md` - Legacy generic system
- `.windsurf/workflows/bootup.md` - Scaffolding workflow
- `.windsurf/workflows/deploy.md` - Deployment workflow
