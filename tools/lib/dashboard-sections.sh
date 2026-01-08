#!/usr/bin/env bash

# Dashboard section functions
# Source this file after common.sh and database.sh

# Prevent double-sourcing
[[ -n "${_TOOLS_LIB_DASHBOARD_LOADED:-}" ]] && return 0
_TOOLS_LIB_DASHBOARD_LOADED=1

# System Overview
show_system_overview() {
    print_section "System Overview"
    draw_separator
    
    echo -e "${WHITE}Timestamp:${NC} $(timestamp)"
    echo -e "${WHITE}Project Root:${NC} $PROJECT_ROOT"
    echo -e "${WHITE}User:${NC} $(whoami)"
    echo -e "${WHITE}OS:${NC} $(uname -s) $(uname -r)"
    echo -e "${WHITE}Shell:${NC} $SHELL"
    echo ""
    
    echo -e "${WHITE}Development Tools:${NC}"
    local tools=("node" "npm" "git" "docker" "docker-compose" "gh" "gcloud" "railway" "pulumi")
    local tool_names=("Node.js" "npm" "Git" "Docker" "Docker Compose" "GitHub CLI" "Google Cloud" "Railway" "Pulumi")
    
    for i in "${!tools[@]}"; do
        local tool="${tools[$i]}"
        local name="${tool_names[$i]}"
        local version
        version=$(get_version "$tool")
        
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
    local env_file="${1:-$PROJECT_ROOT/.env}"
    
    print_section "Environment Status"
    draw_separator
    
    if [[ -f "$env_file" ]]; then
        success ".env file exists"
        
        local env_vars=("NODE_ENV" "PORT" "DATABASE_URL" "REDIS_URL" "JWT_SECRET")
        local missing_vars=()
        
        for var in "${env_vars[@]}"; do
            if grep -q "^$var=" "$env_file"; then
                local value
                value=$(grep "^$var=" "$env_file" | cut -d'=' -f2)
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
            success "All required environment variables configured"
        else
            warning "Missing environment variables: ${missing_vars[*]}"
        fi
    else
        error ".env file not found"
        info "Run: ./tools/setup-env.sh init"
    fi
    echo ""
}

# Git Status
show_git_status() {
    print_section "${SYMBOL_CODE} Git Status"
    draw_separator
    
    if ! git rev-parse --git-dir &> /dev/null; then
        warning "Not in a Git repository"
        return
    fi
    
    echo -e "${WHITE}Repository:${NC} $(git remote get-url origin 2>/dev/null || echo "local")"
    echo -e "${WHITE}Branch:${NC} $(git branch --show-current)"
    echo -e "${WHITE}Last Commit:${NC} $(git log -1 --format="%h - %s (%cr)")"
    echo ""
    
    local status
    status=$(git status --porcelain)
    if [[ -z "$status" ]]; then
        success "Working directory clean"
    else
        warning "Working directory has changes"
        echo -e "${WHITE}Changes:${NC}"
        echo "$status" | head -10
        if [[ $(echo "$status" | wc -l) -gt 10 ]]; then
            echo -e "${GRAY}... and more${NC}"
        fi
    fi
    echo ""
    
    local hooks_dir="$PROJECT_ROOT/.githooks"
    if [[ -d "$hooks_dir" ]]; then
        local hook_count
        hook_count=$(find "$hooks_dir" -name "*.sh" -type f 2>/dev/null | wc -l)
        echo -e "${WHITE}Git Hooks:${NC} $hook_count hooks available"
    fi
    echo ""
}

# Service Health
show_service_health() {
    print_section "${SYMBOL_HEALTH} Service Health"
    draw_separator
    
    echo -e "${WHITE}Local Services:${NC}"
    
    local ports=("3000:Frontend" "4000:Backend" "5000:API" "8080:Dev Server")
    for port_info in "${ports[@]}"; do
        local port="${port_info%%:*}"
        local service="${port_info#*:}"
        
        if lsof -i :"$port" &>/dev/null; then
            success "$service running on port $port"
        fi
    done
    echo ""
}

# Performance Metrics
show_performance_metrics() {
    print_section "${SYMBOL_MONITOR} Performance Metrics"
    draw_separator
    
    echo -e "${WHITE}System Resources:${NC}"
    
    # CPU usage (macOS)
    if command_exists top; then
        local cpu_usage
        cpu_usage=$(top -l 1 -n 0 2>/dev/null | grep "CPU usage" | awk '{print $3}' | sed 's/%//' || echo "N/A")
        echo -e "  CPU Usage: ${cpu_usage}%"
    fi
    
    # Disk usage
    local disk_usage
    disk_usage=$(df -h "$PROJECT_ROOT" 2>/dev/null | awk 'NR==2 {print $5}')
    echo -e "  Disk Usage: $disk_usage"
    echo ""
    
    # Docker resources
    if command_exists docker; then
        echo -e "${WHITE}Docker Resources:${NC}"
        local container_count image_count
        container_count=$(docker ps -q 2>/dev/null | wc -l)
        image_count=$(docker images -q 2>/dev/null | wc -l)
        
        echo -e "  Running Containers: $container_count"
        echo -e "  Images: $image_count"
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
    echo -e "  ${SYMBOL_GEAR} Health check: ${CYAN}./tools/health-check.sh development local${NC}"
    echo ""
}
