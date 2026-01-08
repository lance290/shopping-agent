#!/bin/bash
# Railway Project Initialization Script
# Automates Railway CLI setup and project linking

set -e

echo "🚂 Railway Project Initialization"
echo "=================================="
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found"
    echo ""
    echo "Install Railway CLI:"
    echo "  npm install -g @railway/cli"
    echo ""
    echo "Or via Homebrew:"
    echo "  brew install railway"
    echo ""
    exit 1
fi

echo "✅ Railway CLI found: $(railway --version)"
echo ""

# Check if already logged in
if ! railway whoami &> /dev/null; then
    echo "🔐 Logging into Railway..."
    railway login
    echo ""
fi

echo "✅ Logged in as: $(railway whoami)"
echo ""

# Check if project is already linked
if railway status &> /dev/null; then
    echo "✅ Project already linked:"
    railway status
    echo ""
    read -p "Re-link to a different project? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Using existing project link."
        exit 0
    fi
fi

# Link or create new project
echo "Project Setup:"
echo "1. Link to existing project"
echo "2. Create new project"
echo ""
read -p "Choose option (1 or 2): " -n 1 -r OPTION
echo ""

if [ "$OPTION" = "1" ]; then
    echo "📎 Linking to existing Railway project..."
    railway link
elif [ "$OPTION" = "2" ]; then
    echo "🆕 Creating new Railway project..."
    read -p "Enter project name: " PROJECT_NAME
    railway init "$PROJECT_NAME"
else
    echo "❌ Invalid option"
    exit 1
fi

echo ""
echo "✅ Project linked successfully!"
echo ""

# Show current status
echo "Current project status:"
railway status
echo ""

# Ask about environment setup
read -p "Set up environment variables from .env.production? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f .env.production ]; then
        echo "📝 Setting environment variables..."
        railway vars --env production < .env.production
        echo "✅ Environment variables set"
    else
        echo "⚠️  .env.production not found"
        echo "Create it with your production variables:"
        echo "  DATABASE_URL=..."
        echo "  API_KEY=..."
    fi
fi

echo ""
echo "🎉 Railway initialization complete!"
echo ""
echo "Next steps:"
echo "  1. Deploy: railway up"
echo "  2. View logs: railway logs"
echo "  3. Open dashboard: railway open"
echo ""
