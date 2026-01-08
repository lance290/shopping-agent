#!/usr/bin/env bash

# Setup module functions for dev-setup.sh
# Source this file after common.sh

# Prevent double-sourcing
[[ -n "${_TOOLS_LIB_SETUP_LOADED:-}" ]] && return 0
_TOOLS_LIB_SETUP_LOADED=1

# Package manager detection
PKG_MANAGER="npm"
PKG_INSTALL_CMD="npm install"

detect_package_manager() {
    local project_pkg_manager
    if [[ -f package.json ]]; then
        project_pkg_manager=$(jq -r '.packageManager // empty' package.json | cut -d'@' -f1)
    fi

    if [[ -n "${project_pkg_manager:-}" ]]; then
        PKG_MANAGER="$project_pkg_manager"
        PKG_INSTALL_CMD="$project_pkg_manager install"
    elif [[ -f pnpm-lock.yaml ]]; then
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
    if ! command_exists "$PKG_MANAGER"; then
        if [[ "$PKG_MANAGER" != "npm" ]]; then
            warning "$PKG_MANAGER not installed, falling back to npm"
            PKG_MANAGER="npm"
            PKG_INSTALL_CMD="npm install"
        fi
    fi
    
    info "Using package manager: $PKG_MANAGER"
}

# Check system requirements
check_system_requirements() {
    print_header "Checking System Requirements"
    
    local missing_deps=()
    local required_tools=("node" "npm" "git" "curl" "jq")
    
    for tool in "${required_tools[@]}"; do
        if ! command_exists "$tool"; then
            missing_deps+=("$tool")
        else
            success "$tool is installed"
        fi
    done
    
    # Check Node.js version
    if command_exists node; then
        local node_version major_version
        node_version=$(node --version | cut -d'v' -f2)
        major_version=$(echo "$node_version" | cut -d'.' -f1)
        if [[ $major_version -lt 16 ]]; then
            warning "Node.js version $node_version detected. Version 16+ recommended"
        else
            success "Node.js version $node_version is compatible"
        fi
    fi
    
    # Check optional tools
    local optional_tools=("docker" "docker-compose" "gh" "gcloud" "railway")
    for tool in "${optional_tools[@]}"; do
        if command_exists "$tool"; then
            success "$tool is available (optional)"
        else
            info "$tool not found (optional)"
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        error "Missing required dependencies: ${missing_deps[*]}"
        info "Please install missing dependencies:"
        echo "  • On macOS: brew install ${missing_deps[*]}"
        echo "  • On Ubuntu: sudo apt-get install ${missing_deps[*]}"
        return 1
    fi
}

# Setup environment variables
setup_environment() {
    local env_file="${1:-$PROJECT_ROOT/.env}"
    local env_example="${2:-$PROJECT_ROOT/.env.example}"
    
    print_header "Setting Up Environment"
    
    if [[ ! -f "$env_file" ]]; then
        if [[ -f "$env_example" ]]; then
            info "Creating .env from .env.example"
            cp "$env_example" "$env_file"
            success "Created .env file"
        else
            warning "No .env.example found, creating basic .env"
            cat > "$env_file" << 'EOF'
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
}

# Install dependencies
install_dependencies() {
    print_header "Installing Dependencies"
    
    cd "$PROJECT_ROOT" || return 1
    detect_package_manager
    
    # Clean up conflicting structures if needed
    if [[ "$PKG_MANAGER" == "npm" && -d node_modules/.pnpm ]]; then
        info "Cleaning pnpm-structured node_modules for npm"
        rm -rf node_modules
    elif [[ "$PKG_MANAGER" == "pnpm" && -d node_modules && ! -d node_modules/.pnpm ]]; then
        info "Cleaning npm-structured node_modules for pnpm"
        rm -rf node_modules
    fi
    
    if [[ -f "package.json" ]]; then
        info "Installing main dependencies"
        if $PKG_INSTALL_CMD; then
            success "Main dependencies installed"
        else
            error "Failed to install main dependencies"
            return 1
        fi
    fi
    
    # Install infra dependencies
    if [[ -d "infra" && -f "infra/package.json" ]]; then
        info "Installing infrastructure dependencies"
        cd infra || return 1
        $PKG_INSTALL_CMD && success "Infrastructure dependencies installed" || warning "Failed to install infrastructure dependencies"
        cd "$PROJECT_ROOT" || return 1
    fi
}

