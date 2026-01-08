#!/bin/bash
# Railway Database Provisioning Script
# Automates database creation and connection

set -e

echo "🗄️  Railway Database Provisioning"
echo "================================="
echo ""

# Check Railway CLI
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found"
    exit 1
fi

# Check if logged in
if ! railway whoami &> /dev/null; then
    echo "❌ Not logged into Railway"
    exit 1
fi

# Check if project is linked
if ! railway status &> /dev/null; then
    echo "❌ No Railway project linked"
    exit 1
fi

echo "✅ Pre-flight checks passed"
echo ""

# Database selection
echo "Select database type:"
echo "1. PostgreSQL"
echo "2. MySQL"
echo "3. MongoDB"
echo "4. Redis"
echo ""
read -p "Choose (1-4): " -n 1 -r DB_TYPE
echo ""

case $DB_TYPE in
    1)
        DB_NAME="postgres"
        echo "📦 Provisioning PostgreSQL..."
        railway add --plugin postgresql
        ;;
    2)
        DB_NAME="mysql"
        echo "📦 Provisioning MySQL..."
        railway add --plugin mysql
        ;;
    3)
        DB_NAME="mongodb"
        echo "📦 Provisioning MongoDB..."
        railway add --plugin mongodb
        ;;
    4)
        DB_NAME="redis"
        echo "📦 Provisioning Redis..."
        railway add --plugin redis
        ;;
    *)
        echo "❌ Invalid selection"
        exit 1
        ;;
esac

echo ""
echo "⏳ Waiting for database to provision..."
sleep 10

echo ""
echo "✅ $DB_NAME provisioned successfully!"
echo ""

# Show connection info
echo "📋 Connection Details:"
echo "The DATABASE_URL environment variable has been automatically set."
echo ""
echo "To view the connection string:"
echo "  railway vars"
echo ""

# Offer to create .env file
read -p "Create local .env with connection string? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Fetching connection string..."
    
    # Get DATABASE_URL from Railway
    DB_URL=$(railway vars | grep DATABASE_URL | cut -d'=' -f2-)
    
    if [ -n "$DB_URL" ]; then
        echo "DATABASE_URL=$DB_URL" >> .env.local
        echo "✅ Added to .env.local"
        echo ""
        echo "⚠️  Remember: .env.local is gitignored. Never commit credentials!"
    else
        echo "⚠️  Could not fetch DATABASE_URL. Check Railway dashboard."
    fi
fi

echo ""
echo "🎉 Database setup complete!"
echo ""
echo "Next steps:"
echo "  1. Run migrations: npm run migrate"
echo "  2. Seed data: npm run seed"
echo "  3. Test connection: npm run db:check"
echo ""
