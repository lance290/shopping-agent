#!/bin/bash

# 📊 Developer Dashboard Script
# Provides comprehensive overview of development environment status

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

# Unicode symbols for better visual representation
SYMBOL_CHECK="✅"
SYMBOL_CROSS="❌"
SYMBOL_WARNING="⚠️"
SYMBOL_INFO="ℹ️"
SYMBOL_ROCKET="🚀"
SYMBOL_GEAR="⚙️"
SYMBOL_DATABASE="🗄️"
SYMBOL_HEALTH="💚"
SYMBOL_TEST="🧪"
SYMBOL_DEPLOY="🚀"
SYMBOL_MONITOR="📊"
SYMBOL_SECURITY="🔒"
SYMBOL_CODE="💻"
SYMBOL_DOCKER="🐳"
SYMBOL_CLOUD="☁️"
SYMBOL_TRAIN="🚂"

# Helper functions for colored output
print_header() {
    echo -e "${PURPLE}${SYMBOL_ROCKET} $1${NC}"
}

print_section() {
    echo -e "${CYAN}${SYMBOL_GEAR} $1${NC}"
}

print_success() {
    echo -e "${GREEN}${SYMBOL_CHECK} $1${NC}"
}

print_error() {
    echo -e "${RED}${SYMBOL_CROSS} $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}${SYMBOL_WARNING} $1${NC}"
}

print_info() {
    echo -e "${BLUE}${SYMBOL_INFO} $1${NC}"
}

print_status() {
    local status=$1
    local message=$2
    
    case $status in
        "success") print_success "$message" ;;
        "error") print_error "$message" ;;
        "warning") print_warning "$message" ;;
        *) print_info "$message" ;;
    esac
}

# Draw separator line
draw_separator() {
    echo -e "${GRAY}─────────────────────────────────────────────────────────────────${NC}"
}

# Get current timestamp
get_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# Check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Get version of a command
get_version() {
    local cmd=$1
    if command_exists "$cmd"; then
        case $cmd in
            "node") echo "$(node --version)" ;;
            "npm") echo "$(npm --version)" ;;
            "git") echo "$(git --version | cut -d' ' -f3)" ;;
            "docker") echo "$(docker --version | cut -d' ' -f3 | cut -d',' -f1)" ;;
            "docker-compose") echo "$(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)" ;;
            "gh") echo "$(gh --version | cut -d' ' -f3)" ;;
            "gcloud") echo "$(gcloud version | grep 'Google Cloud SDK' | cut -d' ' -f4)" ;;
            "railway") echo "$(railway version | cut -d' ' -f3)" ;;
            "pulumi") echo "$(pulumi version)" ;;
            *) echo "unknown" ;;
        esac
    else
        echo "not installed"
    fi
}

# System Overview
show_system_overview() {
    print_section "System Overview"
    draw_separator
    
    echo -e "${WHITE}Timestamp:${NC} $(get_timestamp)"
    echo -e "${WHITE}Project Root:${NC} $PROJECT_ROOT"
    echo -e "${WHITE}User:${NC} $(whoami)"
    echo -e "${WHITE}OS:${NC} $(uname -s) $(uname -r)"
    echo -e "${WHITE}Shell:${NC} $SHELL"
    echo ""
    
    # Development tools status
    echo -e "${WHITE}Development Tools:${NC}"
    local tools=("node" "npm" "git" "docker" "docker-compose" "gh" "gcloud" "railway" "pulumi")
    local tool_names=("Node.js" "npm" "Git" "Docker" "Docker Compose" "GitHub CLI" "Google Cloud" "Railway" "Pulumi")
    
    for i in "${!tools[@]}"; do
        local tool="${tools[$i]}"
        local name="${tool_names[$i]}"
        local version=$(get_version "$tool")
        
        if [[ "$version" == "not installed" ]]; then
            echo -e "  ${SYMBOL_CROSS} ${RED}$name:${NC} $version"
        else
            echo -e "  ${SYMBOL_CHECK} ${GREEN}$name:${NC} $version"
        fi
    done
    echo ""
}

