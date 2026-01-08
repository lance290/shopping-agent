#!/bin/bash

# ⚡ Performance Optimization Script
# Optimizes development environment and production deployments

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
LOG_FILE="$PROJECT_ROOT/.logs/optimize.log"

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
    echo -e "${PURPLE}⚡ $1${NC}"
    log "HEADER: $1"
}

# Check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Get file size in MB
get_file_size() {
    local file=$1
    if [[ -f "$file" ]]; then
        echo "$(du -m "$file" | cut -f1)"
    else
        echo "0"
    fi
}

# Get directory size in MB
get_dir_size() {
    local dir=$1
    if [[ -d "$dir" ]]; then
        echo "$(du -sm "$dir" | cut -f1)"
    else
        echo "0"
    fi
}

# Optimize Docker images
optimize_docker() {
    header "Optimizing Docker Images"
    
    if ! command_exists docker; then
        warning "Docker not available. Skipping Docker optimization."
        return
    fi
    
    info "Cleaning up Docker resources..."
    
    # Remove unused containers
    local container_count=$(docker ps -a -q | wc -l)
    if [[ $container_count -gt 0 ]]; then
        info "Removing $container_count stopped containers..."
        docker container prune -f
        success "Removed stopped containers"
    fi
    
    # Remove unused images
    local image_count=$(docker images -f "dangling=true" -q | wc -l)
    if [[ $image_count -gt 0 ]]; then
        info "Removing $image_count dangling images..."
        docker image prune -f
        success "Removed dangling images"
    fi
    
    # Remove unused volumes
    local volume_size_before=$(docker system df --format "{{.Size}}" | grep "Local Volumes" | cut -d' ' -f1 || echo "0")
    info "Current volume size: $volume_size_before"
    
    docker volume prune -f
    success "Cleaned up unused volumes"
    
    # Clean build cache
    docker buildx prune -f
    success "Cleaned build cache"
    
    # Show system usage
    echo ""
    info "Docker system usage after cleanup:"
    docker system df
    echo ""
}

# Optimize Node.js dependencies
optimize_nodejs() {
    header "Optimizing Node.js Dependencies"
    
    if [[ ! -f "$PROJECT_ROOT/package.json" ]]; then
        warning "No package.json found. Skipping Node.js optimization."
        return
    fi
    
    cd "$PROJECT_ROOT"
    
    # Check node_modules size
    local node_modules_size=$(get_dir_size "node_modules")
    info "Current node_modules size: ${node_modules_size}MB"
    
    # Clean npm cache
    info "Cleaning npm cache..."
    npm cache clean --force
    success "Cleaned npm cache"
    
    # Check for unused dependencies
    if command_exists npm-check-updates; then
        info "Checking for outdated packages..."
        ncu
    else
        info "Installing npm-check-updates..."
        npm install -g npm-check-updates
        ncu
    fi
    
    # Audit and fix security issues
    info "Running npm audit..."
    if npm audit fix; then
        success "Fixed security vulnerabilities"
    else
        warning "Some vulnerabilities could not be fixed automatically"
    fi
    
    # Optimize package-lock.json
    if [[ -f "package-lock.json" ]]; then
        local lock_size=$(get_file_size "package-lock.json")
        info "package-lock.json size: ${lock_size}MB"
        
        # Regenerate package-lock.json
        info "Regenerating package-lock.json..."
        rm package-lock.json
        npm install
        success "Regenerated package-lock.json"
    fi
    
    # Check for duplicate dependencies
    if command_exists npm-dedupe; then
        info "Deduplicating dependencies..."
        npm dedupe
        success "Deduplicated dependencies"
    fi
    
    # Final size check
    local final_size=$(get_dir_size "node_modules")
    local saved_size=$((node_modules_size - final_size))
    info "Final node_modules size: ${final_size}MB"
    if [[ $saved_size -gt 0 ]]; then
        success "Saved ${saved_size}MB in node_modules"
    fi
    echo ""
}

