# Node.js/TypeScript Docker Template

Production-ready Docker configuration for Node.js and TypeScript applications, optimized for Railway and GCP Cloud Run.

---

## 📁 Files Included

- **Dockerfile** - Multi-stage production build (recommended)
- **Dockerfile.dev** - Development build with hot reload
- **.dockerignore** - Excludes unnecessary files from build

---

## 🚀 Quick Start

### **Local Development**

```bash
# Build development image
docker build -f Dockerfile.dev -t my-app:dev .

# Run with hot reload (mount source code)
docker run -p 8080:8080 -v $(pwd)/src:/app/src my-app:dev
```

### **Production Build**

```bash
# Build production image
docker build -t my-app:latest .

# Run production image
docker run -p 8080:8080 my-app:latest

# Test health check
curl http://localhost:8080/health
```

---

## 🎯 Deployment Targets

### **Railway**

```bash
# Railway automatically detects Dockerfile
railway login
railway init
railway up

# Or use railway.json for configuration
```

### **GCP Cloud Run (via Pulumi)**

```bash
cd infra/pulumi
pulumi up
# Automatically builds and deploys Docker image
```

### **Docker Compose (Local Full Stack)**

```yaml
# docker-compose.yml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "8080:8080"
    volumes:
      - ./src:/app/src
    environment:
      - DATABASE_URL=postgresql://db:5432/app_dev
```

---

## 📦 Requirements

### **Your Project Structure**

```
your-app/
├── package.json          # Must have "build" and "start" scripts
├── tsconfig.json         # TypeScript configuration
├── src/                  # Source code
│   └── index.ts
├── dist/                 # Build output (gitignored)
└── Dockerfile            # Copy from this template
```

### **Required package.json Scripts**

```json
{
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js",
    "dev": "ts-node-dev --respawn src/index.ts"
  }
}
```

---

## 🔧 Customization

### **Change Entry Point**

If your app starts from a different file:

```dockerfile
# In Dockerfile, change:
CMD ["node", "dist/index.js"]

# To:
CMD ["node", "dist/server.js"]
```

### **Add Environment Variables**

```dockerfile
# In Dockerfile, add to ENV section:
ENV NODE_ENV=production \
    PORT=8080 \
    MY_CUSTOM_VAR=value
```

### **Install System Dependencies**

```dockerfile
# In runner stage, add:
RUN apk add --no-cache \
    postgresql-client \
    python3
```

### **Change Node Version**

```dockerfile
# Change all FROM statements:
FROM node:20-alpine
# To:
FROM node:18-alpine
```

---

## 🏗️ Multi-Stage Build Explained

### **Stage 1: Dependencies (deps)**
- Installs production dependencies only
- Cached separately for faster rebuilds
- Results in smaller final image

### **Stage 2: Builder**
- Installs dev dependencies
- Compiles TypeScript to JavaScript
- Creates optimized dist/ folder

### **Stage 3: Runner (final)**
- Minimal Alpine Linux base
- Only production dependencies
- Non-root user for security
- Health check included

---

## 📊 Image Size Optimization

### **Before Optimization** (Single-stage build)
```
node:20                  ~1000 MB
+ node_modules (all)     ~300 MB
+ source code            ~10 MB
─────────────────────────────────
Total:                   ~1310 MB
```

### **After Optimization** (Multi-stage build)
```
node:20-alpine           ~150 MB
+ node_modules (prod)    ~100 MB
+ compiled code (dist)   ~5 MB
─────────────────────────────────
Total:                   ~255 MB
```

**Result:** 80% reduction in image size! 🎉

---

## 🔐 Security Best Practices

✅ **Non-root User**
- Runs as `nodejs` user (UID 1001)
- Prevents privilege escalation attacks

✅ **Minimal Base Image**
- Alpine Linux (~5 MB vs ~100 MB for full OS)
- Fewer attack surface vulnerabilities

✅ **No Secrets in Image**
- `.dockerignore` excludes `.env` files
- Use environment variables at runtime

✅ **Signal Handling**
- `dumb-init` for proper SIGTERM handling
- Graceful shutdown on container stop

✅ **Health Checks**
- Built-in health endpoint monitoring
- Automatic container restart on failure

---

## 🧪 Testing Your Docker Build

### **1. Build and Run Locally**

```bash
# Build
docker build -t my-app:test .

# Run
docker run -p 8080:8080 \
  -e DATABASE_URL=postgresql://localhost/test \
  my-app:test

# Test
curl http://localhost:8080/health
```

### **2. Inspect Image Size**

```bash
docker images my-app:test
# Should be ~200-300 MB for Node.js apps
```

### **3. Check Security**

```bash
# Verify non-root user
docker run my-app:test whoami
# Should output: nodejs

# Scan for vulnerabilities (optional)
docker scan my-app:test
```

### **4. Test Health Check**

```bash
# Start container
docker run -d --name test-app my-app:test

# Wait 10 seconds for health check
sleep 10

# Check health status
docker inspect --format='{{.State.Health.Status}}' test-app
# Should output: healthy
```

---

## 🐛 Troubleshooting

### **Build Fails: "Cannot find module"**

**Cause:** TypeScript build output location mismatch

**Fix:** Check `tsconfig.json` output directory:
```json
{
  "compilerOptions": {
    "outDir": "./dist"  // Must match Dockerfile
  }
}
```

### **Container Exits Immediately**

**Cause:** App crashes on startup, often missing env vars

**Fix:** Check logs:
```bash
docker logs <container-id>
```

Add required environment variables:
```bash
docker run -e DATABASE_URL=... -e API_KEY=... my-app
```

### **Health Check Failing**

**Cause:** No `/health` endpoint in your app

**Fix:** Add health endpoint:
```typescript
// src/index.ts
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'healthy' });
});
```

Or remove health check from Dockerfile if not needed.

### **Image Too Large (>500 MB)**

**Cause:** Unnecessary files in build context

**Fix:** Verify `.dockerignore` is present and complete:
```bash
# Check what's being sent to Docker
docker build --no-cache --progress=plain . 2>&1 | grep "COPY"
```

---

## 📚 Additional Resources

- [Railway Dockerfile Guide](https://docs.railway.com/guides/dockerfiles)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Node.js Docker Best Practices](https://github.com/nodejs/docker-node/blob/main/docs/BestPractices.md)
- [Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)

---

## ✅ Checklist Before Deploying

- [ ] `package.json` has `build` and `start` scripts
- [ ] Health endpoint at `/health` returns 200 status
- [ ] App listens on `process.env.PORT` (defaults to 8080)
- [ ] `.dockerignore` excludes `.env` and `node_modules`
- [ ] Build succeeds locally: `docker build -t test .`
- [ ] Container runs locally: `docker run -p 8080:8080 test`
- [ ] Health check passes: `curl http://localhost:8080/health`

---

**Ready to deploy?** Copy `Dockerfile` to your project root and run:

```bash
# Railway
railway up

# GCP Cloud Run
cd infra/pulumi && pulumi up

# Local testing
docker build -t my-app . && docker run -p 8080:8080 my-app
```

**Questions?** See main documentation: `docs/strategy/IAC_STRATEGY.md`
