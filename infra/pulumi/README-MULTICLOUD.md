# Multi-Cloud Deployment with Pulumi

Complete guide for deploying to GCP, Railway, and Modal with proper secrets management and multi-environment support.

---

## 🎯 Overview

This Pulumi infrastructure supports:
- ✅ **Multiple Clouds**: GCP Cloud Run, Railway, Modal
- ✅ **Multiple Environments**: PR, Dev, QA, Production
- ✅ **Secrets Management**: Pulumi secrets → Cloud-specific secret stores
- ✅ **Environment Isolation**: Separate resources per environment
- ✅ **Cost Optimization**: Environment-specific resource limits

---

## 📁 File Structure

```
infra/pulumi/
├── index-multicloud.ts           # Multi-cloud deployment code
├── deploy.sh                      # Deployment script
├── package.json                   # Dependencies
├── tsconfig.json                  # TypeScript config
├── Pulumi.pr-template.yaml        # PR environment template
├── Pulumi.dev.yaml                # Development configuration
├── Pulumi.qa.yaml                 # QA configuration
├── Pulumi.production.yaml         # Production configuration
└── README-MULTICLOUD.md           # This file
```

---

## 🚀 Quick Start

### 1. Install Prerequisites

```bash
# Install Pulumi
curl -fsSL https://get.pulumi.com | sh

# Install Node.js dependencies
cd infra/pulumi
npm install

# Login to Pulumi (uses local state by default)
pulumi login --local
# Or use Pulumi Cloud:
# pulumi login
```

### 2. Configure GCP

```bash
# Install gcloud SDK
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

### 3. Set Up Environment

```bash
# Deploy to dev
./deploy.sh dev

# Deploy PR preview
./deploy.sh pr-123 --yes

# Deploy to production (with preview first)
./deploy.sh production --preview
./deploy.sh production
```

---

## 🔑 Secrets Management

### How Secrets Flow

```
Pulumi Config (encrypted)
    ↓
GCP Secret Manager → Cloud Run container
Railway Environment Variables → Railway container
Modal Secrets → Modal function
```

### Setting Secrets

#### For Development:

```bash
# Select stack
pulumi stack select dev

# Set secrets (automatically encrypted)
pulumi config set --secret databaseUrl "postgresql://user:pass@host:5432/db"
pulumi config set --secret apiKey "your-api-key"
pulumi config set --secret jwtSecret "your-jwt-secret"

# Railway (if using)
pulumi config set --secret railwayToken "your-railway-token"
pulumi config set railwayProjectId "your-project-id"

# Modal (if using)
pulumi config set --secret modalToken "your-modal-token"
pulumi config set --secret huggingfaceToken "hf_xxx"
pulumi config set --secret openaiApiKey "sk-xxx"
```

#### For Production:

```bash
pulumi stack select production

# Use different secrets for production
pulumi config set --secret databaseUrl "postgresql://prod-user:prod-pass@prod-host:5432/prod-db"
pulumi config set --secret apiKey "prod-api-key"
# ... etc
```

### Viewing Secrets

```bash
# View all config (secrets shown as [secret])
pulumi config

# View decrypted secret value
pulumi config get databaseUrl --show-secrets
```

---

## 🌍 Multi-Environment Setup

### Environment Hierarchy

| Environment | Purpose | Resources | Public Access |
|-------------|---------|-----------|---------------|
| **PR (pr-123)** | Preview deployments | Minimal (scale to 0) | Yes |
| **Dev** | Development | Small | Yes |
| **QA** | Testing/Staging | Medium | Restricted |
| **Production** | Live | Large (always warm) | Restricted |

### Creating PR Environment

```bash
# Deploy PR preview
./deploy.sh pr-123

# This creates Pulumi.pr-123.yaml from template
# Edit the file to configure PR-specific settings
```

### Environment Configuration

Each environment has its own `Pulumi.<env>.yaml`:

```yaml
# Pulumi.dev.yaml
config:
  gcp:project: my-project-dev
  app:cpu: "1000m"
  app:memory: "512Mi"
  app:minReplicas: 1
  app:deployToGCP: true
  app:deployToRailway: true
```

```yaml
# Pulumi.production.yaml
config:
  gcp:project: my-project-prod
  app:cpu: "2000m"
  app:memory: "2Gi"
  app:minReplicas: 2  # Always warm
  app:deployToGCP: true
  app:deployToRailway: true
  app:deployToModal: true  # Enable ML inference
```

---

## 🏗️ Cloud Provider Configuration

### GCP Cloud Run

**Enabled by default** in all environments.

**Features:**
- Automatic scaling
- Built-in HTTPS
- Secret Manager integration
- Cloud Build integration

**Configuration:**
```yaml
config:
  gcp:project: your-gcp-project
  gcp:region: us-central1
  app:deployToGCP: true
```

---

### Railway

**Optional** - Enable per environment.

**Why Railway:**
- Faster deployments than GCP
- Good for PR previews
- Simple pricing
- Load balancing with GCP

**Configuration:**
```yaml
config:
  app:deployToRailway: true
  app:railwayToken:
    secure: <encrypted-token>
  app:railwayProjectId: <project-id>
```

**Get Railway Token:**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and get token
railway login
railway whoami
# Copy token from ~/.railway/config.json
```

---

### Modal

**Optional** - Best for ML/AI workloads.

**Why Modal:**
- GPU support (A10G, A100)
- Serverless functions
- Auto-scaling
- Pay per second

**Configuration:**
```yaml
config:
  app:deployToModal: true
  app:modalToken:
    secure: <encrypted-token>
  app:modalGpu: "a10g"  # or "a100", "any"
```

**Get Modal Token:**
```bash
# Install Modal
pip install modal

# Get token
modal token new
# Copy from ~/.modal.toml
```

