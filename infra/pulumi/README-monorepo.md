# Monorepo Pulumi Infrastructure

This directory contains parameterized Pulumi infrastructure for deploying monorepo applications to Google Cloud Platform.

---

## 🏗️ Architecture Overview

The monorepo Pulumi setup supports:
- **Multiple Services**: Frontend, Backend, Admin Dashboard, Background Workers
- **Multiple Databases**: PostgreSQL, Redis, MongoDB, Neo4j
- **Flexible Configuration**: Enable/disable services and databases as needed
- **Environment Isolation**: Separate configurations for dev, staging, production
- **Cost Optimization**: Resource limits and auto-scaling configurations

---

## 📁 File Structure

```
infra/pulumi/
├── index.js                    # Original single-service deployment
├── index-monorepo.js           # Parameterized monorepo deployment
├── Pulumi.yaml                 # Original stack configuration
├── Pulumi.monorepo.yaml        # Monorepo stack template
├── config-monorepo.js          # Configuration management script
├── README-monorepo.md          # This file
└── stacks/                     # Stack-specific configurations
    ├── dev.yaml               # Development environment
    ├── staging.yaml           # Staging environment
    └── production.yaml        # Production environment
```

---

## 🚀 Quick Start

### 1. Set Up Pulumi Project

```bash
# Navigate to Pulumi directory
cd infra/pulumi

# Install dependencies
npm install

# Select or create stack
pulumi stack select dev
# or create new stack
pulumi stack init dev
```

### 2. Generate Stack Configuration

```bash
# List available presets
node config-monorepo.js list-presets

# Generate configuration from preset
node config-monorepo.js generate fullstack-cache dev

# This creates Pulumi.dev.yaml with the preset configuration
```

### 3. Customize Configuration

```bash
# Set specific values
node config-monorepo.js set-config dev region us-west1
node config-monorepo.js set-config dev postgresTier db-g1-small

# View configuration
node config-monorepo.js get-config dev
node config-monorepo.js get-config dev postgresTier
```

### 4. Deploy Infrastructure

```bash
# Validate configuration
node config-monorepo.js validate dev

# Preview deployment
pulumi preview

# Deploy infrastructure
pulumi up
```

---

## 🎯 Configuration Presets

### Available Presets

| Preset | Description | Services | Databases |
|--------|-------------|----------|-----------|
| `fullstack` | Basic full-stack app | Frontend, Backend | PostgreSQL |
| `fullstack-cache` | Full-stack with caching | Frontend, Backend | PostgreSQL, Redis |
| `microservices` | Complete microservices | Frontend, Backend, Admin, Worker | PostgreSQL, Redis |
| `data-heavy` | Data-intensive application | Frontend, Backend, Worker | PostgreSQL, Redis, MongoDB, Neo4j |
| `api-only` | Backend API only | Backend | PostgreSQL, Redis |
| `frontend-only` | Frontend only | Frontend | None |

### Using Presets

```bash
# Generate microservices stack
node config-monorepo.js generate microservices staging

# Generate data-heavy stack
node config-monorepo.js generate data-heavy production
```

---

## ⚙️ Service Configuration

### Frontend Service

**Configuration Options:**
- `frontendPort`: Container port (default: 3000)
- `frontendCpu`: CPU allocation (default: "1000m")
- `frontendMemory`: Memory allocation (default: "512Mi")
- `frontendMaxInstances`: Maximum instances (default: 10)
- `frontendConcurrency`: Concurrent requests per instance (default: 100)

**Example:**
```bash
node config-monorepo.js set-config dev frontendCpu "2000m"
node config-monorepo.js set-config dev frontendMemory "1Gi"
```

### Backend Service

**Configuration Options:**
- `backendPort`: Container port (default: 8080)
- `backendCpu`: CPU allocation (default: "1000m")
- `backendMemory`: Memory allocation (default: "512Mi")
- `backendMaxInstances`: Maximum instances (default: 10)
- `backendConcurrency`: Concurrent requests per instance (default: 100)

