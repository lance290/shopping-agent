# Railway Automation

Production deployment automation for Railway platform with GCP hybrid architecture.

---

## 📁 Structure

```
infra/railway/
├── templates/              # Railway configuration templates
│   ├── web-app.json       # Web application config
│   ├── api.json           # REST/GraphQL API config
│   ├── worker.json        # Background worker config
│   └── cron.json          # Scheduled job config
├── scripts/               # CLI automation scripts
│   ├── railway-init.sh    # Project initialization
│   ├── railway-deploy.sh  # Automated deployment
│   ├── railway-provision-db.sh  # Database provisioning
│   └── railway-logs.sh    # Log viewing utility
└── README.md              # This file
```

---

## 🚀 Quick Start

### 1. Install Railway CLI

```bash
# Via npm (recommended)
npm install -g @railway/cli

# Or via Homebrew (macOS)
brew install railway

# Verify installation
railway --version
```

### 2. Initialize Railway Project

```bash
./infra/railway/scripts/railway-init.sh
```

This script will:
- Check Railway CLI installation
- Log you into Railway (if needed)
- Link to existing project or create new one
- Optionally set environment variables from `.env.production`

### 3. Deploy to Railway

```bash
./infra/railway/scripts/railway-deploy.sh
```

This script will:
- Run pre-flight checks
- Confirm deployment details
- Deploy to production or staging
- Record deployment in `proof/deployments/railway.md`

---

## 📋 Configuration Templates

### Using Templates

Copy the appropriate template to your project root as `railway.json`:

```bash
# For web applications
cp infra/railway/templates/web-app.json railway.json

# For APIs
cp infra/railway/templates/api.json railway.json

# For background workers
cp infra/railway/templates/worker.json railway.json

# For scheduled jobs
cp infra/railway/templates/cron.json railway.json
```

### Customizing Templates

