#!/usr/bin/env bash

# Shared utilities library for tools scripts
# Source this file at the top of any script that needs these utilities

# Prevent double-sourcing
[[ -n "${_TOOLS_LIB_COMMON_LOADED:-}" ]] && return 0
_TOOLS_LIB_COMMON_LOADED=1

# Colors for output
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export PURPLE='\033[0;35m'
export CYAN='\033[0;36m'
export WHITE='\033[1;37m'
export GRAY='\033[0;37m'
export NC='\033[0m' # No Color

# Unicode symbols for visual representation
# Using simple variables instead of associative array for better compatibility
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
SYMBOL_ALERT="🚨"
SYMBOL_CHART="📈"
SYMBOL_HEART="💚"

# Standard logging functions
info() { echo -e "${BLUE}${SYMBOL_INFO} $*${NC}"; }
success() { echo -e "${GREEN}${SYMBOL_CHECK} $*${NC}"; }
warning() { echo -e "${YELLOW}${SYMBOL_WARNING} $*${NC}"; }
error() { echo -e "${RED}${SYMBOL_CROSS} $*${NC}"; }
critical() { echo -e "${PURPLE}${SYMBOL_ALERT} CRITICAL: $*${NC}"; }
debug() { [[ "${DEBUG:-false}" == "true" ]] && echo -e "${CYAN}🔍 DEBUG: $*${NC}"; }

# Header and section functions
print_header() { echo -e "${PURPLE}${SYMBOL_ROCKET} $1${NC}"; }
print_section() { echo -e "${CYAN}${SYMBOL_GEAR} $1${NC}"; }

# Draw separator line
draw_separator() {
    echo -e "${GRAY}─────────────────────────────────────────────────────────────────${NC}"
}

# Timestamp functions
timestamp() { date -u +"%Y-%m-%d %H:%M:%S UTC"; }
timestamp_short() { date +"%H:%M:%S"; }
timestamp_file() { date +"%Y%m%d_%H%M%S"; }

# Check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Get version of a command
get_version() {
    local cmd=$1
    if command_exists "$cmd"; then
        case $cmd in
            "node") node --version ;;
            "npm") npm --version ;;
            "git") git --version | cut -d' ' -f3 ;;
            "docker") docker --version | cut -d' ' -f3 | cut -d',' -f1 ;;
            "docker-compose") docker-compose --version | cut -d' ' -f3 | cut -d',' -f1 ;;
            "gh") gh --version | cut -d' ' -f3 ;;
            "gcloud") gcloud version 2>/dev/null | grep 'Google Cloud SDK' | cut -d' ' -f4 ;;
            "railway") railway version 2>/dev/null | cut -d' ' -f3 ;;
            "pulumi") pulumi version 2>/dev/null ;;
            *) echo "unknown" ;;
        esac
    else
        echo "not installed"
    fi
}

# Get file size in MB
get_file_size() {
    local file=$1
    if [[ -f "$file" ]]; then
        du -m "$file" | cut -f1
    else
        echo "0"
    fi
}

# Get directory size in MB
get_dir_size() {
    local dir=$1
    if [[ -d "$dir" ]]; then
        du -sm "$dir" 2>/dev/null | cut -f1
    else
        echo "0"
    fi
}

# Log to file with timestamp
log_to_file() {
    local log_file="$1"
    local message="$2"
    echo "$(timestamp) - $message" >> "$log_file"
}

# Ensure directory exists
ensure_dir() {
    local dir="$1"
    [[ -d "$dir" ]] || mkdir -p "$dir"
}

# Load environment variables from file
load_env_file() {
    local env_file="${1:-.env}"
    if [[ -f "$env_file" ]]; then
        set -a
        # shellcheck source=/dev/null
        source "$env_file"
        set +a
        debug "Loaded environment variables from $env_file"
        return 0
    else
        warning "No .env file found at $env_file"
        return 1
    fi
}

# Check for missing dependencies
check_required_deps() {
    local missing_deps=()
    for dep in "$@"; do
        if ! command_exists "$dep"; then
            missing_deps+=("$dep")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        error "Missing required dependencies: ${missing_deps[*]}"
        info "Install with: brew install ${missing_deps[*]}"
        return 1
    fi
    return 0
}

# Print metric with status coloring
print_metric() {
    local label=$1
    local value=$2
    local status=${3:-"normal"}
    
    case $status in
        "good") echo -e "  ${GREEN}${SYMBOL_CHECK}${NC} $label: ${GREEN}$value${NC}" ;;
        "warning") echo -e "  ${YELLOW}${SYMBOL_WARNING}${NC} $label: ${YELLOW}$value${NC}" ;;
        "critical") echo -e "  ${RED}${SYMBOL_CROSS}${NC} $label: ${RED}$value${NC}" ;;
        *) echo -e "  ${WHITE}$label:${NC} $value" ;;
    esac
}

# Test HTTP endpoint with timeout and retries
test_http_endpoint() {
    local url="$1"
    local service_name="$2"
    local timeout="${3:-10}"
    local retries="${4:-3}"
    local expected_status="${5:-200}"
    
    debug "Testing $service_name at $url"
    
    local attempt=1
    local status_code="000"
    
    while [[ $attempt -le $retries ]]; do
        status_code=$(curl -s -o /dev/null -w "%{http_code}" \
            --max-time "$timeout" \
            --retry 1 \
            "$url" 2>/dev/null || echo "000")
        
        debug "Attempt $attempt: HTTP $status_code for $service_name"
        
        if [[ "$status_code" == "$expected_status" ]]; then
            return 0
        elif [[ "$status_code" =~ ^[45][0-9][0-9]$ ]]; then
            return 1
        fi
        
        ((attempt++))
        sleep 2
    done
    
    return 1
}

# Resolve script and project directories
resolve_paths() {
    export SCRIPT_DIR
    export PROJECT_ROOT
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
}