# Environment Status
show_environment_status() {
    print_section "Environment Status"
    draw_separator
    
    if [[ -f "$ENV_FILE" ]]; then
        print_success ".env file exists"
        
        # Check key environment variables
        local env_vars=("NODE_ENV" "PORT" "DATABASE_URL" "REDIS_URL" "JWT_SECRET")
        local missing_vars=()
        
        for var in "${env_vars[@]}"; do
            if grep -q "^$var=" "$ENV_FILE"; then
                local value=$(grep "^$var=" "$ENV_FILE" | cut -d'=' -f2)
                if [[ -n "$value" ]]; then
                    echo -e "  ${SYMBOL_CHECK} $var: ${GREEN}configured${NC}"
                else
                    echo -e "  ${SYMBOL_WARNING} $var: ${YELLOW}empty${NC}"
                    missing_vars+=("$var")
                fi
            else
                echo -e "  ${SYMBOL_CROSS} $var: ${RED}missing${NC}"
                missing_vars+=("$var")
            fi
        done
        
        if [[ ${#missing_vars[@]} -eq 0 ]]; then
            print_success "All required environment variables configured"
        else
            print_warning "Missing environment variables: ${missing_vars[*]}"
        fi
    else
        print_error ".env file not found"
        print_info "Run: ./tools/setup-env.sh init"
    fi
    echo ""
}

# Database Status
show_database_status() {
    print_section "${SYMBOL_DATABASE} Database Status"
    draw_separator
    
    # Check if Docker is running
    if ! command_exists docker; then
        print_error "Docker not available"
        return
    fi
    
    # Check if docker-compose.dev.yml exists
    local compose_file="$PROJECT_ROOT/docker-compose.dev.yml"
    if [[ ! -f "$compose_file" ]]; then
        print_warning "docker-compose.dev.yml not found"
        return
    fi
    
    # Get container status
    echo -e "${WHITE}Container Status:${NC}"
    local containers=("postgres" "redis" "mongodb" "neo4j")
    local container_names=("PostgreSQL" "Redis" "MongoDB" "Neo4j")
    
    for i in "${!containers[@]}"; do
        local container="${containers[$i]}"
        local name="${container_names[$i]}"
        local status=$(docker-compose -f "$compose_file" ps -q "$container" | xargs docker inspect --format='{{.State.Status}}' 2>/dev/null || echo "not_found")
        
        case $status in
            "running")
                echo -e "  ${SYMBOL_CHECK} ${GREEN}$name:${NC} Running"
                ;;
            "exited")
                echo -e "  ${SYMBOL_WARNING} ${YELLOW}$name:${NC} Stopped"
                ;;
            "not_found")
                echo -e "  ${SYMBOL_CROSS} ${RED}$name:${NC} Not found"
                ;;
            *)
                echo -e "  ${SYMBOL_WARNING} ${YELLOW}$name:${NC} $status"
                ;;
        esac
    done
    echo ""
    
    # Test database connections
    echo -e "${WHITE}Connection Tests:${NC}"
    
    # PostgreSQL
    if command_exists psql; then
        if PGPASSWORD=postgres psql -h localhost -U postgres -d monorepo_dev -c "SELECT 1;" &>/dev/null; then
            print_success "PostgreSQL connection successful"
        else
            print_error "PostgreSQL connection failed"
        fi
    else
        print_warning "PostgreSQL client not available"
    fi
    
    # Redis
    if command_exists redis-cli; then
        if redis-cli -h localhost ping | grep -q PONG; then
            print_success "Redis connection successful"
        else
            print_error "Redis connection failed"
        fi
    else
        print_warning "Redis client not available"
    fi
    
    # MongoDB
    if command_exists mongosh; then
        if mongosh mongodb://admin:password@localhost:27017/monorepo_dev --eval "db.runCommand('ping')" &>/dev/null; then
            print_success "MongoDB connection successful"
        else
            print_error "MongoDB connection failed"
        fi
    else
        print_warning "MongoDB client not available"
    fi
    echo ""
}

