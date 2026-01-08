#!/bin/bash
# Railway Logs Viewer
# Stream or fetch Railway deployment logs

set -e

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

# Parse arguments
MODE="${1:-tail}"
LINES="${2:-100}"

case $MODE in
    tail|follow|stream)
        echo "📊 Streaming Railway logs (Ctrl+C to exit)..."
        echo ""
        railway logs --tail "$LINES"
        ;;
    recent|last)
        echo "📊 Recent Railway logs (last $LINES lines)..."
        echo ""
        railway logs --num "$LINES"
        ;;
    errors|error)
        echo "🔴 Filtering error logs..."
        echo ""
        railway logs --num 500 | grep -i "error\|exception\|fail"
        ;;
    *)
        echo "Usage: $0 [tail|recent|errors] [num_lines]"
        echo ""
        echo "Examples:"
        echo "  $0 tail 50      # Stream last 50 lines"
        echo "  $0 recent 200   # Show last 200 lines"
        echo "  $0 errors       # Show only errors from last 500 lines"
        exit 1
        ;;
esac
