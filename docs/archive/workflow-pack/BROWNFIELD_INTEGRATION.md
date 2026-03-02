# Brownfield Project Integration Guide

This guide explains how to integrate the Windsurf Workflow Pack with **existing brownfield projects** that already have established codebases, build systems, and deployment processes.

---

## 🏗️ **Integration Scenarios**

### **✅ What Works Immediately (No Changes Required):**

- **Workflow files** - All `/plan`, `/implement`, `/agent` workflows work regardless of existing code
- **Git hooks** - Quality gates and formatting apply to new commits
- **Agentic workflows** - Pure YAML, no code dependencies
- **Documentation workflows** - `/constitution`, `/audit`, `/compliance`
- **Planning methodology** - CFOI approach works with any tech stack

### **🔧 What Needs Adaptation:**

#### **1. Dockerfile Integration**

**Scenario A: Existing Project Has No Docker**

```dockerfile
# Template provides: FROM node:18-alpine
# Customize for your stack:

# Python Project:
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["python", "app.py"]

# Go Project:
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o main .
FROM alpine:latest
COPY --from=builder /app/main .
EXPOSE 8080
CMD ["./main"]

# Java Project:
FROM openjdk:17-jdk-slim
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline
COPY . .
RUN mvn package -DskipTests
EXPOSE 8080
CMD ["java", "-jar", "target/app.jar"]
```

**Scenario B: Existing Project Has Docker**

- Keep your existing `Dockerfile`
- Ensure it exposes port 8080 (Cloud Run requirement)
- Add health check endpoint if missing:

```dockerfile
# Add to existing Dockerfile:
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1
```

#### **2. Build System Integration**

**Node.js Brownfield Project:**

```json
// Merge template scripts with existing package.json
{
  "scripts": {
    // Keep existing scripts
    "start": "node server.js",
    "dev": "nodemon server.js",

    // Add workflow scripts
    "format": "prettier --write .",
    "test:unit": "jest",
    "test:integration": "jest --config jest.integration.config.js",
    "test:e2e": "playwright test",
    "test:all": "npm run test:unit && npm run test:integration && npm run test:e2e",
    "seed:pr": "node scripts/seed-pr.js"
  }
}
```

**Non-Node.js Brownfield Project:**

```json
// Create minimal package.json for workflow tooling only
{
  "name": "workflow-tools",
  "private": true,
  "scripts": {
    "format": "prettier --write .",
    "test:unit": "python -m pytest tests/unit/",
    "test:integration": "python -m pytest tests/integration/",
    "test:e2e": "python -m pytest tests/e2e/",
    "test:all": "python -m pytest",
    "seed:pr": "python scripts/seed_data.py"
  },
  "devDependencies": {
    "prettier": "^3.6.2"
  }
}
```

**Alternative: Use Native Build Tools**

```bash
# Python: requirements-dev.txt + Makefile
# Go: Makefile or tools.go
# Java: Maven/Gradle profiles
# .NET: Directory.Build.props

# Example Makefile:
test-all:
	pytest tests/unit/
	pytest tests/integration/
	pytest tests/e2e/

format:
	black .
	isort .

seed-pr:
	python scripts/seed_data.py
```

#### **3. Test Integration Patterns**

**Existing Test Suite Integration:**

```bash
# Template assumes: npm run test:all
# Adapt to existing patterns:

# Python Project:
"test:all": "pytest --cov=src tests/"

# Go Project:
"test:all": "go test ./... -v -race -coverprofile=coverage.out"

# Java Project:
"test:all": "mvn test"

# .NET Project:
"test:all": "dotnet test --collect:\"XPlat Code Coverage\""

# Ruby Project:
"test:all": "bundle exec rspec"
```

#### **4. Infrastructure Conflicts & Solutions**

**Existing Kubernetes Deployment:**

