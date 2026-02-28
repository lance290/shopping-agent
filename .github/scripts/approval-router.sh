#!/usr/bin/env bash
set -e

# ==============================================================================
# Approval Router Logic
# ==============================================================================
# This script encapsulates the decision logic for the Agent Approval Router.
# It is designed to be called from the GitHub Actions workflow.
#
# Environment Variables Required:
# - GH_TOKEN: GitHub token
# - PR_URL: URL of the Pull Request
#
# Usage: ./router.sh
# ==============================================================================

if [ -z "$GH_TOKEN" ] || [ -z "$PR_URL" ]; then
  echo "❌ Error: GH_TOKEN and PR_URL must be set."
  exit 1
fi

echo "🔍 Starting Approval Router analysis for $PR_URL..."

# ------------------------------------------------------------------------------
# 1. GATHER DATA
# ------------------------------------------------------------------------------

echo "📡 Fetching PR data..."
# optimize: single call to get everything we need?
# gh pr view is versatile.
# We need: labels, files, diff size?
# diff size requires 'gh pr diff' usually.

# Get Labels
LABELS_JSON=$(gh pr view "$PR_URL" --json labels -q '.labels[].name')

IS_OVERRIDE=false
IS_BLOCK=false
IS_VERIFIED=false

if echo "$LABELS_JSON" | grep -q "agent:approval-override"; then IS_OVERRIDE=true; fi
if echo "$LABELS_JSON" | grep -q "agent:approval-block"; then IS_BLOCK=true; fi
if echo "$LABELS_JSON" | grep -q "agent:verified"; then IS_VERIFIED=true; fi

echo "   - Labels: Verified=$IS_VERIFIED, Override=$IS_OVERRIDE, Block=$IS_BLOCK"

# Get Changed Files
CHANGED_FILES=$(gh pr diff "$PR_URL" --name-only)
echo "   - Files fetched."

# Get Diff Size
# Note: This can be slow for huge PRs, but necessary.
TOTAL_LINES=$(gh pr diff "$PR_URL" | wc -l)
echo "   - Diff size: $TOTAL_LINES lines"


# ------------------------------------------------------------------------------
# 2. DEFINE PATTERNS
# ------------------------------------------------------------------------------

# Prohibited (Tier 4)
PROHIBITED_PATTERN_ENV="\.env.*"
PROHIBITED_PATTERN_SECRETS="secrets/"
PROHIBITED_PATTERN_COMPLIANCE="compliance/"
FULL_PROHIBITED_REGEX="($PROHIBITED_PATTERN_ENV)|($PROHIBITED_PATTERN_SECRETS)|($PROHIBITED_PATTERN_COMPLIANCE)"

# Danger (Tier 2/3)
DANGER_PATTERN_DB="migration|migrations|schema|db|sql|procedure"
DANGER_PATTERN_AUTH="auth|oauth|jwt|security"
DANGER_PATTERN_PAYMENT="payment|stripe|billing"
DANGER_PATTERN_INFRA="infra|terraform|k8s|deploy|\.github/workflows"
DANGER_PATTERN_COMPLIANCE="compliance|hipaa|pii|phi"
FULL_DANGER_REGEX="($DANGER_PATTERN_DB)|($DANGER_PATTERN_AUTH)|($DANGER_PATTERN_PAYMENT)|($DANGER_PATTERN_INFRA)|($DANGER_PATTERN_COMPLIANCE)"


# ------------------------------------------------------------------------------
# 3. ANALYZE CONTENT
# ------------------------------------------------------------------------------

# Check Prohibited
IS_PROHIBITED=false
MATCHED_PROHIBITED=""
if echo "$CHANGED_FILES" | grep -Eq "$FULL_PROHIBITED_REGEX"; then
  IS_PROHIBITED=true
  MATCHED_PROHIBITED=$(echo "$CHANGED_FILES" | grep -E "$FULL_PROHIBITED_REGEX" | head -n 1)
  echo "🛑 MATCH PROHIBITED: $MATCHED_PROHIBITED"
fi

# Check Danger
IS_DANGER=false
DANGER_REASON=""
MATCHED_DANGER=""
if echo "$CHANGED_FILES" | grep -Eq "$FULL_DANGER_REGEX"; then
  IS_DANGER=true
  MATCHED_DANGER=$(echo "$CHANGED_FILES" | grep -E "$FULL_DANGER_REGEX" | head -n 1)
  DANGER_REASON="Touches danger path: $MATCHED_DANGER"
  echo "⚠️  MATCH DANGER: $MATCHED_DANGER"