# Git Status
show_git_status() {
    print_section "${SYMBOL_CODE} Git Status"
    draw_separator
    
    if ! git rev-parse --git-dir &> /dev/null; then
        print_warning "Not in a Git repository"
        return
    fi
    
    # Basic git info
    echo -e "${WHITE}Repository:${NC} $(git remote get-url origin 2>/dev/null || echo "local")"
    echo -e "${WHITE}Branch:${NC} $(git branch --show-current)"
    echo -e "${WHITE}Last Commit:${NC} $(git log -1 --format="%h - %s (%cr)")"
    echo ""
    
    # Working directory status
    local status=$(git status --porcelain)
    if [[ -z "$status" ]]; then
        print_success "Working directory clean"
    else
        print_warning "Working directory has changes"
        echo -e "${WHITE}Changes:${NC}"
        echo "$status" | head -10
        if [[ $(echo "$status" | wc -l) -gt 10 ]]; then
            echo -e "${GRAY}... and more${NC}"
        fi
    fi
    echo ""
    
    # Git hooks status
    local hooks_dir="$PROJECT_ROOT/.githooks"
    if [[ -d "$hooks_dir" ]]; then
        local hook_count=$(find "$hooks_dir" -name "*.sh" -type f | wc -l)
        echo -e "${WHITE}Git Hooks:${NC} $hook_count hooks available"
        
        # Check if hooks are installed
        local git_hooks_dir="$(git rev-parse --git-dir)/hooks"
        local installed_count=$(find "$git_hooks_dir" -type l | wc -l)
        echo -e "${WHITE}Installed Hooks:${NC} $installed_count hooks installed"
        
        if [[ $hook_count -eq $installed_count ]]; then
            print_success "All Git hooks installed"
        else
            print_warning "Some Git hooks not installed"
        fi
    else
        print_warning "No Git hooks directory found"
    fi
    echo ""
}

# Service Health
show_service_health() {
    print_section "${SYMBOL_HEALTH} Service Health"
    draw_separator
    
    # Run health check script if available
    if [[ -f "$PROJECT_ROOT/tools/health-check.sh" ]]; then
        print_info "Running health check..."
        if "$PROJECT_ROOT/tools/health-check.sh" development local 2>/dev/null; then
            print_success "Health check passed"
        else
            print_warning "Health check completed with issues"
        fi
    else
        print_warning "Health check script not found"
    fi
    echo ""
    
    # Check local services
    echo -e "${WHITE}Local Services:${NC}"
    
    # Check if development server is running
    if lsof -i :8080 &>/dev/null; then
        print_success "Development server running on port 8080"
    else
        print_warning "Development server not running on port 8080"
    fi
    
    # Check for other common ports
    local ports=("3000:Frontend" "4000:Backend" "5000:API" "8080:Dev Server")
    for port_info in "${ports[@]}"; do
        local port=$(echo "$port_info" | cut -d':' -f1)
        local service=$(echo "$port_info" | cut -d':' -f2)
        
        if lsof -i :$port &>/dev/null; then
            print_success "$service running on port $port"
        fi
    done
    echo ""
}

# Test Status
show_test_status() {
    print_section "${SYMBOL_TEST} Test Status"
    draw_separator
    
    # Check package.json for test scripts
    if [[ -f "$PROJECT_ROOT/package.json" ]]; then
        echo -e "${WHITE}Available Test Scripts:${NC}"
        local test_scripts=$(jq -r '.scripts | keys[] | select(test("test"))' "$PROJECT_ROOT/package.json" 2>/dev/null || echo "")
        
        if [[ -n "$test_scripts" ]]; then
            echo "$test_scripts" | while read script; do
                echo -e "  ${SYMBOL_CHECK} npm run $script"
            done
        else
            print_warning "No test scripts found in package.json"
        fi
    fi
    echo ""
    
    # Run service tests if available
    if [[ -f "$PROJECT_ROOT/tools/service-specific-tests.sh" ]]; then
        print_info "Running service tests..."
        if timeout 30 "$PROJECT_ROOT/tools/service-specific-tests.sh" all development &>/dev/null; then
            print_success "Service tests passed"
        else
            print_warning "Service tests failed or timed out"
        fi
    else
        print_warning "Service test script not found"
    fi
    echo ""
}

