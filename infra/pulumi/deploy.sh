#!/bin/bash
# Multi-Cloud Deployment Script
# Usage: ./deploy.sh <environment> [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Usage
usage() {
    echo "Usage: $0 <environment> [options]"
    echo ""
    echo "Environments:"
    echo "  pr-<number>   Deploy PR preview (e.g., pr-123)"
    echo "  dev           Deploy to development"
    echo "  qa            Deploy to QA/staging"
    echo "  production    Deploy to production"
    echo ""
    echo "Options:"
    echo "  --preview     Run pulumi preview only (dry-run)"
    echo "  --yes         Auto-approve deployment"
    echo "  --destroy     Destroy infrastructure"
    echo "  --help        Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 dev                    # Deploy to dev (with approval prompt)"
    echo "  $0 pr-123 --yes           # Deploy PR preview (auto-approve)"
    echo "  $0 production --preview   # Preview production deployment"
    echo "  $0 pr-123 --destroy --yes # Destroy PR environment"
    exit 1
}

# Check arguments
if [ $# -lt 1 ]; then
    usage
fi

ENVIRONMENT=$1
shift

# Parse options
PREVIEW_ONLY=false
AUTO_APPROVE=false
DESTROY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --preview)
            PREVIEW_ONLY=true
            shift
            ;;
        --yes)
            AUTO_APPROVE=true
            shift
            ;;
        --destroy)
            DESTROY=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Validate environment
case $ENVIRONMENT in
    pr-*)
        echo -e "${YELLOW}Deploying PR environment: $ENVIRONMENT${NC}"
        ;;
    dev|qa|production)
        echo -e "${YELLOW}Deploying to: $ENVIRONMENT${NC}"
        ;;
    *)
        echo -e "${RED}Invalid environment: $ENVIRONMENT${NC}"
        usage
        ;;
esac

# Check if Pulumi is installed
if ! command -v pulumi &> /dev/null; then
    echo -e "${RED}Pulumi is not installed${NC}"
    echo "Install from: https://www.pulumi.com/docs/get-started/install/"
    exit 1
fi

# Check if stack config exists
STACK_FILE="Pulumi.$ENVIRONMENT.yaml"
if [ "$ENVIRONMENT" != "pr-"* ] && [ ! -f "$STACK_FILE" ]; then
    echo -e "${RED}Stack configuration not found: $STACK_FILE${NC}"
    echo "Create it from template or run: pulumi config"
    exit 1
fi

# For PR environments, check if template exists
if [[ "$ENVIRONMENT" == pr-* ]] && [ ! -f "$STACK_FILE" ]; then
    echo -e "${YELLOW}Creating PR stack from template...${NC}"
    cp Pulumi.pr-template.yaml "$STACK_FILE"
    echo -e "${GREEN}Created $STACK_FILE${NC}"
    echo -e "${YELLOW}Please update the configuration and re-run${NC}"
    exit 0
fi

# Select stack
echo -e "${GREEN}Selecting stack: $ENVIRONMENT${NC}"
pulumi stack select "$ENVIRONMENT" || pulumi stack init "$ENVIRONMENT"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    npm install
fi

# Build TypeScript if needed
if [ -f "tsconfig.json" ]; then
    echo -e "${YELLOW}Building TypeScript...${NC}"
    npm run build 2>/dev/null || tsc
fi

# Run deployment
if [ "$DESTROY" = true ]; then
    echo -e "${RED}Destroying infrastructure for: $ENVIRONMENT${NC}"
    if [ "$AUTO_APPROVE" = true ]; then
        pulumi destroy --yes
    else
        pulumi destroy
    fi
elif [ "$PREVIEW_ONLY" = true ]; then
    echo -e "${GREEN}Running preview for: $ENVIRONMENT${NC}"
    pulumi preview
else
    echo -e "${GREEN}Deploying to: $ENVIRONMENT${NC}"
    if [ "$AUTO_APPROVE" = true ]; then
        pulumi up --yes
    else
        pulumi up
    fi
fi

# Show outputs
if [ "$DESTROY" = false ]; then
    echo -e "${GREEN}Deployment complete!${NC}"
    echo -e "${YELLOW}Outputs:${NC}"
    pulumi stack output
fi
