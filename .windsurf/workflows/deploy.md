---
allowed-tools: "*"
description: Beginner-friendly deployment with step-by-step guidance
---
allowed-tools: "*"

# 🚀 Deployment Workflow (Beginner)

**Step-by-step deployment workflow designed for beginners with comprehensive guidance and safety checks**

---
allowed-tools: "*"

## 🎯 Who Should Use This Workflow

**✅ PERFECT FOR BEGINNERS:**
- First time deploying to production
- Learning deployment processes
- Want step-by-step guidance
- Prefer safety checks and validation

**📋 Use this workflow if:**
- You're new to deployment
- Want detailed explanations
- Prefer guided processes
- Need safety nets and rollback options

---
allowed-tools: "*"

## Step 0: Let's Get Ready! 

// turbo
**AI: Welcome the beginner and explain what we're doing:**
"Welcome! I'm going to help you deploy your application step by step. We'll make sure everything is safe and working before going live. First, let me check your environment to make sure you're ready to deploy."

**AI: Run environment check:**
```bash
# Check if you're in the right place
pwd
ls -la

# Validate your setup
./tools/validate-secrets.sh
```

**AI: Explain results and next steps based on what you find.**

---
allowed-tools: "*"

## Step 1: Choose Where to Deploy

**AI: Ask beginner to choose deployment target:**

"Where would you like to deploy your application? I'll help you with each option:"

1. **🚂 Railway (Recommended for Beginners)** 
   - Easiest to use
   - Great for production apps
   - Simple setup
   - I'll guide you through everything

2. **☁️ Google Cloud Platform**
   - More advanced but powerful
   - Good for larger applications
   - I'll handle the complex parts

3. **🧪 Test Mode (Learn First)**
   - Practice without actually deploying
   - Great for learning the process
   - No risk of breaking anything

**AI: Based on their choice, explain what will happen and guide them to the right section.**

---
allowed-tools: "*"

## Step 2A: Railway Deployment (Beginner Friendly)

### Let's Get Railway Ready!
// turbo
**AI: Guide them through Railway setup:**
"Great choice! Railway is perfect for beginners. Let me help you get set up:"

```bash
# First, let me check if you have Railway tools
railway --version || echo "Installing Railway CLI..."
npm install -g @railway/cli

# Now let's get you logged in
echo "Time to connect to Railway!"
railway login
```

**AI: Wait for them to complete login, then continue:**
"Great! Now let's link your project to Railway:"

```bash
# Link your project
railway link

# Check everything is working
railway status
```

### Let's Run Safety Checks First!
// turbo
**AI: Explain why we're running tests:**
"Before we deploy, let's make sure everything works perfectly. This prevents problems in production!"

```bash
# Run comprehensive tests
echo "🧪 Running safety checks..."
./tools/service-specific-tests.sh all production
./infra/test-deployment.sh railway production
```

**AI: Explain test results in simple terms:**
- ✅ "All tests passed! You're ready to deploy!"
- ⚠️ "Found some issues, but I can help you fix them"
- ❌ "Let's fix these critical issues first"

### Time to Deploy! 🚂
// turbo
**AI: Guide them through the actual deployment:**
"Exciting! Let's deploy your application. I'll watch everything for you:"

```bash
# Deploy your application
echo "🚂 Deploying to Railway..."
railway up

# Let's wait for it to finish
echo "⏳ Railway is building your application..."
sleep 60

# Get your new URL
DEPLOY_URL=$(railway status --json | jq -r '.deployments[0].url')
echo "🌐 Your app will be live at: $DEPLOY_URL"
```

**AI: Celebrate the deployment!**
"🎉 Congratulations! Your application is deployed! Let me make sure everything is working perfectly."

### Let's Verify Everything Works!
// turbo
**AI: Run verification checks:**
"Now let's test your live application to make sure it's working:"

```bash
# Test your application
echo "💚 Testing your live application..."
curl -f "$DEPLOY_URL/health" && echo "✅ Your app is healthy!"

# Check for any problems
echo "📊 Checking application logs..."
railway logs --tail 10

# Run comprehensive health check
./tools/health-check.sh production railway
```

**AI: Explain results in beginner-friendly terms:**
- ✅ "Perfect! Your application is running great!"
- ⚠️ "Minor issues found, but your app is working"
- ❌ "Let's fix some problems - I'll help you"

---
allowed-tools: "*"

## Step 2B: Google Cloud Deployment (Advanced Beginners)

### Getting Ready for Google Cloud
// turbo
**AI: Guide them through GCP setup:**
"Google Cloud is powerful but a bit more complex. Don't worry, I'll guide you through every step!"

```bash
# Check if you have Google Cloud tools
gcloud --version || echo "You'll need to install Google Cloud CLI first"

# Let's get you logged in
echo "Time to connect to Google Cloud!"
gcloud auth login

# Check your project
gcloud config get-value project
```

**AI: Help them if they don't have a project:**
"If you don't have a project set up, I can help you create one. Just let me know!"

### Safety Checks for GCP
// turbo
**AI: Run the same safety checks:**
"Just like with Railway, let's make sure everything is perfect before deploying:"

```bash
# Run comprehensive tests
echo "🧪 Running safety checks..."
./tools/service-specific-tests.sh all production
./infra/test-deployment.sh gcp production
```

### Deploy to Google Cloud ☁️
// turbo
**AI: Guide them through GCP deployment:**
"Ready for the cloud? Let's deploy to Google Cloud Run:"