# Deployment Status
show_deployment_status() {
    print_section "${SYMBOL_DEPLOY} Deployment Status"
    draw_separator
    
    # Railway status
    if command_exists railway; then
        echo -e "${WHITE}Railway:${NC}"
        if railway whoami &>/dev/null; then
            print_success "Railway authenticated"
            
            # Get project status
            if railway status &>/dev/null; then
                local services=$(railway status --json 2>/dev/null | jq -r '.[] | "\(.name): \(.status)"' 2>/dev/null || echo "Unable to fetch status")
                echo -e "${WHITE}Services:${NC}"
                echo "$services" | while read service_info; do
                    if [[ -n "$service_info" ]]; then
                        local name=$(echo "$service_info" | cut -d':' -f1)
                        local status=$(echo "$service_info" | cut -d':' -f2)
                        if [[ "$status" == "running" ]]; then
                            echo -e "  ${SYMBOL_CHECK} ${GREEN}$name:${NC} $status"
                        else
                            echo -e "  ${SYMBOL_WARNING} ${YELLOW}$name:${NC} $status"
                        fi
                    fi
                done
            else
                print_warning "No Railway project linked"
            fi
        else
            print_error "Railway not authenticated"
            print_info "Run: railway login"
        fi
    else
        print_warning "Railway CLI not installed"
    fi
    echo ""
    
    # GCP status
    if command_exists gcloud; then
        echo -e "${WHITE}Google Cloud:${NC}"
        if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
            print_success "GCP authenticated"
            
            # Get current project
            local project=$(gcloud config get-value project 2>/dev/null || echo "not set")
            echo -e "${WHITE}Project:${NC} $project"
            
            # Get Cloud Run services
            if [[ "$project" != "not set" ]]; then
                local services=$(gcloud run services list --format="value(name,status)" 2>/dev/null || echo "")
                if [[ -n "$services" ]]; then
                    echo -e "${WHITE}Cloud Run Services:${NC}"
                    echo "$services" | while read service_info; do
                        if [[ -n "$service_info" ]]; then
                            local name=$(echo "$service_info" | cut -d' ' -f1)
                            local status=$(echo "$service_info" | cut -d' ' -f2)
                            if [[ "$status" == "RUNNING" ]]; then
                                echo -e "  ${SYMBOL_CHECK} ${GREEN}$name:${NC} $status"
                            else
                                echo -e "  ${SYMBOL_WARNING} ${YELLOW}$name:${NC} $status"
                            fi
                        fi
                    done
                else
                    print_warning "No Cloud Run services found"
                fi
            fi
        else
            print_error "GCP not authenticated"
            print_info "Run: gcloud auth login"
        fi
    else
        print_warning "Google Cloud CLI not installed"
    fi
    echo ""
}

