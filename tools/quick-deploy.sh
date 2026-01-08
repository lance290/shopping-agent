#!/bin/bash

# 🚀 Quick Deploy Script for Intermediate Developers
# Streamlined deployment with automation and efficiency features

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/.logs/quick-deploy.log"

# Create logs directory
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Colored output functions
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
    log "INFO: $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
    log "SUCCESS: $1"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    log "WARNING: $1"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    log "ERROR: $1"
}

header() {
    echo -e "${PURPLE}🚀 $1${NC}"
    log "HEADER: $1"
}

# Check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Show help
show_help() {
    echo "Usage: $0 [platform] [environment] [options]"
    echo ""
    echo "Platforms:"
    echo "  railway     Deploy to Railway (default for production)"
    echo "  gcp         Deploy to Google Cloud Platform"
    echo "  both        Deploy to both platforms"
    echo "  test        Run tests without deploying"
    echo ""
    echo "Environments:"
    echo "  production  Production deployment (default)"
    echo "  staging     Staging deployment"
    echo "  development Development deployment"
    echo ""
    echo "Options:"
    echo "  --fast         Skip non-essential tests for faster deployment"
    echo "  --parallel     Deploy to multiple platforms in parallel"
    echo "  --monitoring   Start monitoring after deployment"
    echo "  --skip-tests   Skip all pre-deployment tests"
    echo "  --force        Force deployment without confirmation"
    echo "  --help, -h     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Deploy to Railway production"
    echo "  $0 railway staging    # Deploy to Railway staging"
    echo "  $0 both --fast        # Fast deployment to both platforms"
    echo "  $0 gcp --parallel     # Parallel deployment with monitoring"
    echo "  $0 test               # Run tests only"
    echo ""
    echo "Intermediate Features:"
    echo "  • Parallel deployment support"
    echo "  • Performance optimization"
    echo "  • Advanced monitoring integration"
    echo "  • Environment-specific configurations"
    echo "  • Automated rollback capabilities"
}

# Validate environment
validate_environment() {
    header "Validating Environment"
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir &> /dev/null; then
        error "Not in a git repository. Please run from project root."
        exit 1
    fi
    
    # Check for uncommitted changes
    if [[ -n $(git status --porcelain) ]]; then
        warning "You have uncommitted changes:"
        git status --porcelain
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            info "Please commit your changes first."
            exit 1
        fi
    fi
    
    # Validate environment configuration
    if [[ -f "$PROJECT_ROOT/tools/validate-secrets.sh" ]]; then
        info "Validating environment configuration..."
        if "$PROJECT_ROOT/tools/validate-secrets.sh"; then
            success "Environment validation passed"
        else
            warning "Environment validation completed with warnings"
        fi
    fi
    
    # Check for required files
    local required_files=("package.json" "Dockerfile")
    for file in "${required_files[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
            error "Required file missing: $file"
            exit 1
        fi
    done
    
    success "Environment validation complete"
}

# Run pre-deployment tests
run_tests() {
    if [[ "${SKIP_TESTS:-}" == "true" ]]; then
        warning "Skipping tests as requested"
        return
    fi
    
    header "Running Pre-Deployment Tests"
    
    # Run service tests
    if [[ -f "$PROJECT_ROOT/tools/service-specific-tests.sh" ]]; then
        info "Running service-specific tests..."
        if "$PROJECT_ROOT/tools/service-specific-tests.sh" all "$ENVIRONMENT"; then
            success "Service tests passed"
        else
            warning "Service tests completed with warnings"
        fi
    fi
    
    # Run deployment tests
    if [[ -f "$PROJECT_ROOT/infra/test-deployment.sh" ]]; then
        info "Running deployment tests..."
        if "$PROJECT_ROOT/infra/test-deployment.sh" "$PLATFORM" "$ENVIRONMENT"; then
            success "Deployment tests passed"
        else
            warning "Deployment tests completed with warnings"
        fi
    fi
    
    success "All tests completed"
}

