#!/bin/bash

# 🚀 Local Development Setup Script
# Sets up complete local development environment for monorepo

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
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"
LOG_FILE="$PROJECT_ROOT/.logs/dev-setup.log"

# Package manager detection
PKG_MANAGER="npm"
PKG_INSTALL_CMD="npm install"

detect_package_manager() {
    cd "$PROJECT_ROOT"
    if [[ -f pnpm-lock.yaml ]]; then
        PKG_MANAGER="pnpm"
        PKG_INSTALL_CMD="pnpm install"
    elif [[ -f yarn.lock ]]; then
        PKG_MANAGER="yarn"
        PKG_INSTALL_CMD="yarn install"
    elif [[ -f bun.lockb ]]; then
        PKG_MANAGER="bun"
        PKG_INSTALL_CMD="bun install"
    elif [[ -d node_modules/.pnpm ]]; then
        PKG_MANAGER="pnpm"
        PKG_INSTALL_CMD="pnpm install"
    else
        PKG_MANAGER="npm"
        PKG_INSTALL_CMD="npm install"
    fi
    
    # Fallback to npm if detected manager not installed
    if ! command -v "$PKG_MANAGER" &> /dev/null; then
        if [[ "$PKG_MANAGER" != "npm" ]]; then
            warning "$PKG_MANAGER not installed, falling back to npm"
            PKG_MANAGER="npm"
            PKG_INSTALL_CMD="npm install"
        fi
    fi
    
    info "Using package manager: $PKG_MANAGER"
}

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

# Check if running from project root
check_project_root() {
    if [[ ! -f "$PROJECT_ROOT/package.json" && ! -f "$PROJECT_ROOT/README.md" ]]; then
        error "This script must be run from the project root directory"
        echo "Usage: ./tools/dev-setup.sh"
        exit 1
    fi
}

