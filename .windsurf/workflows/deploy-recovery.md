---
allowed-tools: "*"
description: Recover from failed or problematic deployments
---
allowed-tools: "*"

# Deployment Recovery Workflow

Use this workflow when a deployment fails, causes issues, or needs to be rolled back.

---
allowed-tools: "*"

## When to Use

- Deployment succeeded but app is crashing
- Health checks failing after deployment
- Need to rollback to previous version
- Database migration failed
- Environment variables missing/incorrect

---
allowed-tools: "*"

## Step 0: Assess the Situation

**AI: Ask the user:**

1. What platform? (Railway/GCP/Other)
2. What's the symptom?
   - App crashed immediately
   - Health check timeout
   - Database connection failed
   - 500 errors in production
   - Other (describe)
3. When did this start? (after which deployment)

**AI: Based on answers, guide to appropriate section below.**

---
allowed-tools: "*"

## Step 1: Quick Diagnostics

### For Railway

**AI: Run diagnostics:**

```bash
# Check if Railway CLI is available
railway whoami

# Get current status
railway status

# Fetch recent logs (last 100 lines)
railway logs --num 100
```

**AI: Analyze logs for:**
- Crash messages
- Connection errors
- Missing environment variables
- Port binding issues
- Database connection failures

**AI: Report findings to user and suggest next step.**

---
allowed-tools: "*"

### For GCP

**AI: Run diagnostics:**

```bash
# Check authentication
gcloud auth list

# Get service status
gcloud run services describe SERVICE_NAME --format="value(status.conditions)"

# Fetch recent logs
gcloud run services logs read SERVICE_NAME --limit 100
```

**AI: Analyze logs for:**
- Container startup failures
- Health check timeouts
- Permission errors
- Resource limits exceeded
- Database connection issues

**AI: Report findings to user and suggest next step.**

---
allowed-tools: "*"

## Step 2: Common Issues & Quick Fixes

### Issue: App Crashes Immediately

**Symptoms:**
- "Crashed" status in Railway/GCP
- Container exits with error code

**Common Causes:**

1. **Missing Environment Variables**
   ```bash
   # Railway: Check vars
   railway vars
   
   # GCP: Check env vars
   gcloud run services describe SERVICE_NAME --format="value(spec.template.spec.containers[0].env)"
   ```
   
   **Fix:**
   ```bash
   # Railway: Set missing vars
   railway vars set VAR_NAME=value
   
   # GCP: Update service
   gcloud run services update SERVICE_NAME \
     --set-env-vars VAR_NAME=value
   ```

2. **Wrong Start Command**
   ```bash
   # Check railway.json or Cloud Run config
   cat railway.json
   ```
   
   **Fix:**
   ```json
   // railway.json
   {
     "deploy": {
       "startCommand": "node dist/index.js"  // Verify this path
     }
   }
   ```

3. **Port Not Matching**
   
   **Fix in code:**
   ```typescript
   const PORT = process.env.PORT || 8080;
   app.listen(PORT, () => {
     console.log(`Server listening on port ${PORT}`);
   });
   ```

**AI: After applying fix, redeploy and verify:**
```bash
# Railway
railway up

# GCP
gcloud run deploy SERVICE_NAME --source .
```

---
allowed-tools: "*"

### Issue: Health Check Timeout

**Symptoms:**
- Deployment shows "Unhealthy"
- Health check endpoint timing out

**Common Causes:**

1. **No Health Endpoint**
   
   **Fix: Add health endpoint:**
   ```typescript
   // Express.js
   app.get('/health', (req, res) => {
     res.status(200).json({ 
       status: 'healthy',
       timestamp: new Date().toISOString()
     });
   });
   
   // FastAPI
   @app.get("/health")
   def health():
       return {"status": "healthy"}
   ```

2. **Slow Startup**
   
   **Fix: Increase timeout in railway.json:**
   ```json
   {
     "deploy": {
       "healthcheckTimeout": 300  // Increase to 300s
     }
   }
   ```

3. **Database Blocking Startup**
   
   **Fix: Make DB connection non-blocking:**
   ```typescript
   // Don't wait for DB in startup
   app.listen(PORT, () => {
     console.log('Server started');
     // Connect to DB asynchronously
     connectDatabase().catch(console.error);
   });
   ```

**AI: After fix, redeploy and run health check:**
```bash
./tools/health-check.sh https://your-app.railway.app
```

---
allowed-tools: "*"

### Issue: Database Connection Failed

**Symptoms:**
- "ECONNREFUSED" errors
- "Connection timeout" errors
- "Authentication failed" errors

**Common Causes:**

1. **DATABASE_URL Not Set**
   
   **Fix:**
   ```bash
   # Railway: Check and set
   railway vars | grep DATABASE_URL
   railway vars set DATABASE_URL=postgresql://...
   
   # GCP: Update secret
   gcloud run services update SERVICE_NAME \
     --set-secrets DATABASE_URL=db-url:latest
   ```

2. **Database Not Provisioned**
   
   **Fix:**
   ```bash
   # Railway: Provision database
   ./infra/railway/scripts/railway-provision-db.sh
   
   # GCP: Create Cloud SQL instance
   gcloud sql instances create my-db \
     --database-version=POSTGRES_15 \
     --tier=db-f1-micro \
     --region=us-central1
   ```

3. **Migrations Not Run**
   
   **Fix:**
   ```bash
   # Run migrations
   railway run npm run migrate
   
   # Or in GCP
   gcloud run jobs execute migrate-job
   ```

**AI: Verify database connection:**
```bash
# Test connection
railway run node -e "require('pg').Client({connectionString:process.env.DATABASE_URL}).connect().then(() => console.log('Connected!'))"
```