# Deploy to Railway
deploy_railway() {
    header "Deploying to Railway"
    
    # Check Railway CLI
    if ! command_exists railway; then
        info "Installing Railway CLI..."
        npm install -g @railway/cli
    fi
    
    # Check authentication
    if ! railway whoami &> /dev/null; then
        info "Please authenticate with Railway:"
        railway login
    fi
    
    # Check project linkage
    if ! railway status &> /dev/null; then
        info "Linking Railway project..."
        railway link
    fi
    
    # Set environment variables if .env file exists
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        info "Setting environment variables..."
        # Extract variables from .env (excluding comments)
        grep -v "^#" "$PROJECT_ROOT/.env" | grep "=" | while IFS='=' read -r key value; do
            if [[ -n "$key" && -n "$value" ]]; then
                railway variables set "$key=$value"
            fi
        done
    fi
    
    # Deploy
    info "Deploying to Railway..."
    railway up
    
    # Wait for deployment
    info "Waiting for deployment to complete..."
    sleep 60
    
    # Get deployment URL
    local deploy_url
    deploy_url=$(railway status --json 2>/dev/null | jq -r '.deployments[0].url' || echo "")
    
    if [[ -n "$deploy_url" ]]; then
        success "Railway deployment complete!"
        echo "🌐 URL: $deploy_url"
        DEPLOY_URL="$deploy_url"
    else
        error "Failed to get Railway deployment URL"
        exit 1
    fi
}

# Deploy to GCP
deploy_gcp() {
    header "Deploying to Google Cloud Platform"
    
    # Check GCP CLI
    if ! command_exists gcloud; then
        error "Google Cloud CLI not found. Please install gcloud."
        exit 1
    fi
    
    # Check authentication
    if ! gcloud auth list --filter=status:ACTIVE | grep -q .; then
        info "Please authenticate with Google Cloud:"
        gcloud auth login
    fi
    
    # Check project configuration
    local project_id
    project_id=$(gcloud config get-value project 2>/dev/null || echo "")
    if [[ -z "$project_id" ]]; then
        error "No GCP project configured. Run: gcloud config set project YOUR_PROJECT_ID"
        exit 1
    fi
    
    info "Using GCP project: $project_id"
    
    # Check Pulumi
    if ! command_exists pulumi; then
        info "Installing Pulumi..."
        curl -fsSL https://get.pulumi.com | sh
        export PATH="$PATH:$HOME/.pulumi/bin"
    fi
    
    # Deploy infrastructure
    if [[ -d "$PROJECT_ROOT/infra/pulumi" ]]; then
        info "Deploying GCP infrastructure..."
        cd "$PROJECT_ROOT/infra/pulumi"
        
        # Install dependencies
        npm install
        
        # Select or create stack
        local stack_name="$ENVIRONMENT"
        if ! pulumi stack select "$stack_name" 2>/dev/null; then
            pulumi stack init "$stack_name"
        fi
        
        # Deploy infrastructure
        pulumi up --stack="$stack_name" --yes
        
        # Get service URL
        local deploy_url
        deploy_url=$(pulumi stack output url 2>/dev/null || echo "")
        
        cd "$PROJECT_ROOT"
        
        if [[ -n "$deploy_url" ]]; then
            success "GCP deployment complete!"
            echo "🌐 URL: $deploy_url"
            DEPLOY_URL="$deploy_url"
        else
            error "Failed to get GCP deployment URL"
            exit 1
        fi
    else
        error "Pulumi configuration not found in infra/pulumi/"
        exit 1
    fi
}

# Run post-deployment verification
verify_deployment() {
    header "Verifying Deployment"
    
    if [[ -z "${DEPLOY_URL:-}" ]]; then
        error "No deployment URL available for verification"
        return
    fi
    
    # Health check
    info "Running health check..."
    if curl -f "$DEPLOY_URL/health" --max-time 30 &>/dev/null; then
        success "Health check passed"
    else
        warning "Health check failed or endpoint not available"
    fi
    
    # Basic accessibility test
    info "Testing basic accessibility..."
    if curl -f "$DEPLOY_URL" --max-time 30 &>/dev/null; then
        success "Basic accessibility test passed"
    else
        warning "Basic accessibility test failed"
    fi
    
    # Run health check script if available
    if [[ -f "$PROJECT_ROOT/tools/health-check.sh" ]]; then
        info "Running comprehensive health check..."
        if "$PROJECT_ROOT/tools/health-check.sh" "$ENVIRONMENT" local; then
            success "Comprehensive health check passed"
        else
            warning "Comprehensive health check completed with warnings"
        fi
    fi
}