# Optimize Git repository
optimize_git() {
    header "Optimizing Git Repository"
    
    if ! git rev-parse --git-dir &> /dev/null; then
        warning "Not in a Git repository. Skipping Git optimization."
        return
    fi
    
    # Get repository size before optimization
    local repo_size_before=$(du -sm .git | cut -f1)
    info "Current .git size: ${repo_size_before}MB"
    
    # Clean up unreachable objects
    info "Cleaning up unreachable Git objects..."
    git gc --prune=now
    success "Cleaned up unreachable objects"
    
    # Pack loose objects
    info "Packing loose objects..."
    git repack -ad
    success "Packed loose objects"
    
    # Clean reflog
    info "Cleaning reflog..."
    git reflog expire --expire=now --all
    success "Cleaned reflog"
    
    # Final garbage collection
    info "Running final garbage collection..."
    git gc --aggressive --prune=now
    success "Completed garbage collection"
    
    # Get repository size after optimization
    local repo_size_after=$(du -sm .git | cut -f1)
    local saved_size=$((repo_size_before - repo_size_after))
    info "Final .git size: ${repo_size_after}MB"
    if [[ $saved_size -gt 0 ]]; then
        success "Saved ${saved_size}MB in .git directory"
    fi
    echo ""
}

# Optimize file system
optimize_filesystem() {
    header "Optimizing File System"
    
    # Find large files
    info "Finding large files (>10MB)..."
    find "$PROJECT_ROOT" -type f -size +10M -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/dist/*" -not -path "*/build/*" | while read file; do
        local size=$(du -mh "$file" | cut -f1)
        echo "  $size $file"
    done
    
    # Find empty directories
    info "Finding empty directories..."
    find "$PROJECT_ROOT" -type d -empty -not -path "*/node_modules/*" -not -path "*/.git/*" | head -10
    
    # Clean up log files
    info "Cleaning up log files..."
    find "$PROJECT_ROOT" -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true
    success "Cleaned old log files"
    
    # Clean up temporary files
    info "Cleaning up temporary files..."
    find "$PROJECT_ROOT" -name "*.tmp" -type f -delete 2>/dev/null || true
    find "$PROJECT_ROOT" -name "*.temp" -type f -delete 2>/dev/null || true
    find "$PROJECT_ROOT" -name ".DS_Store" -type f -delete 2>/dev/null || true
    success "Cleaned temporary files"
    
    # Optimize .gitignore
    if [[ -f "$PROJECT_ROOT/.gitignore" ]]; then
        info "Checking .gitignore optimization..."
        
        local common_patterns=(
            "*.log"
            "*.tmp"
            "*.temp"
            ".DS_Store"
            "Thumbs.db"
            "*.swp"
            "*.swo"
            "*~"
            ".env.local"
            ".env.development.local"
            ".env.test.local"
            ".env.production.local"
        )
        
        local added_patterns=0
        for pattern in "${common_patterns[@]}"; do
            if ! grep -q "^$pattern$" "$PROJECT_ROOT/.gitignore"; then
                echo "$pattern" >> "$PROJECT_ROOT/.gitignore"
                ((added_patterns++))
            fi
        done
        
        if [[ $added_patterns -gt 0 ]]; then
            success "Added $added_patterns patterns to .gitignore"
        else
            success ".gitignore already optimized"
        fi
    fi
    echo ""
}

# Optimize environment variables
optimize_environment() {
    header "Optimizing Environment Configuration"
    
    if [[ ! -f "$ENV_FILE" ]]; then
        warning ".env file not found. Skipping environment optimization."
        return
    fi
    
    # Check for duplicate variables
    info "Checking for duplicate environment variables..."
    local duplicates=$(sort "$ENV_FILE" | uniq -d || true)
    if [[ -n "$duplicates" ]]; then
        warning "Found duplicate variables:"
        echo "$duplicates"
    else
        success "No duplicate environment variables found"
    fi
    
    # Check for unused variables
    info "Checking for potentially unused variables..."
    local env_vars=$(grep -v "^#" "$ENV_FILE" | grep "=" | cut -d'=' -f1)
    
    for var in $env_vars; do
        if ! grep -r "\$$var" "$PROJECT_ROOT/src" "$PROJECT_ROOT/lib" "$PROJECT_ROOT/config" 2>/dev/null | grep -v ".env" | head -1 | grep -q .; then
            warning "Variable $var may be unused"
        fi
    done
    
    # Optimize .env file format
    info "Optimizing .env file format..."
    
    # Create backup
    cp "$ENV_FILE" "$ENV_FILE.backup"
    
    # Sort and clean .env file
    {
        echo "# Optimized environment configuration"
        echo "# Generated on $(date)"
        echo ""
        
        # Add comments for sections
        echo "# Core Application Settings"
        grep -E "^(NODE_ENV|PORT|DEBUG)" "$ENV_FILE" | sort
        
        echo ""
        echo "# Database Configuration"
        grep -E "^(DATABASE_URL|REDIS_URL|MONGODB_URI|NEO4J_URI)" "$ENV_FILE" | sort
        
        echo ""
        echo "# External Services"
        grep -E "^(STRIPE_SECRET_KEY|PINECONE_API_KEY|JWT_SECRET)" "$ENV_FILE" | sort
        
        echo ""
        echo "# Platform Configuration"
        grep -E "^(GCP_PROJECT_ID|RAILWAY_TOKEN|AWS_REGION)" "$ENV_FILE" | sort
        
        echo ""
        echo "# Feature Flags"
        grep -E "^(FEATURE_|ENABLE_)" "$ENV_FILE" | sort || true
        
        echo ""
        echo "# Custom Variables"
        grep -v -E "^(NODE_ENV|PORT|DEBUG|DATABASE_URL|REDIS_URL|MONGODB_URI|NEO4J_URI|STRIPE_SECRET_KEY|PINECONE_API_KEY|JWT_SECRET|GCP_PROJECT_ID|RAILWAY_TOKEN|AWS_REGION|FEATURE_|ENABLE_)" "$ENV_FILE" | grep "=" | sort
    } > "$ENV_FILE.tmp"
    
    mv "$ENV_FILE.tmp" "$ENV_FILE"
    success "Optimized .env file format"
    echo ""
}

# Optimize build process
optimize_build() {
    header "Optimizing Build Process"
    
    if [[ ! -f "$PROJECT_ROOT/package.json" ]]; then
        warning "No package.json found. Skipping build optimization."
        return
    fi
    
    cd "$PROJECT_ROOT"
    
    # Check build scripts
    info "Analyzing build scripts..."
    local build_scripts=$(jq -r '.scripts | keys[] | select(test("build"))' package.json 2>/dev/null || echo "")
    
    if [[ -n "$build_scripts" ]]; then
        echo "Found build scripts:"
        echo "$build_scripts"
        
        # Optimize build cache
        if [[ -d "node_modules/.cache" ]]; then
            local cache_size=$(get_dir_size "node_modules/.cache")
            info "Build cache size: ${cache_size}MB"
            
            read -p "Clear build cache? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf node_modules/.cache
                success "Cleared build cache"
            fi
        fi
        
        # Check for build optimization opportunities
        if command_exists npm; then
            info "Checking for build optimization opportunities..."
            
            # Check if terser is available for minification
            if ! jq -e '.devDependencies.terser' package.json &>/dev/null; then
                info "Consider adding terser for better minification"
            fi
            
            # Check if webpack-bundle-analyzer is available
            if ! jq -e '.devDependencies."webpack-bundle-analyzer"' package.json &>/dev/null; then
                info "Consider adding webpack-bundle-analyzer for bundle analysis"
            fi
        fi
    else
        warning "No build scripts found in package.json"
    fi
    
    # Clean build artifacts
    info "Cleaning old build artifacts..."
    
    for build_dir in "dist" "build" ".next" ".nuxt" "out"; do
        if [[ -d "$build_dir" ]]; then
            local size=$(get_dir_size "$build_dir")
            info "Found $build_dir directory (${size}MB)"
            
            read -p "Remove $build_dir? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf "$build_dir"
                success "Removed $build_dir directory"
            fi
        fi
    done
    echo ""
}

# Generate optimization report
generate_report() {
    header "Optimization Report"
    
    echo ""
    echo -e "${CYAN}📊 Optimization Summary${NC}"
    echo ""
    
    # Project statistics
    local project_size=$(get_dir_size "$PROJECT_ROOT")
    local node_modules_size=$(get_dir_size "$PROJECT_ROOT/node_modules")
    local git_size=$(get_dir_size "$PROJECT_ROOT/.git")
    local dist_size=$(get_dir_size "$PROJECT_ROOT/dist")
    local build_size=$(get_dir_size "$PROJECT_ROOT/build")
    
    echo -e "${BLUE}Project Statistics:${NC}"
    echo "  Total size: ${project_size}MB"
    echo "  node_modules: ${node_modules_size}MB"
    echo "  .git: ${git_size}MB"
    echo "  dist: ${dist_size}MB"
    echo "  build: ${build_size}MB"
    echo ""
    
    # Recommendations
    echo -e "${BLUE}Recommendations:${NC}"
    
    if [[ $node_modules_size -gt 500 ]]; then
        echo "  ⚠️  Large node_modules directory. Consider using npm ci or pruning unused packages."
    fi
    
    if [[ $git_size -gt 100 ]]; then
        echo "  ⚠️  Large .git directory. Consider running git gc more frequently."
    fi
    
    if [[ $dist_size -gt 100 ]]; then
        echo "  ⚠️  Large dist directory. Consider cleaning old builds."
    fi
    
    if [[ $build_size -gt 100 ]]; then
        echo "  ⚠️  Large build directory. Consider cleaning old builds."
    fi
    
    # Performance tips
    echo ""
    echo -e "${BLUE}Performance Tips:${NC}"
    echo "  • Use npm ci instead of npm install for CI/CD"
    echo "  • Enable npm cache for faster installs"
    echo "  • Use .dockerignore to reduce build context"
    echo "  • Implement bundle splitting for better caching"
    echo "  • Use CDN for static assets in production"
    echo "  • Enable compression for API responses"
    echo "  • Implement database connection pooling"
    echo "  • Use Redis for session storage"
    echo ""
    
    # Next steps
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  • Review and commit .gitignore changes"
    echo "  • Update CI/CD pipeline with optimizations"
    echo "  • Monitor performance metrics in production"
    echo "  • Set up automated cleanup scripts"
    echo "  • Consider using a package manager like pnpm or yarn"
    echo ""
    
    success "Optimization complete!"
}

# Main function
main() {
    echo -e "${PURPLE}"
    echo "⚡ Performance Optimization"
    echo "==========================="
    echo -e "${NC}"
    
    optimize_docker
    optimize_nodejs
    optimize_git
    optimize_filesystem
    optimize_environment
    optimize_build
    generate_report
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --docker, -d   Optimize Docker only"
        echo "  --nodejs, -n   Optimize Node.js only"
        echo "  --git, -g      Optimize Git only"
        echo "  --fs, -f       Optimize file system only"
        echo "  --env, -e      Optimize environment only"
        echo "  --build, -b    Optimize build process only"
        echo ""
        exit 0
        ;;
    --docker|-d)
        optimize_docker
        ;;
    --nodejs|-n)
        optimize_nodejs
        ;;
    --git|-g)
        optimize_git
        ;;
    --fs|-f)
        optimize_filesystem
        ;;
    --env|-e)
        optimize_environment
        ;;
    --build|-b)
        optimize_build
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