fi

# Check Diff Size
IS_LARGE_DIFF=false
if [ "$TOTAL_LINES" -gt 200 ]; then
  IS_LARGE_DIFF=true
  echo "⚠️  LARGE DIFF: $TOTAL_LINES > 200"
fi


# ------------------------------------------------------------------------------
# 4. DETERMINE DECISION (PRECEDENCE LOGIC)
# ------------------------------------------------------------------------------

RISK_LEVEL="low"
REASON="Low Risk + Verified"
ACTION="approve"

if [ "$IS_PROHIBITED" = "true" ]; then
  RISK_LEVEL="prohibited"
  REASON="Touches PROHIBITED path: $MATCHED_PROHIBITED"
  ACTION="block"

elif [ "$IS_BLOCK" = "true" ]; then
  RISK_LEVEL="high"
  REASON="Manual Block Label (agent:approval-block)"
  ACTION="human"

elif [ "$IS_OVERRIDE" = "true" ]; then
  RISK_LEVEL="low"
  REASON="Manual Override Label (agent:approval-override)"
  ACTION="approve"

elif [ "$IS_VERIFIED" = "false" ]; then
  RISK_LEVEL="high"
  REASON="Missing verification (waiting for Verification Gates)"
  ACTION="human"

elif [ "$IS_DANGER" = "true" ]; then
  RISK_LEVEL="high"
  REASON="$DANGER_REASON"
  ACTION="human"

elif [ "$IS_LARGE_DIFF" = "true" ]; then
  RISK_LEVEL="high"
  REASON="Large diff (>200 lines)"
  ACTION="human"
fi

echo "🏁 Decision: ACTION=$ACTION, RISK=$RISK_LEVEL, REASON='$REASON'"


# ------------------------------------------------------------------------------
# 5. EXECUTE ACTIONS (IDEMPOTENT)
# ------------------------------------------------------------------------------

# Helper: Check if comment exists
comment_exists() {
  local search_str=$1
  gh pr view "$PR_URL" --json comments -q ".comments[].body" | grep -Fq "$search_str"
}

# Helper: Post comment
post_comment() {
  local body=$1
  local unique_marker=$2 # A string to check for existence
  
  if comment_exists "$unique_marker"; then
    echo "ℹ️  Comment already exists. Skipping."
  else
    echo "📝 Posting comment..."
    gh pr comment "$PR_URL" --body "$body"
  fi
}

# Helper: Manage Labels
# We use 'gh pr edit' which is generally idempotent (adding existing label is no-op)
update_labels() {
  local add=$1
  local remove=$2
  
  # Construct args only if non-empty
  local args=()
  [ -n "$add" ] && args+=(--add-label "$add")
  [ -n "$remove" ] && args+=(--remove-label "$remove")
  
  if [ ${#args[@]} -gt 0 ]; then
    echo "🏷️  Updating labels: +$add, -$remove"
    gh pr edit "$PR_URL" "${args[@]}" || true
  fi
}


case "$ACTION" in
  "block")
    echo "🛑 PROHIBITED PATH DETECTED"
    update_labels "agent:prohibited" "agent:approved"
    
    # Block comment
    post_comment "🛑 **BLOCKED: Prohibited Path Detected**<br>Reason: $REASON<br><br>This change touches Tier 4 prohibited files and cannot be auto-approved." "BLOCKED: Prohibited Path Detected"
    
    echo "❌ Exiting with failure to block merge."
    exit 1
    ;;

  "human")
    echo "👤 Routing to human review"
    update_labels "agent:needs-human" "agent:approved"
    
    # Warning comment
    # Use a generic marker "Routing to Human Review" to detect dupes
    post_comment "⚠️ **Routing to Human Review**<br>Reason: $REASON" "Routing to Human Review"
    ;;

  "approve")
    echo "✅ Approving PR"
    
    # Approve review (only if not already approved?)
    # 'gh pr review --approve' fails if you already approved. We should swallow that error or check first.
    # checking reviews is expensive. We'll just try and swallow error.
    gh pr review "$PR_URL" --approve --body "🤖 Auto-approved ($REASON)" || echo "ℹ️  Could not approve (already approved? or own PR?)"
    
    update_labels "agent:approved" "agent:needs-human"
    
    echo "🚀 Merging PR..."
    gh pr merge "$PR_URL" --squash --delete-branch || echo "⚠️  Merge failed (check PR status)"
    ;;
esac

echo "✅ Done."
exit 0