# Check system requirements
check_system_requirements() {
    header "Checking System Requirements"
    
    local missing_deps=()
    
    # Check for required tools
    local required_tools=("node" "npm" "git" "curl" "jq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_deps+=("$tool")
        else
            success "$tool is installed"
        fi
    done
    
    # Check Node.js version
    if command -v node &> /dev/null; then
        local node_version=$(node --version | cut -d'v' -f2)
        local major_version=$(echo "$node_version" | cut -d'.' -f1)
        if [[ $major_version -lt 16 ]]; then
            warning "Node.js version $node_version detected. Version 16+ recommended"
        else
            success "Node.js version $node_version is compatible"
        fi
    fi
    
    # Check for optional tools
    local optional_tools=("docker" "docker-compose" "gh" "gcloud" "railway")
    for tool in "${optional_tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            success "$tool is available (optional)"
        else
            info "$tool not found (optional)"
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        error "Missing required dependencies: ${missing_deps[*]}"
        echo ""
        info "Please install missing dependencies:"
        echo "  • On macOS: brew install ${missing_deps[*]}"
        echo "  • On Ubuntu: sudo apt-get install ${missing_deps[*]}"
        echo "  • Node.js: https://nodejs.org/"
        exit 1
    fi
}

# Setup environment variables
setup_environment() {
    header "Setting Up Environment"
    
    # Copy .env.example if .env doesn't exist
    if [[ ! -f "$ENV_FILE" ]]; then
        if [[ -f "$ENV_EXAMPLE" ]]; then
            info "Creating .env from .env.example"
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            success "Created .env file"
        else
            warning "No .env.example found, creating basic .env"
            cat > "$ENV_FILE" << EOF
# Local Development Environment
NODE_ENV=development
PORT=8080

# Database URLs (for local development)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/monorepo_dev
REDIS_URL=redis://localhost:6379
MONGODB_URI=mongodb://localhost:27017/monorepo_dev
NEO4J_URI=bolt://localhost:7687

# External Services (use test keys)
JWT_SECRET=dev-secret-change-in-production
STRIPE_SECRET_KEY=sk_test_dummy_key
PINECONE_API_KEY=test_dummy_key

# Platform Configuration
GCP_PROJECT_ID=your-gcp-project-id
RAILWAY_TOKEN=your-railway-token
EOF
            success "Created basic .env file"
        fi
    else
        info ".env file already exists"
    fi
    
    # Validate environment
    if [[ -f "$PROJECT_ROOT/tools/validate-secrets.sh" ]]; then
        info "Validating environment configuration"
        chmod +x "$PROJECT_ROOT/tools/validate-secrets.sh"
        if "$PROJECT_ROOT/tools/validate-secrets.sh"; then
            success "Environment validation passed"
        else
            warning "Environment validation completed with warnings"
        fi
    fi
}

# Install dependencies
install_dependencies() {
    header "Installing Dependencies"
    
    cd "$PROJECT_ROOT"
    detect_package_manager
    
    # Clean up conflicting structures if needed
    if [[ "$PKG_MANAGER" == "npm" && -d node_modules/.pnpm ]]; then
        info "Cleaning pnpm-structured node_modules for npm"
        rm -rf node_modules
    elif [[ "$PKG_MANAGER" == "pnpm" && -d node_modules && ! -d node_modules/.pnpm ]]; then
        info "Cleaning npm-structured node_modules for pnpm"
        rm -rf node_modules
    fi
    
    # Install main dependencies
    if [[ -f "package.json" ]]; then
        info "Installing main dependencies"
        if $PKG_INSTALL_CMD; then
            success "Main dependencies installed"
        else
            error "Failed to install main dependencies"
            exit 1
        fi
    fi
    
    # Install tool dependencies
    if [[ -d "infra" && -f "infra/package.json" ]]; then
        info "Installing infrastructure dependencies"
        cd infra
        if $PKG_INSTALL_CMD; then
            success "Infrastructure dependencies installed"
        else
            warning "Failed to install infrastructure dependencies"
        fi
        cd "$PROJECT_ROOT"
    fi
    
    # Install Railway CLI
    if command -v npm &> /dev/null && ! command -v railway &> /dev/null; then
        info "Installing Railway CLI"
        npm install -g @railway/cli
        success "Railway CLI installed"
    fi
    
    # Install Pulumi CLI
    if command -v npm &> /dev/null && ! command -v pulumi &> /dev/null; then
        info "Installing Pulumi CLI"
        curl -fsSL https://get.pulumi.com | sh
        success "Pulumi CLI installed"
    fi
}

# Setup local databases
setup_databases() {
    header "Setting Up Local Databases"
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        warning "Docker not found. Skipping database setup"
        info "To set up local databases manually:"
        echo "  • PostgreSQL: brew install postgresql or sudo apt-get install postgresql"
        echo "  • Redis: brew install redis or sudo apt-get install redis-server"
        echo "  • MongoDB: brew install mongodb-community or sudo apt-get install mongodb"
        return
    fi
    
    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        warning "Docker Compose not found. Skipping database setup"
        return
    fi
    
    # Create docker-compose.dev.yml if it doesn't exist
    local compose_file="$PROJECT_ROOT/docker-compose.dev.yml"
    if [[ ! -f "$compose_file" ]]; then
        info "Creating docker-compose.dev.yml"
        cat > "$compose_file" << EOF
version: '3.8'

services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: monorepo_dev
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  mongodb:
    image: mongo:6
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: password
      MONGO_INITDB_DATABASE: monorepo_dev
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    healthcheck:
      test: ["CMD", "echo", "db.runCommand('ping').ok", "|", "mongo", "localhost:27017/test", "--quiet"]
      interval: 10s
      timeout: 5s
      retries: 5

  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/password
      NEO4J_PLUGINS: '["apoc"]'
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "password", "RETURN 1"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
  mongodb_data:
  neo4j_data:
EOF
        success "Created docker-compose.dev.yml"
    fi
    
    # Start databases
    info "Starting local databases"
    if docker-compose -f "$compose_file" up -d; then
        success "Local databases started"
        
        # Wait for databases to be ready
        info "Waiting for databases to be ready..."
        sleep 10
        
        # Test database connections
        if command -v psql &> /dev/null; then
            if PGPASSWORD=postgres psql -h localhost -U postgres -d monorepo_dev -c "SELECT 1;" &> /dev/null; then
                success "PostgreSQL connection successful"
            else
                warning "PostgreSQL connection failed"
            fi
        fi
        
        if command -v redis-cli &> /dev/null; then
            if redis-cli -h localhost ping | grep -q PONG; then
                success "Redis connection successful"
            else
                warning "Redis connection failed"
            fi
        fi
        
        info "Database URLs for .env:"
        echo "  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/monorepo_dev"
        echo "  REDIS_URL=redis://localhost:6379"
        echo "  MONGODB_URI=mongodb://admin:password@localhost:27017/monorepo_dev"
        echo "  NEO4J_URI=bolt://neo4j:password@localhost:7687"
    else
        error "Failed to start local databases"
        exit 1
    fi
}

# Setup Git hooks
setup_git_hooks() {
    header "Setting Up Git Hooks"
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir &> /dev/null; then
        warning "Not in a git repository. Skipping Git hooks setup"
        return
    fi
    
    local hooks_dir="$PROJECT_ROOT/.githooks"
    local git_hooks_dir="$(git rev-parse --git-dir)/hooks"
    
    if [[ -d "$hooks_dir" ]]; then
        info "Installing Git hooks"
        
        # Make hooks executable
        find "$hooks_dir" -name "*.sh" -exec chmod +x {} \;
        
        # Install hooks
        for hook in "$hooks_dir"/*; do
            local hook_name=$(basename "$hook")
            if [[ -f "$hook" && -x "$hook" ]]; then
                ln -sf "$hook" "$git_hooks_dir/$hook_name"
                success "Installed $hook_name hook"
            fi
        done
        
        # Enable Node.js hooks if available
        local node_hooks_dir="$PROJECT_ROOT/.githooks-node"
        if [[ -d "$node_hooks_dir" ]]; then
            for hook in "$node_hooks_dir"/*.js; do
                local hook_name=$(basename "$hook" .js)
                if [[ -f "$hook" ]]; then
                    ln -sf "$hook" "$git_hooks_dir/$hook_name"
                    success "Installed $hook_name hook (Node.js)"
                fi
            done
        fi
    else
        warning "No Git hooks directory found"
    fi
}

# Setup development scripts
setup_dev_scripts() {
    header "Setting Up Development Scripts"
    
    # Make all tool scripts executable
    find "$PROJECT_ROOT/tools" -name "*.sh" -exec chmod +x {} \;
    success "Made tool scripts executable"
    
    # Create development shortcuts
    local shortcuts_dir="$PROJECT_ROOT/.dev-scripts"
    mkdir -p "$shortcuts_dir"
    
    # Create start script
    cat > "$shortcuts_dir/start-dev.sh" << EOF
#!/bin/bash
# Start development environment

echo "🚀 Starting development environment..."

# Start databases
if [[ -f "docker-compose.dev.yml" ]]; then
    docker-compose -f docker-compose.dev.yml up -d
fi

# Start application
npm run dev

echo "✅ Development environment started"
EOF
    chmod +x "$shortcuts_dir/start-dev.sh"
    
    # Create stop script
    cat > "$shortcuts_dir/stop-dev.sh" << EOF
#!/bin/bash
# Stop development environment

echo "🛑 Stopping development environment..."

# Stop databases
if [[ -f "docker-compose.dev.yml" ]]; then
    docker-compose -f docker-compose.dev.yml down
fi

echo "✅ Development environment stopped"
EOF
    chmod +x "$shortcuts_dir/stop-dev.sh"
    
    # Create test script
    cat > "$shortcuts_dir/test-all.sh" << EOF
#!/bin/bash
# Run all tests

echo "🧪 Running all tests..."

# Run unit tests
npm test

# Run service tests
./tools/service-specific-tests.sh all development

# Run deployment tests
./infra/test-deployment.sh comprehensive development

echo "✅ All tests completed"
EOF
    chmod +x "$shortcuts_dir/test-all.sh"
    
    success "Created development scripts in .dev-scripts/"
}

# Setup IDE configuration
setup_ide_config() {
    header "Setting Up IDE Configuration"
    
    # Create VS Code configuration
    local vscode_dir="$PROJECT_ROOT/.vscode"
    mkdir -p "$vscode_dir"
    
    # Create extensions.json
    if [[ ! -f "$vscode_dir/extensions.json" ]]; then
        cat > "$vscode_dir/extensions.json" << EOF
{
  "recommendations": [
    "ms-vscode.vscode-json",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "ms-vscode.vscode-typescript-next",
    "formulahendry.auto-rename-tag",
    "christian-kohler.path-intellisense",
    "ms-vscode.vscode-docker",
    "googlecloudtools.cloudcode",
    "railway.railway"
  ]
}
EOF
        success "Created VS Code extensions recommendations"
    fi
    
    # Create settings.json
    if [[ ! -f "$vscode_dir/settings.json" ]]; then
        cat > "$vscode_dir/settings.json" << EOF
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "typescript.preferences.importModuleSpecifier": "relative",
  "emmet.includeLanguages": {
    "javascript": "javascriptreact"
  },
  "files.exclude": {
    "**/node_modules": true,
    "**/dist": true,
    "**/build": true,
    "**/.git": true,
    "**/.DS_Store": true,
    "**/Thumbs.db": true
  },
  "search.exclude": {
    "**/node_modules": true,
    "**/dist": true,
    "**/build": true,
    "**/.git": true
  }
}
EOF
        success "Created VS Code settings"
    fi
    
    # Create launch.json for debugging
    if [[ ! -f "$vscode_dir/launch.json" ]]; then
        cat > "$vscode_dir/launch.json" << EOF
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug Node.js",
      "type": "node",
      "request": "launch",
      "program": "\${workspaceFolder}/src/index.js",
      "console": "integratedTerminal",
      "restart": true,
      "runtimeExecutable": "nodemon"
    },
    {
      "name": "Debug Tests",
      "type": "node",
      "request": "launch",
      "program": "\${workspaceFolder}/node_modules/.bin/jest",
      "args": ["--runInBand"],
      "console": "integratedTerminal",
      "internalConsoleOptions": "neverOpen"
    }
  ]
}
EOF
        success "Created VS Code launch configuration"
    fi
}