---
allowed-tools: "*"

## Step 3: Rollback Decision

**AI: Ask user:**

Can the issue be fixed quickly (< 5 minutes)?

**If YES:** Apply fix and redeploy (see Step 2)

**If NO:** Proceed to rollback (Step 4)

---
allowed-tools: "*"

## Step 4: Rollback to Previous Version

### Railway Rollback

**AI: Execute rollback:**

```bash
# View deployment history
railway logs --deployment-id

# Rollback to previous deployment
railway rollback
```

**AI: Verify rollback:**
```bash
# Check status
railway status

# Run health check
./tools/health-check.sh https://your-app.railway.app

# Check logs for errors
railway logs --num 50
```

**AI: Report to user:**
- Rollback status (success/failure)
- Current deployment version
- Health check results

---
allowed-tools: "*"

### GCP Rollback

**AI: Execute rollback:**

```bash
# List revisions
gcloud run revisions list --service=SERVICE_NAME

# Identify previous revision (second in list)
PREVIOUS_REVISION=$(gcloud run revisions list --service=SERVICE_NAME --format="value(name)" --limit=2 | tail -1)

# Rollback traffic to previous revision
gcloud run services update-traffic SERVICE_NAME \
  --to-revisions=$PREVIOUS_REVISION=100
```

**AI: Verify rollback:**
```bash
# Check service status
gcloud run services describe SERVICE_NAME

# Run health check
./tools/health-check.sh https://SERVICE_NAME-xxx.run.app

# Check logs
gcloud run services logs read SERVICE_NAME --limit 50
```

**AI: Report to user:**
- Rollback status
- Previous revision now serving 100% traffic
- Health check results

---
allowed-tools: "*"

## Step 5: Root Cause Analysis

**AI: Help user investigate:**

1. **Compare deployments:**
   ```bash
   # What changed between working and broken?
   git diff WORKING_COMMIT BROKEN_COMMIT
   ```

2. **Check for common issues:**
   - New dependencies added?
   - Environment variables changed?
   - Database schema changed?
   - External API changes?

3. **Review logs systematically:**
   ```bash
   # Railway: Full logs from failed deployment
   railway logs --num 500 > failed-deployment.log
   
   # GCP: Export logs
   gcloud logging read "resource.type=cloud_run_revision" \
     --limit 500 > failed-deployment.log
   ```

4. **Document findings:**
   ```bash
   # Create incident report
   cat > .cfoi/branches/$(git rev-parse --abbrev-ref HEAD)/incidents/$(date +%Y%m%d-%H%M%S).md <<EOF
   # Deployment Incident Report
   
   **Date:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
   **Platform:** Railway/GCP
   **Symptom:** [describe]
   
   ## Timeline
   - [time]: Deployment initiated
   - [time]: Issue detected
   - [time]: Rollback completed
   
   ## Root Cause
   [describe what went wrong]
   
   ## Resolution
   [describe fix applied]
   
   ## Prevention
   [how to prevent in future]
   EOF
   ```

**AI: Suggest preventive measures based on root cause.**

---
allowed-tools: "*"

## Step 6: Fix and Redeploy

**AI: Once root cause identified:**

1. **Create fix branch:**
   ```bash
   git checkout -b fix/deployment-issue
   ```

2. **Apply fix** (based on root cause from Step 5)

3. **Test locally:**
   ```bash
   # Run tests
   npm test
   
   # Run verification
   ./tools/verify-implementation.sh
   
   # Test locally
   npm run dev
   # Manually verify fix works
   ```

4. **Deploy fix:**
   ```bash
   # Railway
   ./infra/railway/scripts/railway-deploy.sh
   
   # GCP
   gcloud run deploy SERVICE_NAME --source .
   ```

5. **Verify deployment:**
   ```bash
   # Run health check
   ./tools/health-check.sh https://your-app.com
   
   # Monitor logs for 5 minutes
   railway logs  # or gcloud run services logs read
   
   # Test critical paths manually
   ```

**AI: If deployment succeeds, document resolution in incident report.**

---
allowed-tools: "*"

## Step 7: Post-Recovery Checklist

**AI: Guide user through checklist:**

- [ ] Application is healthy and responding
- [ ] All critical endpoints working
- [ ] Database connections stable
- [ ] No errors in logs (last 100 lines)
- [ ] Health check passing
- [ ] Incident report documented
- [ ] Preventive measures identified
- [ ] Team notified (if applicable)

**AI: Create summary:**

```markdown
## Recovery Summary

**Issue:** [brief description]
**Duration:** [time from detection to resolution]
**Resolution:** [what fixed it]
**Rollback Required:** Yes/No

**Lessons Learned:**
1. [lesson 1]
2. [lesson 2]

**Action Items:**
1. [ ] [preventive measure 1]
2. [ ] [preventive measure 2]
```

---
allowed-tools: "*"

## Emergency Contacts & Resources

### Platform Status Pages
- Railway: https://status.railway.app
- GCP: https://status.cloud.google.com

### Documentation
- [DEPLOYMENT.md](../../docs/DEPLOYMENT.md) - Full deployment guide
- [TROUBLESHOOTING.md](../../docs/TROUBLESHOOTING.md) - Common issues
- Railway Docs: https://docs.railway.app
- GCP Docs: https://cloud.google.com/run/docs

### Support Channels
- Railway Discord: https://discord.gg/railway
- GCP Support: https://cloud.google.com/support

---
allowed-tools: "*"

**Recovery complete!** Document what happened and implement preventive measures to avoid recurrence. 🚀