**Environment Variables:**
Automatically configured based on enabled databases:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `MONGODB_URI`: MongoDB connection string
- `NEO4J_URI`: Neo4j connection string

### Admin Dashboard

**Configuration Options:**
- `adminPort`: Container port (default: 3001)
- `adminCpu`: CPU allocation (default: "1000m")
- `adminMemory`: Memory allocation (default: "512Mi")
- `adminMaxInstances`: Maximum instances (default: 5)
- `adminConcurrency`: Concurrent requests per instance (default: 50)

### Background Worker

**Configuration Options:**
- `workerCpu`: CPU allocation (default: "500m")
- `workerMemory`: Memory allocation (default: "256Mi")
- `workerMaxInstances`: Maximum instances (default: 3)
- `workerConcurrency`: Concurrent requests per instance (default: 1)

---

## 🗄️ Database Configuration

### PostgreSQL

**Configuration Options:**
- `postgresTier`: Machine tier (default: "db-f1-micro")
- `postgresDiskSize`: Disk size in GB (default: 10)
- `postgresVersion`: PostgreSQL version (default: "POSTGRES_15")

**Available Tiers:**
- `db-f1-micro`: 1 vCPU, 0.6 GB RAM (~$10/month)
- `db-g1-small`: 1 vCPU, 1.7 GB RAM (~$25/month)
- `db-n1-standard-1`: 1 vCPU, 3.75 GB RAM (~$50/month)

**Example:**
```bash
node config-monorepo.js set-config staging postgresTier "db-g1-small"
node config-monorepo.js set-config staging postgresDiskSize 20
```

### Redis

**Configuration Options:**
- `redisTier`: Service tier (default: "BASIC")
- `redisMemorySize`: Memory size in GB (default: 1)
- `redisVersion`: Redis version (default: "REDIS_7_0")

**Available Tiers:**
- `BASIC`: Basic tier (~$7/month for 1GB)
- `STANDARD_HA`: High availability (~$15/month for 1GB)

### MongoDB

**Configuration Options:**
- `mongodbTier`: Atlas tier (default: "M0")

**Available Tiers:**
- `M0`: Shared cluster (~$9/month)
- `M2`: Dedicated cluster (~$25/month)
- `M5`: Dedicated cluster (~$60/month)

### Neo4j

**Configuration Options:**
- `neo4jTier`: Machine tier (default: "db-n1-standard-1")
- `neo4jDiskSize`: Disk size in GB (default: 10)

---

## 🌍 Environment Management

### Development Environment

```bash
# Create dev stack
pulumi stack init dev
node config-monorepo.js generate fullstack-cache dev

# Use cost-effective configurations
node config-monorepo.js set-config dev postgresTier "db-f1-micro"
node config-monorepo.js set-config dev redisTier "BASIC"
node config-monorepo.js set-config dev frontendMaxInstances 2
node config-monorepo.js set-config dev backendMaxInstances 2
```

### Staging Environment

```bash
# Create staging stack
pulumi stack init staging
node config-monorepo.js generate microservices staging

# Use moderate configurations
node config-monorepo.js set-config staging postgresTier "db-g1-small"
node config-monorepo.js set-config staging redisTier "STANDARD_HA"
node config-monorepo.js set-config staging frontendMaxInstances 5
node config-monorepo.js set-config staging backendMaxInstances 5
```

### Production Environment

```bash
# Create production stack
pulumi stack init production
node config-monorepo.js generate data-heavy production

# Use production-grade configurations
node config-monorepo.js set-config production postgresTier "db-n1-standard-2"
node config-monorepo.js set-config production redisTier "STANDARD_HA"
node config-monorepo.js set-config production redisMemorySize 5
node config-monorepo.js set-config production frontendMaxInstances 20
node config-monorepo.js set-config production backendMaxInstances 20
```

---

## 🚢 Deployment Workflow

### 1. Configure Branch Name