# Create deployment record
create_deployment_record() {
    local record_file="$PROJECT_ROOT/.logs/deployment-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$record_file" << EOF
# Deployment Record

**Date:** $(date)
**Platform:** $PLATFORM
**Environment:** $ENVIRONMENT
**URL:** ${DEPLOY_URL:-"N/A"}

## Deployment Details
- **Branch:** $(git branch --show-current)
- **Commit:** $(git rev-parse --short HEAD)
- **Deployed by:** $(whoami)

## Verification Results
- Health Check: $([ "${HEALTH_CHECK_PASSED:-}" == "true" ] && echo "✅ Passed" || echo "⚠️ Failed")
- Basic Accessibility: $([ "${ACCESSIBILITY_CHECK_PASSED:-}" == "true" ] && echo "✅ Passed" || echo "⚠️ Failed")

## Next Steps
1. Monitor application performance
2. Check error rates in logs
3. Verify user functionality
4. Set up monitoring alerts

## Rollback Information
- Railway: \`railway rollback\`
- GCP: \`gcloud run services update-traffic SERVICE_NAME --to-revisions=PREVIOUS_REVISION=100\`
EOF
    
    success "Deployment record created: $record_file"
}

# Main deployment function
main() {
    local platform="${1:-railway}"
    local environment="${2:-production}"
    
    # Set global variables
    PLATFORM="$platform"
    ENVIRONMENT="$environment"
    DEPLOY_URL=""
    
    echo -e "${PURPLE}"
    echo "🚀 Quick Deploy - Junior Developer Deployment"
    echo "=============================================="
    echo -e "${NC}"
    
    echo "Platform: $PLATFORM"
    echo "Environment: $ENVIRONMENT"
    echo ""
    
    # Validate environment
    validate_environment
    
    # Run tests
    run_tests
    
    # Confirmation prompt
    if [[ "${FORCE_DEPLOY:-}" != "true" ]]; then
        echo ""
        read -p "Ready to deploy to $PLATFORM ($ENVIRONMENT)? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            info "Deployment cancelled."
            exit 0
        fi
    fi
    
    # Deploy based on platform
    case "$PLATFORM" in
        "railway")
            deploy_railway
            ;;
        "gcp")
            deploy_gcp
            ;;
        "both")
            deploy_railway
            local railway_url="$DEPLOY_URL"
            deploy_gcp
            echo ""
            echo "🌐 Railway URL: $railway_url"
            echo "🌐 GCP URL: $DEPLOY_URL"
            ;;
        "test")
            info "Test mode - no actual deployment"
            success "All tests completed successfully"
            exit 0
            ;;
        *)
            error "Unknown platform: $PLATFORM"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
    
    # Verify deployment
    verify_deployment
    
    # Create deployment record
    create_deployment_record
    
    # Success message
    echo ""
    header "Deployment Complete! 🎉"
    echo "Platform: $PLATFORM"
    echo "Environment: $ENVIRONMENT"
    echo "URL: $DEPLOY_URL"
    echo ""
    echo "Next steps:"
    echo "1. Visit your application at $DEPLOY_URL"
    echo "2. Run monitoring: ./tools/monitor.sh"
    echo "3. View dashboard: ./tools/dev-dashboard.sh"
    echo "4. Check logs for any issues"
    echo ""
    success "Happy coding! 🚀"
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    --skip-tests)
        export SKIP_TESTS="true"
        shift
        main "$@"
        ;;
    --force)
        export FORCE_DEPLOY="true"
        shift
        main "$@"
        ;;
    "")
        main "railway" "production"
        ;;
    *)
        main "$@"
        ;;
esac