# Security Status
show_security_status() {
    print_section "${SYMBOL_SECURITY} Security Status"
    draw_separator
    
    # Check for secrets validation
    if [[ -f "$PROJECT_ROOT/tools/validate-secrets.sh" ]]; then
        print_info "Running security validation..."
        if "$PROJECT_ROOT/tools/validate-secrets.sh" 2>/dev/null; then
            print_success "Security validation passed"
        else
            print_warning "Security validation found issues"
        fi
    else
        print_warning "Security validation script not found"
    fi
    echo ""
    
    # Check for exposed secrets
    echo -e "${WHITE}Security Checks:${NC}"
    
    # Check for common secret patterns in code
    local secret_patterns=("sk_test\|sk_live" "password\|secret" "api_key\|apikey" "token")
    local found_secrets=false
    
    for pattern in "${secret_patterns[@]}"; do
        if grep -r -i "$pattern" --include="*.js" --include="*.ts" --include="*.json" --exclude-dir=node_modules --exclude-dir=.git "$PROJECT_ROOT" | head -5 | grep -q .; then
            print_warning "Potential secrets found matching: $pattern"
            found_secrets=true
        fi
    done
    
    if [[ "$found_secrets" == "false" ]]; then
        print_success "No obvious secrets found in code"
    fi
    
    # Check .gitignore for sensitive files
    echo -e "${WHITE}Gitignore Security:${NC}"
    local sensitive_patterns=(".env" "*.key" "*.pem" "secrets" "credentials")
    local ignored_patterns=0
    
    if [[ -f "$PROJECT_ROOT/.gitignore" ]]; then
        for pattern in "${sensitive_patterns[@]}"; do
            if grep -q "^$pattern" "$PROJECT_ROOT/.gitignore"; then
                ((ignored_patterns++))
            fi
        done
        
        if [[ $ignored_patterns -eq ${#sensitive_patterns[@]} ]]; then
            print_success "All sensitive patterns in .gitignore"
        else
            print_warning "Some sensitive patterns missing from .gitignore"
        fi
    else
        print_error ".gitignore file not found"
    fi
    echo ""
}

# Performance Metrics
show_performance_metrics() {
    print_section "${SYMBOL_MONITOR} Performance Metrics"
    draw_separator
    
    # System resources
    echo -e "${WHITE}System Resources:${NC}"
    
    # CPU usage
    if command_exists top; then
        local cpu_usage=$(top -l 1 -n 0 | grep "CPU usage" | awk '{print $3}' | sed 's/%//' || echo "N/A")
        echo -e "  CPU Usage: ${cpu_usage}%"
    fi
    
    # Memory usage
    if command_exists vm_stat; then
        local memory_info=$(vm_stat | grep "Pages free" | awk '{print $3}' | sed 's/\.//')
        local free_memory=$((memory_info * 4096 / 1024 / 1024))
        echo -e "  Free Memory: ${free_memory}MB"
    fi
    
    # Disk usage
    local disk_usage=$(df -h "$PROJECT_ROOT" | awk 'NR==2 {print $5}')
    echo -e "  Disk Usage: $disk_usage"
    echo ""
    
    # Docker resources
    if command_exists docker; then
        echo -e "${WHITE}Docker Resources:${NC}"
        local container_count=$(docker ps -q | wc -l)
        local image_count=$(docker images -q | wc -l)
        local docker_size=$(docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}" | tail -n +2 | grep "Local Volumes" | awk '{print $3}' || echo "N/A")
        
        echo -e "  Running Containers: $container_count"
        echo -e "  Images: $image_count"
        echo -e "  Docker Size: $docker_size"
    fi
    echo ""
}

# Quick Actions
show_quick_actions() {
    print_section "Quick Actions"
    draw_separator
    
    echo -e "${WHITE}Common Commands:${NC}"
    echo -e "  ${SYMBOL_GEAR} Start development: ${CYAN}./.dev-scripts/start-dev.sh${NC}"
    echo -e "  ${SYMBOL_GEAR} Stop development: ${CYAN}./.dev-scripts/stop-dev.sh${NC}"
    echo -e "  ${SYMBOL_GEAR} Run all tests: ${CYAN}./.dev-scripts/test-all.sh${NC}"
    echo -e "  ${SYMBOL_GEAR} Validate environment: ${CYAN}./tools/validate-secrets.sh${NC}"
    echo -e "  ${SYMBOL_GEAR} Health check: ${CYAN}./tools/health-check.sh development local${NC}"
    echo -e "  ${SYMBOL_GEAR} Service tests: ${CYAN}./tools/service-specific-tests.sh all development${NC}"
    echo -e "  ${SYMBOL_GEAR} Deployment test: ${CYAN}./infra/test-deployment.sh comprehensive development${NC}"
    echo ""
    
    echo -e "${WHITE}Platform Commands:${NC}"
    echo -e "  ${SYMBOL_TRAIN} Railway deploy: ${CYAN}railway up${NC}"
    echo -e "  ${SYMBOL_CLOUD} GCP deploy: ${CYAN}gcloud run deploy SERVICE --image=IMAGE${NC}"
    echo ""
    
    echo -e "${WHITE}Setup Commands:${NC}"
    echo -e "  ${SYMBOL_ROCKET} Initial setup: ${CYAN}./tools/dev-setup.sh${NC}"
    echo -e "  ${SYMBOL_GEAR} Environment setup: ${CYAN}./tools/setup-env.sh${NC}"
    echo -e "  ${SYMBOL_GEAR} Sync secrets: ${CYAN}./tools/sync-secrets.sh push all${NC}"
    echo ""
}

# Main dashboard function
main() {
    clear
    echo -e "${PURPLE}"
    echo "📊 Developer Dashboard"
    echo "======================"
    echo -e "${NC}"
    
    show_system_overview
    show_environment_status
    show_database_status
    show_git_status
    show_service_health
    show_test_status
    show_deployment_status
    show_security_status
    show_performance_metrics
    show_quick_actions
    
    print_header "Dashboard Complete"
    echo -e "${GREEN}Last Updated: $(get_timestamp)${NC}"
    echo ""
    echo -e "${BLUE}Press Enter to refresh or 'q' to quit...${NC}"
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --watch, -w    Watch mode (refresh every 30 seconds)"
        echo "  --section, -s  Show specific section only"
        echo ""
        echo "Available sections:"
        echo "  system, env, database, git, health, test, deploy, security, perf, actions"
        exit 0
        ;;
    --watch|-w)
        while true; do
            main
            read -t 30 -r input
            if [[ "$input" == "q" ]]; then
                break
            fi
        done
        ;;
    --section|-s)
        section="${2:-}"
        case "$section" in
            "system") show_system_overview ;;
            "env") show_environment_status ;;
            "database") show_database_status ;;
            "git") show_git_status ;;
            "health") show_service_health ;;
            "test") show_test_status ;;
            "deploy") show_deployment_status ;;
            "security") show_security_status ;;
            "perf") show_performance_metrics ;;
            "actions") show_quick_actions ;;
            *)
                echo "Unknown section: $section"
                echo "Available: system, env, database, git, health, test, deploy, security, perf, actions"
                exit 1
                ;;
        esac
        ;;
    "")
        main
        ;;
    *)
        echo "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
