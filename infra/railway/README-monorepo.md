# Railway Monorepo Deployment

This directory contains Railway configuration templates and automation for deploying monorepo applications.

---

## 🚂 Architecture Overview

The Railway monorepo setup supports:
- **Multiple Services**: Frontend, Backend, Admin Dashboard, Background Workers
- **Database Plugins**: PostgreSQL, Redis, MongoDB (via Railway plugins)
- **Environment Management**: Separate configurations for dev, staging, production
- **Automated Configuration**: Scripts to generate and manage service configs
- **Health Monitoring**: Built-in health checks and restart policies

---

## 📁 File Structure

```
infra/railway/
├── templates/                    # Railway service templates
│   ├── frontend.json            # React/Next.js frontend config
│   ├── backend.json             # Node.js/Express API config
│   ├── admin.json               # Admin dashboard config
│   ├── worker.json              # Background worker config
│   ├── web-app.json             # Generic web app config
│   ├── api.json                 # REST API config
│   └── cron.json                # Scheduled job config
├── scripts/                      # Deployment automation scripts
│   ├── railway-init.sh          # Initialize Railway project
│   ├── railway-deploy.sh        # Deploy services
│   ├── railway-provision-db.sh  # Provision databases
│   └── railway-logs.sh          # View service logs
├── config-railway.js            # Configuration helper script
├── README-monorepo.md           # This file
└── railway-project.json         # Project metadata (generated)
```

---

## 🚀 Quick Start

### 1. Install Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login
```

### 2. Set Up Monorepo Configuration

```bash
# Navigate to Railway directory
cd infra/railway

# Configure entire monorepo
node config-railway.js setup-monorepo ../../your-mvp

# This creates railway.json files for all services
```

### 3. Link Project to Railway

```bash
# Navigate to your project root
cd ../../your-mvp

# Link to Railway
railway link

# Select or create project
# Choose environment (production/staging)
```

### 4. Deploy Services

```bash
# Deploy all services
./infra/railway/scripts/railway-deploy.sh

# Or deploy individual services
cd apps/frontend && railway up
cd apps/backend && railway up
```

---

## 🎯 Service Templates

### Frontend Template (`frontend.json`)

**Use Case:** React/Next.js applications
**Default Port:** 3000
**Health Path:** `/`

**Features:**
- Optimized for static site generation
- Environment-specific build variables
- Graceful health checks
- Automatic restarts on failure

**Configuration:**
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "npm start",
    "healthcheckPath": "/",
    "restartPolicyType": "ON_FAILURE"
  },
  "environments": {
    "production": {
      "variables": {
        "NODE_ENV": "production",
        "NEXT_PUBLIC_ENV": "production"
      }
    }
  }
}
```

### Backend Template (`backend.json`)

**Use Case:** Node.js/Express APIs
**Default Port:** 8080
**Health Path:** `/health`

**Features:**
- API-optimized configuration
- Longer health check grace period
- Debug logging in non-production
- Database connection support

**Configuration:**
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "npm start",
    "healthcheckPath": "/health",
    "restartPolicyType": "ON_FAILURE"
  },
  "environments": {
    "production": {
      "variables": {
        "NODE_ENV": "production",
        "PORT": "8080",
        "LOG_LEVEL": "info"
      }
    }
  }
}
```

### Admin Template (`admin.json`)

**Use Case:** Admin dashboards and internal tools
**Default Port:** 3000
**Health Path:** `/`

**Features:**
- Similar to frontend but with admin-specific variables
- Protected deployment considerations
- Environment-specific branding

### Worker Template (`worker.json`)

**Use Case:** Background job processors
**Default Port:** N/A
**Health Path:** `/health`

**Features:**
- Always restart policy
- No exposed ports (internal service)
- Job processing optimizations

---

## ⚙️ Configuration Management

### Using the Configuration Helper

```bash
# List available templates
node config-railway.js list-templates

# Generate service configuration
node config-railway.js generate frontend ./apps/frontend

# Set up entire monorepo
node config-railway.js setup-monorepo ./my-mvp

# Validate configuration
node config-railway.js validate ./apps/backend

# List configured services
node config-railway.js list-services ./my-mvp

# Add environment variable
node config-railway.js add-env ./apps/backend API_URL https://api.example.com
```

### Manual Configuration

Create `railway.json` in your service directory:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "npm start",
    "healthcheckPath": "/health",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  },
  "environments": {
    "production": {
      "variables": {
        "NODE_ENV": "production",
        "PORT": "8080"
      }
    }
  }
}
```

---

## 🗄️ Database Setup

### Provision Databases

```bash
# Use the automated script
./scripts/railway-provision-db.sh

# Or use Railway CLI directly
railway add postgresql
railway add redis
railway add mongodb
```

### Database Configuration

**PostgreSQL:**
```bash
# Add PostgreSQL plugin
railway add postgresql

# Get connection string
railway variables get DATABASE_URL
```

**Redis:**
```bash
# Add Redis plugin
railway add redis

# Get connection string
railway variables get REDIS_URL
```

**MongoDB:**
```bash
# Add MongoDB plugin
railway add mongodb

# Get connection string
railway variables get MONGODB_URL
```

### Environment Variables

Railway automatically provides database connection variables:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `MONGODB_URL` - MongoDB connection string

Add custom variables:
```bash
# Set variable for current environment
railway variables set JWT_SECRET=your-secret-key

# Set variable for specific environment
railway variables set JWT_SECRET=your-secret-key --environment production
```

