#!/bin/bash
# Railway Deployment Script
# Automated deployment with pre-flight checks

set -e

echo "🚀 Railway Deployment"
echo "===================="
echo ""

# Check Railway CLI
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Install: npm install -g @railway/cli"
    exit 1
fi

# Check if logged in
if ! railway whoami &> /dev/null; then
    echo "❌ Not logged into Railway"
    echo "Run: railway login"
    exit 1
fi

# Check if project is linked
if ! railway status &> /dev/null; then
    echo "❌ No Railway project linked"
    echo "Run: ./infra/railway/scripts/railway-init.sh"
    exit 1
fi

echo "✅ Pre-flight checks passed"
echo ""

# Show current project
echo "Current project:"
railway status
echo ""

# Confirm deployment
CURRENT_BRANCH=$(git branch --show-current)
CURRENT_COMMIT=$(git rev-parse --short HEAD)

echo "Deploying:"
echo "  Branch: $CURRENT_BRANCH"
echo "  Commit: $CURRENT_COMMIT"
echo ""

read -p "Continue with deployment? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  Warning: You have uncommitted changes"
    git status --short
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled. Commit your changes first."
        exit 0
    fi
fi

# Select environment
echo "Select environment:"
echo "1. Production"
echo "2. Staging"
echo ""
read -p "Choose (1 or 2, default: 1): " -n 1 -r ENV_CHOICE
echo ""

if [ "$ENV_CHOICE" = "2" ]; then
    ENV="staging"
else
    ENV="production"
fi

echo "📦 Deploying to $ENV environment..."
echo ""

# Deploy
railway up --environment "$ENV"

DEPLOY_STATUS=$?

if [ $DEPLOY_STATUS -eq 0 ]; then
    echo ""
    echo "✅ Deployment successful!"
    echo ""
    
    # Get deployment URL
    echo "🌐 Deployment URL:"
    railway open --environment "$ENV" || echo "Run: railway open"
    
    echo ""
    echo "📊 View logs:"
    echo "  railway logs --environment $ENV"
    
    # Create deployment record
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    mkdir -p proof/deployments
    
    cat >> proof/deployments/railway.md <<EOF

## Deployment - $TIMESTAMP
- **Environment:** $ENV
- **Branch:** $CURRENT_BRANCH
- **Commit:** $CURRENT_COMMIT
- **Status:** ✅ Success
- **Command:** railway up --environment $ENV

EOF
    
    echo ""
    echo "📝 Deployment recorded in proof/deployments/railway.md"
else
    echo ""
    echo "❌ Deployment failed"
    echo ""
    echo "View logs for details:"
    echo "  railway logs --environment $ENV"
    exit 1
fi
