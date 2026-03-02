# 🚀 Quick Start - Deploy Your First MVP in 30 Minutes

**Goal:** Get from zero to a live, deployed MVP as fast as possible.
---

## ⚡ **Super Fast Track (For Impatient Developers)**

```bash
# 1. Copy the framework into your project root
cp -R /path/to/Infra-As-A-Service/* ./
cp -R /path/to/Infra-As-A-Service/.* ./ 2>/dev/null || true

# 2. Run setup script
./install.sh
# This configures git hooks, creates .cfoi/, and sets up npm scripts

# 3. Plan your first feature with Windsurf slash commands
# In Windsurf: /plan "create a landing page with email signup"

# 4. Push and open a PR (CI deploys your MVP automatically)
git checkout -b feature/landing-page
git add .
git commit -m "feat: landing page with email signup"
git push origin feature/landing-page
# Create the PR on GitHub

# 5. Your MVP is live! Check the PR comment for the URL 🎉
```

**That's it!** Workflows, hooks, docs, and slash commands are ready automatically.

### **Prerequisites:**

- GitHub account
- Google Cloud account (free tier works!)
- Git installed locally
- Node.js 18+ installed (or Docker)

---

### **Step 1: Copy & Install (2 minutes)**

```bash
# Copy the framework into your project repository
cp -R /path/to/Infra-As-A-Service/* ./
cp -R /path/to/Infra-As-A-Service/.* ./ 2>/dev/null || true

# Run the setup script
./install.sh
```

**What this does:**

- Copies `.windsurf/`, hooks, docs, tools, infra, and helpers into your project root
- Configures git hooks for quality enforcement
- Creates `.cfoi/` directory for planning artifacts
- Updates package.json with framework scripts (if package.json exists)
- Installs npm dependencies and Playwright (if package.json exists)

**For detailed instructions:** See [INSTALL.md](../../INSTALL.md)

---

### **Step 2: Google Cloud Setup (5 minutes)**

**If this is your first time**, you need to set up Google Cloud:

👉 **Follow the detailed guide:** [`docs/setup/SERVICES_GCP.md`](../setup/SERVICES_GCP.md)

**Quick version:**

```bash
# 1. Create GCP project at console.cloud.google.com
# 2. Enable required APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# 3. Create service account and download key
# 4. Add GitHub secrets:
#    - GCP_PROJECT_ID
#    - GCP_SA_KEY (paste entire JSON)
```

**Already set up?** Skip to Step 3!

> Need databases, auth, email, or storage? Check the service catalog in `docs/setup/`:
> - [`SERVICES_POSTGRES.md`](../setup/SERVICES_POSTGRES.md)
> - [`SERVICES_MONGODB.md`](../setup/SERVICES_MONGODB.md)
> - [`SERVICES_REDIS.md`](../setup/SERVICES_REDIS.md)
> - [`SERVICES_AUTH.md`](../setup/SERVICES_AUTH.md)
> - [`SERVICES_EMAIL.md`](../setup/SERVICES_EMAIL.md)
> - [`SERVICES_STORAGE.md`](../setup/SERVICES_STORAGE.md)
> - [`SECRETS_MANAGEMENT.md`](../setup/SECRETS_MANAGEMENT.md)

---

### **Step 3: Create Your First Effort & Plan (5 minutes)**

Use the multi-effort workflow to organize your work:

```bash
# Create your first effort
# In Windsurf chat, type: /effort-new
# Choose type: feature
# Name: landing-page
# Description: Create landing page with email signup

# Then plan it
# In Windsurf chat, type: /plan
```


**Example plan for a landing page:**

```markdown
User Story: Visitor can sign up for our waitlist

E2E Flow:

1. User visits landing page
2. User sees compelling headline and description
3. User enters email in signup form
4. User clicks "Join Waitlist" button
5. User sees success message
6. Email is stored in database

API Contracts:
POST /api/waitlist
Body: { email: string }
Returns: { success: true, message: string }

Domain Rules:

- Email must be valid format
- No duplicate emails allowed
- Return friendly error messages
```

---

### **Step 4: Break Down Into Tasks (3 minutes)**

```bash
# In Windsurf chat, type: /task
```

**Example task breakdown:**

```yaml
tasks:
  - name: Create landing page HTML/React
    time: 2 hours
  - name: Create email signup form component
    time: 1 hour
  - name: Create POST /api/waitlist endpoint
    time: 1 hour
  - name: Set up database connection
    time: 1 hour
  - name: Add email validation
    time: 30 min
  - name: Create success/error messages
    time: 30 min
  - name: Add E2E tests
    time: 1 hour
```

---

### **Step 5: Implement Your MVP (Variable)**

```bash
# For each task, use the /implement workflow
# In Windsurf chat, type: /implement

# Windsurf will guide you through:
# 1. Writing the code
# 2. Testing it works
# 3. Committing changes
```

**Tips for fast implementation:**

- Commit frequently (small, focused commits)

---

### **Step 6: Deploy to Production (2 minutes)**

```bash
# 1. Create a feature branch
git checkout -b feature/landing-page

# 2. Commit your changes
git add .
git commit -m "feat: landing page with email signup"

# 3. Push to GitHub
git push origin feature/landing-page

# 4. Create a Pull Request on GitHub
# GitHub will automatically deploy your app!
```

**What happens automatically:**

1. GitHub Actions triggers
2. Your app builds
3. Deploys to Google Cloud Run
4. Creates ephemeral environment
5. Runs all tests
6. Comments on PR with live URL