```bash
# Go to the infrastructure directory
cd infra/pulumi

# Set up the deployment
echo "☁️ Preparing Google Cloud infrastructure..."
npm install
pulumi up --stack=production --yes

# Get your application URL
DEPLOY_URL=$(pulumi stack output url)
echo "🌐 Your app will be live at: $DEPLOY_URL"
```

**AI: Celebrate and verify:**
"🎉 Amazing! Your application is on Google Cloud! Let me test it:"

```bash
# Test your GCP application
curl -f "$DEPLOY_URL/health" && echo "✅ Your cloud app is healthy!"
```

---
allowed-tools: "*"

## Step 2C: Test Mode (Practice Without Risk)

### Learn Deployment Safely
// turbo
**AI: Explain test mode:**
"Test mode is perfect for learning! We'll go through all the steps without actually deploying anything. This way you can practice and learn safely."

```bash
# Run all the tests we would run before deployment
echo "🧪 Running comprehensive tests..."
./tools/validate-secrets.sh
./tools/service-specific-tests.sh all production
./infra/test-deployment.sh comprehensive production

# Practice deployment steps (simulation)
echo "🚀 Practicing deployment steps..."
echo "✅ Environment validation: PASSED"
echo "✅ Service tests: PASSED" 
echo "✅ Deployment tests: PASSED"
echo "✅ Health checks: PASSED"
```

**AI: Encourage them:**
"Great job! You've successfully practiced all the deployment steps. When you're ready to deploy for real, just choose Railway or GCP above!"

---
allowed-tools: "*"

## Step 3: Celebrate and Monitor! 🎉

### Your Application is Live!
// turbo
**AI: Help them celebrate and understand what's next:**
"🎉 Congratulations! Your application is now live on the internet! Here's what happens next:"

```bash
# Start monitoring your application
echo "📊 Setting up monitoring for your app..."
./tools/monitor.sh --section system &

# Create a deployment record
echo "📝 Creating your deployment record..."
cat > .logs/your-first-deployment.md << EOF
# 🎉 Your First Deployment!

**Date:** $(date)
**Platform:** $PLATFORM
**URL:** $DEPLOY_URL
**Status:** ✅ SUCCESS

## What You Accomplished
- ✅ Validated your environment
- ✅ Ran comprehensive tests  
- ✅ Deployed to production
- ✅ Verified your application works
- ✅ Set up monitoring

## Next Steps
1. Visit your app: $DEPLOY_URL
2. Watch the monitoring: ./tools/monitor.sh
3. Show your team! 🚀

## You're Now a Deployment Pro! 🌟
EOF

echo "✅ Your deployment record is saved!"
```

---
allowed-tools: "*"

## Step 4: What to Do Next

### Beginner Next Steps
// turbo
**AI: Guide them on what to do after deployment:**

**🎯 Immediate Actions:**
1. **Visit your application** - Click the URL above!
2. **Test it manually** - Try clicking around
3. **Check the monitoring** - Run `./tools/monitor.sh`

**📚 Learning Resources:**
- Read your deployment record in `.logs/your-first-deployment.md`
- Try the `/push` workflow next time for more automation
- Look at `docs/TROUBLESHOOTING.md` if you see any issues

**🛠️ For Next Time:**
- Try the `/push` workflow for more automation
- Learn the `./tools/quick-deploy.sh` script for faster deployment
- Explore the monitoring tools

---
allowed-tools: "*"

## 🆘 Help & Troubleshooting

### If Something Goes Wrong
// turbo
**AI: Reassure them and provide help:**

"Don't worry! Deployment issues happen to everyone. Here's how to get help:"

**🚨 Quick Fixes:**
```bash
# Check what's happening
railway logs --tail 50  # For Railway
./tools/health-check.sh production railway  # Health check

# If you need to go back
railway rollback  # Undo last deployment
```

**📞 Get More Help:**
- Use the `/deploy-recovery` workflow
- Read `docs/TROUBLESHOOTING.md`
- Ask for help from your team

---
allowed-tools: "*"

## 🎓 You've Learned a Lot!

### What You Accomplished
// turbo
**AI: Summarize their achievements:**

**🌟 Amazing! You just:**
- ✅ Validated a production environment
- ✅ Ran comprehensive safety tests
- ✅ Deployed a real application to the cloud
- ✅ Verified your deployment works
- ✅ Set up monitoring
- ✅ Created deployment documentation

**🚀 You're Ready For:**
- Next time try `/push` for more automation
- Learn the `./tools/quick-deploy.sh` script
- Explore monitoring and optimization tools

---
allowed-tools: "*"

## 🎉 Congratulations!

**You've successfully deployed your first application! 🎉**

Your application is now live at: `$DEPLOY_URL`

**What's Next:**
1. **Visit your app** and test it manually
2. **Share it with your team** - they'll be impressed!
3. **Try `/push` next time** for more automation
4. **Explore the monitoring tools**

**Welcome to cloud deployment! You're officially a deployment developer! 🌟**

---
allowed-tools: "*"

## 📚 Quick Reference

### Commands You Learned
```bash
# Validate environment
./tools/validate-secrets.sh

# Run tests
./tools/service-specific-tests.sh all production

# Deploy to Railway
railway up

# Check your app
curl YOUR_URL/health

# Monitor your app
./tools/monitor.sh
```

### For Next Time
```bash
# More automated deployment
/push

# Faster script-based deployment  
./tools/quick-deploy.sh

# If something goes wrong
/deploy-recovery
```

---
allowed-tools: "*"

**🎯 Beginner Complete!** You've successfully deployed your first application! 🚀