---

## 📊 Resource Limits by Environment

| Environment | CPU | Memory | Min Replicas | Max Replicas |
|-------------|-----|--------|--------------|--------------|
| PR | 500m | 256Mi | 0 | 2 |
| Dev | 1000m | 512Mi | 1 | 5 |
| QA | 1500m | 1Gi | 1 | 8 |
| Production | 2000m | 2Gi | 2 | 20 |

**Customize in stack config:**
```yaml
config:
  app:cpu: "2000m"
  app:memory: "2Gi"
  app:minReplicas: 2
  app:maxReplicas: 20
```

---

## 🔒 Security & IAM

### Public vs Private Access

**PR/Dev** - Public access (for testing):
```yaml
# Automatically configured - no IAM restrictions
```

**QA** - Restricted to team:
```yaml
config:
  app:allowedUsers: "user:qa-team@company.com,serviceAccount:qa-bot@project.iam.gserviceaccount.com"
```

**Production** - Service accounts only:
```yaml
config:
  app:allowedUsers: "serviceAccount:prod-bot@project.iam.gserviceaccount.com"
```

### GCP Secret Manager IAM

Pulumi automatically grants Cloud Run access to secrets:
- Creates secret in Secret Manager
- Grants `roles/secretmanager.secretAccessor` to Cloud Run service account

---

## 📝 Common Workflows

### Deploy to Development

```bash
./deploy.sh dev
```

### Deploy PR Preview

```bash
# GitHub Actions can call this
./deploy.sh pr-${PR_NUMBER} --yes
```

### Preview Production Changes

```bash
# Always preview production first
./deploy.sh production --preview

# If looks good, deploy
./deploy.sh production
```

### Destroy PR Environment

```bash
# Clean up after PR is merged
./deploy.sh pr-123 --destroy --yes
```

### Update Secrets

```bash
# Select environment
pulumi stack select production

# Update secret
pulumi config set --secret databaseUrl "new-connection-string"

# Deploy to apply changes
./deploy.sh production
```

---

## 🐛 Troubleshooting

### Issue: "No such file or directory: Pulumi.<env>.yaml"

**Fix:** Create stack configuration from template:
```bash
cp Pulumi.pr-template.yaml Pulumi.dev.yaml
# Edit configuration
./deploy.sh dev
```

### Issue: "GCP APIs not enabled"

**Fix:** Enable required APIs:
```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### Issue: "Permission denied" on secrets

**Fix:** Grant Secret Manager access:
```bash
# Get Cloud Run service account
gcloud run services describe SERVICE_NAME --region=us-central1 --format="value(spec.template.spec.serviceAccountName)"

# Grant access
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"
```

### Issue: Railway deployment fails

**Fix:** Check Railway token and project ID:
```bash
pulumi config get railwayToken --show-secrets
pulumi config get railwayProjectId

# Verify in Railway dashboard
railway whoami
railway list
```

### Issue: Modal GPU not available

**Fix:** Check Modal GPU availability and pricing:
```bash
modal gpu list
# Use "any" for flexible allocation
pulumi config set modalGpu "any"
```

---

## 💰 Cost Optimization

### By Environment

**PR Environments:**
- Scale to 0 when idle
- Minimal resources
- Auto-destroy after merge

**Development:**
- Single replica
- Small resources
- Scale down after hours (optional)

**Production:**
- Always warm (min 2 replicas)
- Right-sized resources
- Monitor and adjust

### GCP Cloud Run Pricing

- **Free tier**: 2 million requests/month
- **After free tier**: $0.40 per million requests
- **CPU**: $0.00002400 per vCPU-second
- **Memory**: $0.00000250 per GiB-second

### Railway Pricing

- **Starter**: $5/month
- **Pro**: $20/month + usage
- **Pay per GB-hour**: ~$0.000231/GB-hour

### Modal Pricing

- **Free tier**: $30/month credit
- **GPU**: ~$1-4/hour depending on type
- **Pay per second**: Billed by actual usage

---

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy
on:
  pull_request:
  push:
    branches: [main, dev]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Pulumi
        uses: pulumi/actions@v3
        
      - name: Deploy PR Preview
        if: github.event_name == 'pull_request'
        run: |
          cd infra/pulumi
          ./deploy.sh pr-${{ github.event.pull_request.number }} --yes
        env:
          PULUMI_ACCESS_TOKEN: ${{ secrets.PULUMI_ACCESS_TOKEN }}
          
      - name: Deploy to Dev
        if: github.ref == 'refs/heads/dev'
        run: |
          cd infra/pulumi
          ./deploy.sh dev --yes
          
      - name: Deploy to Production
        if: github.ref == 'refs/heads/main'
        run: |
          cd infra/pulumi
          ./deploy.sh production --yes
```

---

## 📚 Further Reading

- **Pulumi Docs**: https://www.pulumi.com/docs/
- **GCP Cloud Run**: https://cloud.google.com/run/docs
- **Railway Docs**: https://docs.railway.app/
- **Modal Docs**: https://modal.com/docs

---

## ❓ FAQ

**Q: Can I deploy to all three clouds simultaneously?**  
A: Yes! Set all provider flags to true in your stack config.

**Q: How do I rotate secrets?**  
A: Update via `pulumi config set --secret`, then redeploy.

**Q: Can I use different clouds per environment?**  
A: Yes! Configure `deployToX` flags differently per stack.

**Q: What if I only want GCP?**  
A: Set `deployToRailway: false` and `deployToModal: false`.

**Q: How do I monitor deployments?**  
A: Use Pulumi Cloud dashboard or `pulumi stack output --show-urls`.

---

**Created:** November 15, 2025  
**Status:** Production-Ready  
**Framework Version:** 97%