**Check your PR comments** for the live environment link! 🎉

---

### **Step 7: Test Your Live MVP (5 minutes)**

1. Click the URL in your PR comment
2. Test the signup form
3. Verify email gets stored
4. Share with friends for feedback!

---

## 🎓 **Common First-Time Questions**

### **Q: Where do I put my code?**

**A:** Depends on your language:

```bash
# Node.js/TypeScript
server.js           # Main entry point (already exists)
package.json        # Dependencies

# Python
app.py             # Main entry point
requirements.txt   # Dependencies

# Go
main.go           # Main entry point
go.mod            # Dependencies

# The Dockerfile will be auto-configured for your language
```

### **Q: How do I connect to a database?**

**A:** See the services guides in `docs/setup/`:

- **PostgreSQL:** [`docs/setup/SERVICES_DATABASE.md`](./docs/setup/SERVICES_DATABASE.md)
- **MongoDB:** [`docs/setup/SERVICES_MONGODB.md`](./docs/setup/SERVICES_MONGODB.md)
- **Redis:** [`docs/setup/SERVICES_REDIS.md`](./docs/setup/SERVICES_REDIS.md)

### **Q: How do I add authentication?**

**A:** See [`docs/setup/SERVICES_AUTH.md`](./docs/setup/SERVICES_AUTH.md)

Options: Firebase Auth, Auth0, Clerk, Supabase

### **Q: My deployment failed. What do I do?**

**A:** Check the GitHub Actions logs:

1. Go to your PR on GitHub
2. Click "Checks" tab
3. Click the failing job
4. Read the error message

Common issues:

- Missing environment variables → Check `.env.example`
- Port not 8080 → Cloud Run requires port 8080
- Health check failing → Add `/health` endpoint

### **Q: How do I run this locally?**

Quick version:

```bash
# Copy environment variables
cp .env.example .env
# Edit .env with your values

# Run locally
npm install
npm start

# Visit http://localhost:8080
```

### **Q: Can I use my own cloud provider?**

**A:** Yes! The workflows are cloud-agnostic. You'll need to:

1. Modify `.github/workflows/pr-env.yml` for your provider
2. Update `infra/pulumi/index.js` (or use Terraform)
3. See [`BROWNFIELD_INTEGRATION.md`](./BROWNFIELD_INTEGRATION.md)

---

## 🎯 **What to Build First (MVP Ideas)**

Not sure what to build? Here are common MVP patterns:

### **1. Landing Page + Waitlist**

- Static page with email signup
- Store emails in database
- Thank you page
- **Time:** 2-4 hours
- **Example:** [`examples/landing-page-waitlist/`](./examples/landing-page-waitlist/)

### **2. Simple CRUD App**

- User authentication
- Create/Read/Update/Delete items
- Basic UI
- **Time:** 1-2 days
- **Example:** [`examples/crud-with-auth/`](./examples/crud-with-auth/)

### **3. API Backend**

- REST API endpoints
- Data validation
- Authentication
- **Time:** 1 day
- **Example:** [`examples/api-backend/`](./examples/api-backend/)

### **4. Real-Time Chat**

- WebSocket connection
- Message broadcasting
- User presence
- **Time:** 1-2 days
- **Example:** [`examples/realtime-chat/`](./examples/realtime-chat/)

---

## 🚀 **Optimization Tips for Speed**

### **Code Faster:**

- Use `/agent-plan` for AI-powered planning
- Use `/implement` for guided implementation
- Copy from `examples/` directory
- Use ChatGPT/Claude for boilerplate code

### **Deploy Faster:**

- Commit small changes frequently
- Use PR comments for quick feedback
- Test in ephemeral environment before merging
- Automate everything with workflows

### **Learn Faster:**

- Read [`INTERN_LEARNING_PATH.md`](./docs/learning/INTERN_LEARNING_PATH.md)
- Check [`examples/`](./examples/) for patterns
- Ask in Windsurf chat for help
- Review other PRs in your organization

---

## 📚 **Next Steps After First Deploy**

1. **Add more features** using `/effort-new → /plan → /task → /implement` cycle
2. **Work on bugs/enhancements** using `/effort-new` to create separate efforts in same branch
3. **Configure custom domain** - See [`EPHEMERAL_SETUP.md`](./EPHEMERAL_SETUP.md)
4. **Launch to users!** 🎉

### **Working with Multiple Efforts**

After your feature is deployed, you might need to fix bugs or add enhancements:

```bash
# Create a bug fix effort
/effort-new
# Type: bug
# Name: fix-email-validation
# Description: Fix email validation edge case

# Plan and implement the bug fix
/plan
/task
/implement

# Switch back to add an enhancement
/effort-switch
# Or create a new enhancement effort
/effort-new

# See all your efforts
/effort-list
```


---

## 🆘 **Getting Stuck?**

1. **Ask Windsurf** - Type your question in the chat
2. **Check GitHub Issues** - Others may have same problem
3. **Ask your mentor** - That's what they're there for!

---

## ⏱️ **Timeline Summary**

- **First-time setup:** 10-15 minutes (one-time)
- **Plan MVP:** 5-10 minutes per feature
- **Implement feature:** 1-4 hours (depending on complexity)
- **Deploy & test:** 5 minutes (automatic)

**Total for simple landing page MVP:** 2-4 hours from zero to deployed! 🚀

---

**Ready to build?** Start with Step 1 above, and you'll have your MVP live in less than 30 minutes! 💪