# Setup Git hooks
setup_git_hooks() {
    print_header "Setting Up Git Hooks"
    
    if ! git rev-parse --git-dir &> /dev/null; then
        warning "Not in a git repository. Skipping Git hooks setup"
        return
    fi
    
    local hooks_dir="$PROJECT_ROOT/.githooks"
    local git_hooks_dir
    git_hooks_dir="$(git rev-parse --git-dir)/hooks"
    
    if [[ -d "$hooks_dir" ]]; then
        info "Installing Git hooks"
        find "$hooks_dir" -name "*.sh" -exec chmod +x {} \;
        
        for hook in "$hooks_dir"/*; do
            local hook_name
            hook_name=$(basename "$hook")
            if [[ -f "$hook" && -x "$hook" ]]; then
                ln -sf "$hook" "$git_hooks_dir/$hook_name"
                success "Installed $hook_name hook"
            fi
        done
        
        # Node.js hooks
        local node_hooks_dir="$PROJECT_ROOT/.githooks-node"
        if [[ -d "$node_hooks_dir" ]]; then
            for hook in "$node_hooks_dir"/*.js; do
                local hook_name
                hook_name=$(basename "$hook" .js)
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
    print_header "Setting Up Development Scripts"
    
    find "$PROJECT_ROOT/tools" -name "*.sh" -exec chmod +x {} \;
    success "Made tool scripts executable"
    
    local shortcuts_dir="$PROJECT_ROOT/.dev-scripts"
    mkdir -p "$shortcuts_dir"
    
    # Create start script
    cat > "$shortcuts_dir/start-dev.sh" << 'EOF'
#!/bin/bash
echo "🚀 Starting development environment..."
[[ -f "docker-compose.dev.yml" ]] && docker-compose -f docker-compose.dev.yml up -d
npm run dev
echo "✅ Development environment started"
EOF
    chmod +x "$shortcuts_dir/start-dev.sh"
    
    # Create stop script
    cat > "$shortcuts_dir/stop-dev.sh" << 'EOF'
#!/bin/bash
echo "🛑 Stopping development environment..."
[[ -f "docker-compose.dev.yml" ]] && docker-compose -f docker-compose.dev.yml down
echo "✅ Development environment stopped"
EOF
    chmod +x "$shortcuts_dir/stop-dev.sh"
    
    # Create test script
    cat > "$shortcuts_dir/test-all.sh" << 'EOF'
#!/bin/bash
echo "🧪 Running all tests..."
npm test
./tools/service-specific-tests.sh all development
echo "✅ All tests completed"
EOF
    chmod +x "$shortcuts_dir/test-all.sh"
    
    success "Created development scripts in .dev-scripts/"
}

# Setup IDE configuration
setup_ide_config() {
    print_header "Setting Up IDE Configuration"
    
    local vscode_dir="$PROJECT_ROOT/.vscode"
    mkdir -p "$vscode_dir"
    
    if [[ ! -f "$vscode_dir/extensions.json" ]]; then
        cat > "$vscode_dir/extensions.json" << 'EOF'
{
  "recommendations": [
    "ms-vscode.vscode-json",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "ms-vscode.vscode-typescript-next",
    "ms-vscode.vscode-docker"
  ]
}
EOF
        success "Created VS Code extensions recommendations"
    fi
    
    if [[ ! -f "$vscode_dir/settings.json" ]]; then
        cat > "$vscode_dir/settings.json" << 'EOF'
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": { "source.fixAll.eslint": "explicit" },
  "files.exclude": { "**/node_modules": true, "**/dist": true }
}
EOF
        success "Created VS Code settings"
    fi
}

# Generate setup report
generate_setup_report() {
    print_header "Setup Complete"
    
    echo ""
    echo -e "${CYAN}🎉 Local development environment setup complete!${NC}"
    echo ""
    echo -e "${BLUE}📋 Next Steps:${NC}"
    echo ""
    echo -e "${YELLOW}Development:${NC}"
    echo "  • Start development: ./.dev-scripts/start-dev.sh"
    echo "  • Stop development: ./.dev-scripts/stop-dev.sh"
    echo "  • Run all tests: ./.dev-scripts/test-all.sh"
    echo ""
    echo -e "${YELLOW}Platform Setup:${NC}"
    echo "  • Railway: railway login && railway link"
    echo "  • GCP: gcloud auth login && gcloud config set project YOUR_PROJECT_ID"
    echo ""
    echo -e "${GREEN}✅ Happy coding!${NC}"
}
