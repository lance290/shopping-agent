#!/usr/bin/env bash

# Optimization utilities
# Source this file after common.sh

# Prevent double-sourcing
[[ -n "${_TOOLS_LIB_OPTIMIZE_LOADED:-}" ]] && return 0
_TOOLS_LIB_OPTIMIZE_LOADED=1

# Optimize Docker images
optimize_docker() {
    print_header "Optimizing Docker Images"
    
    if ! command_exists docker; then
        warning "Docker not available. Skipping Docker optimization."
        return
    fi
    
    info "Cleaning up Docker resources..."
    
    # Remove unused containers
    docker container prune -f 2>/dev/null && success "Removed stopped containers"
    
    # Remove unused images
    docker image prune -f 2>/dev/null && success "Removed dangling images"
    
    # Remove unused volumes
    docker volume prune -f 2>/dev/null && success "Cleaned up unused volumes"
    
    # Clean build cache
    docker buildx prune -f 2>/dev/null && success "Cleaned build cache"
    
    echo ""
}

# Optimize Node.js dependencies
optimize_nodejs() {
    print_header "Optimizing Node.js Dependencies"
    
    if [[ ! -f "${PROJECT_ROOT:-.}/package.json" ]]; then
        warning "No package.json found. Skipping Node.js optimization."
        return
    fi
    
    local node_modules_size
    node_modules_size=$(get_dir_size "${PROJECT_ROOT:-.}/node_modules")
    info "Current node_modules size: ${node_modules_size}MB"
    
    # Clean npm cache
    npm cache clean --force 2>/dev/null && success "Cleaned npm cache"
    
    # Audit and fix
    npm audit fix 2>/dev/null && success "Fixed security vulnerabilities" || warning "Some vulnerabilities could not be fixed"
    
    # Dedupe
    npm dedupe 2>/dev/null && success "Deduplicated dependencies"
    
    local final_size
    final_size=$(get_dir_size "${PROJECT_ROOT:-.}/node_modules")
    info "Final node_modules size: ${final_size}MB"
    
    echo ""
}

# Optimize Git repository
optimize_git() {
    print_header "Optimizing Git Repository"
    
    if ! git rev-parse --git-dir &> /dev/null; then
        warning "Not in a Git repository. Skipping Git optimization."
        return
    fi
    
    local repo_size_before
    repo_size_before=$(du -sm .git 2>/dev/null | cut -f1 || echo "0")
    info "Current .git size: ${repo_size_before}MB"
    
    git gc --prune=now 2>/dev/null && success "Cleaned up unreachable objects"
    git repack -ad 2>/dev/null && success "Packed loose objects"
    git reflog expire --expire=now --all 2>/dev/null && success "Cleaned reflog"
    
    local repo_size_after
    repo_size_after=$(du -sm .git 2>/dev/null | cut -f1 || echo "0")
    info "Final .git size: ${repo_size_after}MB"
    
    echo ""
}

# Optimize file system
optimize_filesystem() {
    print_header "Optimizing File System"
    
    # Clean up log files older than 7 days
    find "${PROJECT_ROOT:-.}" -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true
    success "Cleaned old log files"
    
    # Clean up temporary files
    find "${PROJECT_ROOT:-.}" -name "*.tmp" -type f -delete 2>/dev/null || true
    find "${PROJECT_ROOT:-.}" -name "*.temp" -type f -delete 2>/dev/null || true
    find "${PROJECT_ROOT:-.}" -name ".DS_Store" -type f -delete 2>/dev/null || true
    success "Cleaned temporary files"
    
    echo ""
}

# Generate optimization report
generate_optimization_report() {
    print_header "Optimization Report"
    
    local project_size node_modules_size git_size
    project_size=$(get_dir_size "${PROJECT_ROOT:-.}")
    node_modules_size=$(get_dir_size "${PROJECT_ROOT:-.}/node_modules")
    git_size=$(get_dir_size "${PROJECT_ROOT:-.}/.git")
    
    echo ""
    echo -e "${CYAN}📊 Optimization Summary${NC}"
    echo ""
    echo -e "${BLUE}Project Statistics:${NC}"
    echo "  Total size: ${project_size}MB"
    echo "  node_modules: ${node_modules_size}MB"
    echo "  .git: ${git_size}MB"
    echo ""
    
    if [[ $node_modules_size -gt 500 ]]; then
        echo "  ⚠️  Large node_modules. Consider pruning unused packages."
    fi
    
    if [[ $git_size -gt 100 ]]; then
        echo "  ⚠️  Large .git directory. Consider running git gc more frequently."
    fi
    
    echo ""
    success "Optimization complete!"
}