---

## 🌍 Environment Management

### Environment Configuration

Each service supports three environments:
- **production** - Live production environment
- **staging** - Staging/testing environment
- **development** - Development environment

### Environment-Specific Variables

```json
{
  "environments": {
    "production": {
      "variables": {
        "NODE_ENV": "production",
        "LOG_LEVEL": "info",
        "API_URL": "https://api.yourapp.com"
      }
    },
    "staging": {
      "variables": {
        "NODE_ENV": "production",
        "LOG_LEVEL": "debug",
        "API_URL": "https://staging-api.yourapp.com"
      }
    },
    "development": {
      "variables": {
        "NODE_ENV": "development",
        "LOG_LEVEL": "debug",
        "API_URL": "http://localhost:8080"
      }
    }
  }
}
```

### Switching Environments

```bash
# Switch to production environment
railway environment production

# Switch to staging environment
railway environment staging

# Deploy to current environment
railway up
```

---

## 🚢 Deployment Workflow

### 1. Initialize Project

```bash
# Navigate to project root
cd your-mvp

# Link to Railway
railway link

# Select project and environment
```

### 2. Configure Services

```bash
# Set up all services
./infra/railway/config-railway.js setup-monorepo .

# Validate configurations
./infra/railway/config-railway.js validate ./apps/frontend
./infra/railway/config-railway.js validate ./apps/backend
```

### 3. Deploy Services

```bash
# Deploy all services
./infra/railway/scripts/railway-deploy.sh

# Or deploy individually
cd apps/frontend && railway up
cd apps/backend && railway up
```

### 4. Monitor Deployment

```bash
# View deployment status
railway status

# View logs
railway logs

# View specific service logs
railway logs --service frontend
```

---

## 📊 Service Management

### List Services

```bash
# List all services in project
railway services

# List configured services in monorepo
node config-railway.js list-services .
```

### Service URLs

```bash
# Get service URLs
railway domains

# Example output:
# Frontend: https://your-app-production.up.railway.app
# Backend: https://your-api-production.up.railway.app
```

### Environment Variables

```bash
# List all variables
railway variables

# Get specific variable
railway variables get DATABASE_URL

# Set variable
railway variables set API_KEY=your-key
```

---

## 🔧 Advanced Configuration

### Custom Domains

```bash
# Add custom domain
railway domains add yourapp.com

# Add domain to specific service
railway domains add api.yourapp.com --service backend
```

### Build Configuration

**Custom Dockerfile:**
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile.custom",
    "buildContext": "."
  }
}
```

**Nixpacks Builder:**
```json
{
  "build": {
    "builder": "NIXPACKS"
  }
}
```

### Health Checks

**HTTP Health Check:**
```json
{
  "deploy": {
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "healthcheckGracePeriod": 30
  }
}
```

**Port Health Check:**
```json
{
  "deploy": {
    "healthcheckPort": 8080,
    "healthcheckTimeout": 100
  }
}
```

### Restart Policies

```json
{
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Available Policies:**
- `ON_FAILURE` - Restart on failure (default)
- `ALWAYS` - Always restart
- `NEVER` - Never restart

---

## 🛠️ Troubleshooting

### Common Issues

**Build Failures:**
```bash
# Check build logs
railway logs --build

# Common causes:
# - Missing Dockerfile
# - Invalid package.json
# - Build timeout
```

**Health Check Failures:**
```bash
# Check service logs
railway logs

# Verify health endpoint
curl https://your-service.up.railway.app/health
```

**Environment Variable Issues:**
```bash
# Check variables
railway variables

# Test variable injection
railway variables get DATABASE_URL
```

**Database Connection Issues:**
```bash
# Check database status
railway status

# Test connection locally
# Use Railway variables in local .env
```

### Debug Commands

```bash
# View project status
railway status

# View service logs
railway logs --service <service-name>

# View build logs
railway logs --build

# View environment variables
railway variables

# View domains
railway domains

# Redeploy service
railway up --service <service-name>
```

### Recovery Commands

```bash
# Restart service
railway restart

# Redeploy all services
railway up

# Reset environment
railway environment reset
```

---

## 📈 Best Practices

### Performance Optimization

1. **Use appropriate builders:**
   - `DOCKERFILE` for custom builds
   - `NIXPACKS` for standard Node.js apps

2. **Optimize Docker images:**
   - Multi-stage builds
   - Minimal base images
   - Proper caching

3. **Configure health checks:**
   - Fast health endpoints
   - Appropriate timeouts
   - Grace periods for startup

### Security

1. **Environment variables:**
   - Use Railway variables for secrets
   - Don't commit secrets to git
   - Use different keys per environment

2. **Service isolation:**
   - Separate databases per service
   - Use Railway's network isolation
   - Implement proper authentication

### Cost Management

1. **Right-size services:**
   - Monitor resource usage
   - Use appropriate instance sizes
   - Scale down when possible

2. **Optimize databases:**
   - Choose appropriate database tiers
   - Implement connection pooling
   - Use caching when possible

---

## 📚 Additional Resources

- [Railway Documentation](https://docs.railway.app/)
- [Railway CLI Reference](https://docs.railway.app/develop/cli)
- [Railway Service Configuration](https://docs.railway.app/develop/services)
- [Railway Environment Variables](https://docs.railway.app/develop/variables)

---

**Questions?** Check the [main README](../README.md) or create an issue on GitHub.