```javascript
// Modify infra/pulumi/index.js for K8s compatibility
const k8s = require("@pulumi/kubernetes");

// Create namespace for ephemeral environments
const namespace = new k8s.core.v1.Namespace(`${serviceName}-ns`);

// Deploy to existing cluster instead of Cloud Run
const deployment = new k8s.apps.v1.Deployment(serviceName, {
  metadata: { namespace: namespace.metadata.name },
  spec: {
    replicas: 1,
    selector: { matchLabels: { app: serviceName } },
    template: {
      metadata: { labels: { app: serviceName } },
      spec: {
        containers: [
          {
            name: serviceName,
            image: `gcr.io/${projectId}/${serviceName}:latest`,
            ports: [{ containerPort: 8080 }],
          },
        ],
      },
    },
  },
});
```

**Existing App Engine/Cloud Functions:**

```javascript
// Adapt for App Engine
const appEngineService = new gcp.appengine.StandardAppVersion(serviceName, {
  service: serviceName,
  runtime: "python39", // or your runtime
  entrypoint: { shell: "gunicorn -b :$PORT main:app" },
  deployment: {
    files: [
      {
        name: "main.py",
        sourceUrl: "gs://bucket/source.zip",
      },
    ],
  },
});
```

---

## 🎯 **Brownfield Integration Strategies**

### **Strategy 1: Workflows-First (Recommended)**

**Timeline: 5 minutes**

```bash
# Copy only workflow files
cp -r template/.windsurf/ existing-project/
cp -r template/.githooks/ existing-project/

# Skip infrastructure files initially:
# - Skip Dockerfile modifications
# - Skip server.js example
# - Skip package.json changes
```

**Benefits:**

- ✅ Immediate workflow adoption
- ✅ No risk to existing deployment
- ✅ Team can learn CFOI methodology
- ✅ Works with any tech stack

### **Strategy 2: Parallel Infrastructure**

**Timeline: 15 minutes**

```bash
# Add ephemeral environments alongside existing deployment
# Keep production deployment unchanged
# Use branch-specific Cloud Run for PR testing only

# Modify infra/pulumi/index.js:
const serviceName = `${appName}-ephemeral-${sanitizedBranch}`;
// This creates separate resources, no conflicts
```

**Benefits:**

- ✅ Existing deployment untouched
- ✅ PR testing in cloud environment
- ✅ Gradual team adoption
- ✅ Easy rollback if issues

### **Strategy 3: Gradual Migration**

**Timeline: 30+ minutes**

```bash
# Phase 1: Workflows (5 min)
# Phase 2: Ephemeral environments (15 min)
# Phase 3: Migrate existing CI/CD (variable)
# Phase 4: Full infrastructure adoption (variable)
```

**Benefits:**

- ✅ Comprehensive modernization
- ✅ Full workflow pack benefits
- ✅ Team learns incrementally
- ⚠️ Requires more planning

---

## 🚨 **Common Conflicts & Solutions**

### **Port Conflicts**

```bash
# Problem: Template hardcodes port 8080, brownfield uses 3000
# Solution: Environment variable approach

# In Dockerfile:
ENV PORT=${PORT:-8080}
EXPOSE $PORT

# In application code:
const port = process.env.PORT || 3000; // Node.js
port = int(os.environ.get('PORT', 5000)) # Python
```

### **Build System Mismatch**

```bash
# Problem: Template assumes npm, brownfield uses Maven/Gradle/Make
# Solution: Wrapper approach

# Create package.json with proxy scripts:
{
  "scripts": {
    "test:all": "make test",
    "build": "./gradlew build",
    "format": "make format",
    "seed:pr": "make seed-data"
  }
}

# Or skip package.json entirely and modify GitHub Actions:
- name: Run Tests
  run: make test-all  # instead of npm run test:all
```

### **Database Dependencies**

```bash
# Problem: Template has minimal infra, brownfield needs PostgreSQL/Redis
# Solution: Extend Pulumi configuration

// Add to infra/pulumi/index.js:
const database = new gcp.sql.DatabaseInstance(`${serviceName}-db`, {
  databaseVersion: "POSTGRES_14",
  settings: {
    tier: "db-f1-micro",
    diskSize: 10,
    diskType: "PD_SSD"
  }
});

const redis = new gcp.redis.Instance(`${serviceName}-cache`, {
  memorySizeGb: 1,
  region: region
});

// Pass connection strings to Cloud Run
env: [
  { name: "DATABASE_URL", value: database.connectionName },
  { name: "REDIS_URL", value: redis.host }
]
```