Edit `railway.json` to match your project:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"  // Change if using custom Dockerfile
  },
  "deploy": {
    "startCommand": "node dist/index.js",  // Change to your start command
    "healthcheckPath": "/health",          // Change to your health endpoint
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

---

## 🛠️ Automation Scripts

### railway-init.sh

**Purpose:** Initialize Railway project connection

**Usage:**
```bash
./infra/railway/scripts/railway-init.sh
```

**What it does:**
- Checks Railway CLI installation
- Authenticates with Railway
- Links to existing or creates new project
- Sets up environment variables

**Interactive prompts:**
- Login (if not authenticated)
- Link existing vs. create new project
- Environment variable setup

---

### railway-deploy.sh

**Purpose:** Automated deployment with safety checks

**Usage:**
```bash
./infra/railway/scripts/railway-deploy.sh
```

**What it does:**
- Pre-flight checks (CLI, auth, project link)
- Shows deployment details (branch, commit)
- Confirms deployment
- Deploys to selected environment
- Records deployment in proof/

**Interactive prompts:**
- Deployment confirmation
- Environment selection (production/staging)
- Handling uncommitted changes

**Output:**
- Deployment URL
- Status confirmation
- Deployment record in `proof/deployments/railway.md`

---

### railway-provision-db.sh

**Purpose:** Provision and configure Railway databases

**Usage:**
```bash
./infra/railway/scripts/railway-provision-db.sh
```

**What it does:**
- Provisions selected database type
- Configures DATABASE_URL environment variable
- Optionally creates local `.env.local` with connection string

**Supported databases:**
1. PostgreSQL
2. MySQL
3. MongoDB
4. Redis

**Interactive prompts:**
- Database type selection
- Local .env file creation

**Next steps (shown after provisioning):**
- Run migrations
- Seed data
- Test connection

---

### railway-logs.sh

**Purpose:** View Railway deployment logs

**Usage:**
```bash
# Stream logs (default)
./infra/railway/scripts/railway-logs.sh

# Show last N lines
./infra/railway/scripts/railway-logs.sh recent 200

# Filter errors only
./infra/railway/scripts/railway-logs.sh errors
```

**Modes:**
- `tail` (default): Stream logs in real-time
- `recent [N]`: Show last N lines
- `errors`: Filter error/exception logs only

---

## 🔑 Environment Variables

### Setting Variables via CLI

```bash
# Set individual variables
railway vars set API_KEY=your-api-key
railway vars set NODE_ENV=production

# Set from .env file
railway vars --env production < .env.production

# View all variables
railway vars
```

### Required Variables (typical)

Create `.env.production` with:

```bash
NODE_ENV=production
PORT=8080

# Database (auto-set by Railway if using their DB)
DATABASE_URL=postgresql://...

# Your app-specific variables
API_KEY=your-api-key
JWT_SECRET=your-jwt-secret
SENDGRID_API_KEY=your-sendgrid-key
```

### Security Best Practices

✅ **DO:**
- Use Railway's environment variables UI/CLI
- Keep `.env.production` in `.gitignore`
- Rotate secrets regularly
- Use different secrets per environment

❌ **DON'T:**
- Commit `.env` files to git
- Hardcode secrets in code
- Share production secrets in Slack/email
- Use same secrets for dev/staging/prod

---

## 🗄️ Database Management

### Provisioning a Database

Use the automated script:
```bash
./infra/railway/scripts/railway-provision-db.sh
```

Or manually via CLI:
```bash
railway add --plugin postgresql
railway add --plugin redis
railway add --plugin mongodb
railway add --plugin mysql
```

### Connection Strings

Railway automatically injects `DATABASE_URL` into your environment:

**PostgreSQL:**
```
postgresql://user:password@host:port/database
```

**MongoDB:**
```
mongodb://user:password@host:port/database
```

**Redis:**
```
redis://host:port
```

**MySQL:**
```
mysql://user:password@host:port/database
```

### Migrations

Run migrations after database provisioning:

```bash
# Using Prisma
npx prisma migrate deploy

# Using Knex
npx knex migrate:latest

# Using TypeORM
npm run typeorm migration:run

# Custom migration script
npm run migrate
```

---

## 🔗 GCP + Railway Hybrid

### Architecture

```
Railway (Apps)              GCP (Infrastructure)
├── Web App                 ├── Cloud SQL (PostgreSQL)
├── API Service             ├── Cloud Storage (GCS)
├── Worker                  ├── Memorystore (Redis)
└── Connects to ───────────>└── Secret Manager
```

### Connecting Railway to GCP Services

#### Option 1: Public Endpoints (Recommended for MVP)

Railway apps connect to GCP services via public IPs with authorized networks:

```javascript
// Example: Connecting to GCP Cloud SQL
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: {
    rejectUnauthorized: true
  }
});
```

Set in Railway:
```bash
railway vars set DATABASE_URL=postgresql://user:pass@35.1.2.3:5432/db?sslmode=require
```

#### Option 2: VPC Peering (Production)

For production, use GCP Cloud SQL Proxy:

**In Railway service:**
```dockerfile
# Add to your Dockerfile
RUN wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud_sql_proxy
RUN chmod +x cloud_sql_proxy
```

**Start script:**
```bash
./cloud_sql_proxy -instances=PROJECT:REGION:INSTANCE=tcp:5432 &
node dist/index.js
```

### GCP Secrets in Railway

Sync GCP secrets to Railway:

```bash
# Get secret from GCP
gcloud secrets versions access latest --secret="api-key"

# Set in Railway
railway vars set API_KEY=$(gcloud secrets versions access latest --secret="api-key")
```

Or use automated sync (create this script):
```bash
#!/bin/bash
# sync-gcp-secrets.sh

SECRETS=("api-key" "jwt-secret" "sendgrid-key")

for SECRET in "${SECRETS[@]}"; do
    VALUE=$(gcloud secrets versions access latest --secret="$SECRET")
    railway vars set "$(echo $SECRET | tr '[:lower:]' '[:upper:]' | tr '-' '_')"="$VALUE"
done
```

---

## 📊 Monitoring & Logs

### View Logs

```bash
# Real-time streaming
railway logs

# Last 100 lines
railway logs --num 100

# Filter by deployment
railway logs --deployment-id [id]

# Using helper script
./infra/railway/scripts/railway-logs.sh
```

### Metrics Dashboard

Open Railway dashboard:
```bash
railway open
```

View:
- CPU usage
- Memory usage
- Request rate
- Response times
- Error rates

### Alerts (Configure in Railway UI)

Recommended alerts:
- CPU usage > 80%
- Memory usage > 90%
- Error rate > 1%
- Response time > 1s (95th percentile)

---

## 💰 Cost Management

### Pricing Overview (as of 2025)

**Developer Plan:** $5/month per service
- 500 MB RAM
- 1 vCPU shared
- Unlimited bandwidth
- 1 GB storage

**Pro Plan:** $20/month per service
- 8 GB RAM
- 8 vCPU
- Priority support
- Custom domains

### Cost Optimization Tips

1. **Right-size services:** Start with Developer plan, upgrade if needed
2. **Use sleep mode:** Enable for dev/staging (not production)
3. **Database optimization:** Use Railway's small DB tier for MVPs
4. **Monitor usage:** Set budget alerts in Railway dashboard

### Typical MVP Costs

| Service | Tier | Monthly Cost |
|---------|------|-------------|
| Web App | Developer | $5 |
| API | Developer | $5 |
| Worker | Developer | $5 |
| PostgreSQL | 500 MB | $5 |
| Redis | 100 MB | $5 |
| **Total** | | **$25** |

---

## 🐛 Troubleshooting

### Common Issues

#### "Railway CLI not found"

**Fix:**
```bash
npm install -g @railway/cli
# Or
brew install railway
```

#### "Not logged in"

**Fix:**
```bash
railway login
```

#### "No project linked"

**Fix:**
```bash
railway link
# Or use init script
./infra/railway/scripts/railway-init.sh
```

#### "Build failed"

**Causes:**
- Missing Dockerfile
- Incorrect build command
- Missing dependencies
- Wrong Node version

**Debug:**
```bash
railway logs
# Check build logs for specific errors
```

#### "Health check timeout"

**Causes:**
- No `/health` endpoint
- App not listening on PORT
- Slow startup time

**Fix:**
```typescript
// Add health endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'healthy' });
});

// Listen on Railway's PORT
const PORT = process.env.PORT || 8080;
app.listen(PORT);
```

#### "Database connection failed"

**Causes:**
- Wrong DATABASE_URL
- Database not provisioned
- Network/firewall issues

**Fix:**
```bash
# Check if DATABASE_URL is set
railway vars | grep DATABASE_URL

# Test connection
railway run node -e "require('pg').Client({connectionString:process.env.DATABASE_URL}).connect()"
```

---

## 📚 Additional Resources

### Official Documentation
- [Railway Docs](https://docs.railway.app)
- [Railway CLI Reference](https://docs.railway.app/develop/cli)
- [Railway Plugins](https://docs.railway.app/plugins)

### Framework Resources
- Docker templates: `infra/docker/templates/`
- IaC reference: `docs/strategy/IAC_REFERENCE.md`
- Deploy workflow: `.windsurf/workflows/deploy.md`
- Setup guides: `docs/setup/`

### Support
- Railway Discord: https://discord.gg/railway
- Railway Status: https://status.railway.app
- Framework Issues: Create issue in repo

---

## ✅ Deployment Checklist

Before your first Railway deployment:

- [ ] Railway CLI installed
- [ ] Logged into Railway (`railway whoami`)
- [ ] Project linked (`railway status`)
- [ ] Dockerfile exists at project root
- [ ] Health endpoint returns 200 at `/health`
- [ ] App listens on `process.env.PORT`
- [ ] `.env.production` created (not committed)
- [ ] Environment variables set in Railway
- [ ] Database provisioned (if needed)
- [ ] Tests passing locally
- [ ] Git changes committed

---

**Ready to deploy?** Run:
```bash
./infra/railway/scripts/railway-deploy.sh
```

Or use the `/deploy` workflow in Windsurf! 🚀