```bash
# Set branch name for unique resource naming
pulumi config set branch feature-user-auth
```

### 2. Preview Changes

```bash
# Preview what will be created/updated
pulumi preview
```

### 3. Deploy Infrastructure

```bash
# Deploy all configured services and databases
pulumi up
```

### 4. Get Service URLs

```bash
# Get deployed service URLs
pulumi stack output serviceUrls

# Example output:
# {
#   "frontend": "https://myapp-frontend-feature-user-auth-abc123.a.run.app",
#   "backend": "https://myapp-backend-feature-user-auth-abc123.a.run.app"
# }
```

---

## 📊 Monitoring and Management

### View Stack Outputs

```bash
# Get all stack outputs
pulumi stack output

# Get specific output
pulumi stack output serviceUrls
pulumi stack output databases
```

### Update Running Services

```bash
# Update configuration
node config-monorepo.js set-config production backendMaxInstances 50

# Apply changes
pulumi up
```

### Remove Services

```bash
# Disable a service
node config-monorepo.js set-config production admin false

# Apply changes (will remove admin service)
pulumi up
```

---

## 💰 Cost Management

### Estimate Costs

```bash
# Get cost estimate for current configuration
node config-monorepo.js estimate-cost production

# Example output:
# Cost Estimate for stack 'production':
# =====================================
# Services:
#   Frontend: $0 - $50/month
#   Backend: $0 - $100/month
#   Admin: $0 - $30/month
#   Worker: $0 - $40/month
# Databases:
#   PostgreSQL: $10 - $200/month
#   Redis: $7 - $50/month
#   MongoDB: $9 - $25/month
#   Neo4j: $50 - $500/month
# Total Estimated Cost: $76 - $995/month
```

### Cost Optimization Tips

1. **Use appropriate tiers**: Match database tiers to actual needs
2. **Set instance limits**: Limit max instances to control costs
3. **Disable unused services**: Turn off admin/worker when not needed
4. **Monitor usage**: Use GCP monitoring to track actual usage
5. **Use preemptible VMs**: For non-critical workloads

---

## 🔧 Advanced Configuration

### Custom Environment Variables

```javascript
// In index-monorepo.js, add custom environment variables
const customEnvVars = [
  {
    name: "CUSTOM_API_KEY",
    value: config.get("customApiKey") || "",
  },
  {
    name: "FEATURE_FLAGS",
    value: config.get("featureFlags") || "{}",
  },
];
```

### Resource Tags

```javascript
// Add resource tags for cost tracking
const commonTags = {
  environment: stackName,
  project: appName,
  managedBy: "pulumi-monorepo",
};
```

### Custom Domains

```javascript
// Configure custom domains for services
const domainConfig = {
  frontend: config.get("frontendDomain") || "",
  backend: config.get("backendDomain") || "",
};
```

---

## 🛠️ Troubleshooting

### Common Issues

**Stack already exists:**
```bash
pulumi stack select dev
# or
pulumi stack rm dev
pulumi stack init dev
```

**Configuration validation errors:**
```bash
# Validate configuration
node config-monorepo.js validate dev

# Check for missing required values
node config-monorepo.js get-config dev
```

**Deployment failures:**
```bash
# Check detailed error messages
pulumi up --verbose

# Check resource status
pulumi stack status
```

**Permission errors:**
```bash
# Ensure GCP authentication
gcloud auth login
gcloud config set project your-project-id

# Check Pulumi configuration
pulumi config
```

### Debug Commands

```bash
# Show current stack configuration
pulumi config --show-secrets

# Show stack outputs
pulumi stack output

# Show deployment history
pulumi history

# Refresh stack state
pulumi refresh
```

---

## 📚 Additional Resources

- [Pulumi GCP Documentation](https://www.pulumi.com/docs/gcp/)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Google Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Google Memorystore Documentation](https://cloud.google.com/memorystore/docs)

---

**Questions?** Check the [main README](../README.md) or create an issue on GitHub.