### **Existing CI/CD Pipeline**

```bash
# Problem: Brownfield has Jenkins/CircleCI/GitLab CI
# Solution: Hybrid approach

# Keep existing CI for production
# Add GitHub Actions only for ephemeral environments
# Gradually migrate confidence builds

# Or adapt existing CI to use workflow pack:
# - Copy workflow concepts to existing pipeline
# - Use /plan, /implement methodology
# - Keep existing deployment process
```

---

## 📋 **Brownfield Integration Checklist**

### **Pre-Integration Assessment**

- [ ] **Document existing build process** - Commands, dependencies, environment variables
- [ ] **Identify test commands** - Unit, integration, e2e test execution
- [ ] **Note deployment process** - Current CI/CD, infrastructure, environment variables
- [ ] **Check port usage** - What port does the application currently use?
- [ ] **Review dependencies** - Package managers, build tools, runtime requirements
- [ ] **Backup configurations** - CI/CD configs, deployment scripts, environment files

### **Phase 1: Workflow Adoption (Low Risk)**

- [ ] Copy `.windsurf/workflows/` directory
- [ ] Copy `.githooks/` directory
- [ ] Test `/plan` workflow on small change
- [ ] Test `/implement` workflow
- [ ] Train team on CFOI methodology
- [ ] Verify git hooks don't break existing workflow

### **Phase 2: Infrastructure Planning (Medium Risk)**

- [ ] Choose integration strategy (workflows-first/parallel/gradual)
- [ ] Adapt Dockerfile for your tech stack
- [ ] Configure Google Cloud project (if using ephemeral environments)
- [ ] Set up GitHub secrets (GCP_PROJECT_ID, GCP_SA_KEY)
- [ ] Test infrastructure on feature branch
- [ ] Verify no conflicts with existing deployment

### **Phase 3: Full Integration (Higher Risk)**

- [ ] Update package.json or create wrapper scripts
- [ ] Modify test commands to match existing suite
- [ ] Extend infrastructure for database/cache dependencies
- [ ] Update CI/CD to use new workflows
- [ ] Migrate team to new process
- [ ] Monitor and adjust based on team feedback

---

## 💡 **Smart Brownfield Tips**

### **Start Small**

```bash
# Don't try to migrate everything at once
# Pick one small feature or bug fix
# Use workflows for that single change
# Build confidence before expanding
```

### **Preserve What Works**

```bash
# If existing deployment is stable, keep it
# Add ephemeral environments for testing only
# Migrate when team is comfortable and confident
```

### **Team Training**

```bash
# CFOI methodology is the real value
# Infrastructure is just tooling
# Focus on /plan → /clarify → /task → /implement flow
# Technical migration can happen gradually
```

### **Rollback Plan**

```bash
# Always have a rollback strategy
# Keep existing CI/CD working during transition
# Use feature flags for gradual rollout
# Document what changed for easy reversal
```

---

## 🎯 **Success Patterns**

### **New Features Only**

- Apply CFOI methodology to new features
- Leave legacy code deployment unchanged
- Use ephemeral environments for new development
- Gradually expand to more of the codebase

### **Team-by-Team Adoption**

- Start with most motivated team
- Let them become internal champions
- Share success stories and lessons learned
- Expand to other teams based on results

### **Component-by-Component**

- Identify loosely coupled components
- Migrate one component at a time
- Use for microservices or modular monoliths
- Build expertise before tackling core systems

The key insight: **This workflow pack is methodology-first**. You can adopt the planning and implementation workflows immediately, then add infrastructure when your team is ready and confident.

---

## 🔗 **Related Documentation**

- `README.md` - Main workflow pack overview
- `EPHEMERAL_SETUP.md` - Infrastructure setup guide
- `.windsurf/workflows/` - Individual workflow documentation
- `infra/pulumi/` - Infrastructure code examples