# Run initial tests
run_initial_tests() {
    header "Running Initial Tests"
    
    # Test environment validation
    if [[ -f "$PROJECT_ROOT/tools/validate-secrets.sh" ]]; then
        info "Testing environment validation"
        if "$PROJECT_ROOT/tools/validate-secrets.sh"; then
            success "Environment validation test passed"
        else
            warning "Environment validation test completed with warnings"
        fi
    fi
    
    # Test service-specific tests
    if [[ -f "$PROJECT_ROOT/tools/service-specific-tests.sh" ]]; then
        info "Testing service-specific tests"
        if "$PROJECT_ROOT/tools/service-specific-tests.sh" all development; then
            success "Service-specific tests passed"
        else
            warning "Service-specific tests completed with warnings"
        fi
    fi
    
    # Test health check
    if [[ -f "$PROJECT_ROOT/tools/health-check.sh" ]]; then
        info "Testing health check"
        if "$PROJECT_ROOT/tools/health-check.sh" development local; then
            success "Health check test passed"
        else
            warning "Health check test completed with warnings"
        fi
    fi
}

# Generate setup report
generate_report() {
    header "Setup Complete"
    
    echo ""
    echo -e "${CYAN}🎉 Local development environment setup complete!${NC}"
    echo ""
    echo -e "${BLUE}📋 Next Steps:${NC}"
    echo ""
    
    # Environment
    echo -e "${YELLOW}Environment:${NC}"
    echo "  • Review and update .env file with your configuration"
    echo "  • Run: ./tools/validate-secrets.sh to validate configuration"
    echo ""
    
    # Databases
    echo -e "${YELLOW}Databases:${NC}"
    echo "  • Local databases are running via Docker"
    echo "  • Stop databases: docker-compose -f docker-compose.dev.yml down"
    echo "  • Restart databases: docker-compose -f docker-compose.dev.yml restart"
    echo ""
    
    # Development
    echo -e "${YELLOW}Development:${NC}"
    echo "  • Start development: ./.dev-scripts/start-dev.sh"
    echo "  • Stop development: ./.dev-scripts/stop-dev.sh"
    echo "  • Run all tests: ./.dev-scripts/test-all.sh"
    echo ""
    
    # Tools
    echo -e "${YELLOW}Available Tools:${NC}"
    echo "  • Environment setup: ./tools/setup-env.sh"
    echo "  • Validate secrets: ./tools/validate-secrets.sh"
    echo "  • Sync secrets: ./tools/sync-secrets.sh"
    echo "  • Health check: ./tools/health-check.sh"
    echo "  • Service tests: ./tools/service-specific-tests.sh"
    echo "  • Deployment tests: ./infra/test-deployment.sh"
    echo ""
    
    # Platform setup
    echo -e "${YELLOW}Platform Setup:${NC}"
    echo "  • Railway: railway login && railway link"
    echo "  • GCP: gcloud auth login && gcloud config set project YOUR_PROJECT_ID"
    echo ""
    
    # Help
    echo -e "${YELLOW}Getting Help:${NC}"
    echo "  • Documentation: ./docs/DEPLOYMENT.md"
    echo "  • Troubleshooting: ./docs/TROUBLESHOOTING.md"
    echo "  • Implementation plan: ./docs/MONOREPO_IMPLEMENTATION_PLAN.md"
    echo ""
    
    echo -e "${GREEN}✅ Happy coding!${NC}"
    
    # Log completion
    log "SETUP_COMPLETE: Local development environment setup completed successfully"
}

# Main function
main() {
    echo -e "${PURPLE}"
    echo "🚀 Local Development Setup"
    echo "=========================="
    echo -e "${NC}"
    
    check_project_root
    check_system_requirements
    setup_environment
    install_dependencies
    setup_databases
    setup_git_hooks
    setup_dev_scripts
    setup_ide_config
    run_initial_tests
    generate_report
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --skip-dbs     Skip database setup"
        echo "  --skip-hooks   Skip Git hooks setup"
        echo "  --skip-ide     Skip IDE configuration"
        echo ""
        exit 0
        ;;
    --skip-dbs)
        echo "Skipping database setup..."
        setup_databases() { info "Skipping database setup"; }
        main
        ;;
    --skip-hooks)
        echo "Skipping Git hooks setup..."
        setup_git_hooks() { info "Skipping Git hooks setup"; }
        main
        ;;
    --skip-ide)
        echo "Skipping IDE configuration..."
        setup_ide_config() { info "Skipping IDE configuration"; }
        main
        ;;
    "")
        main
        ;;
    *)
        error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
