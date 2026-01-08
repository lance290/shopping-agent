#!/usr/bin/env bash

# Secrets Validation Script
# Validates environment variables against security requirements and best practices

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_SCHEMA="$PROJECT_ROOT/.env.schema.json"
ENV_FILE="$PROJECT_ROOT/.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Validation results
VALIDATION_ERRORS=()
VALIDATION_WARNINGS=()
VALIDATION_SUCCESS=()

# Logging functions
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; VALIDATION_SUCCESS+=("$1"); }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; VALIDATION_WARNINGS+=("$1"); }
error() { echo -e "${RED}❌ $1${NC}"; VALIDATION_ERRORS+=("$1"); }

# Check dependencies
check_dependencies() {
    if ! command -v jq &> /dev/null; then
        error "jq is required for JSON parsing"
        exit 1
    fi
    
    if [[ ! -f "$ENV_SCHEMA" ]]; then
        error "Environment schema not found: $ENV_SCHEMA"
        exit 1
    fi
}

# Load environment variable
get_env_var() {
    local var_name="$1"
    grep "^${var_name}=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | tr -d '"' || echo ""
}

# Validate string length
validate_length() {
    local value="$1"
    local min_length="$2"
    local max_length="${3:-}"
    
    local length=${#value}
    
    if [[ $length -lt $min_length ]]; then
        return 1
    fi
    
    if [[ -n "$max_length" && $length -gt $max_length ]]; then
        return 1
    fi
    
    return 0
}

# Validate secret strength
validate_secret_strength() {
    local secret="$1"
    local var_name="$2"
    local min_length="${3:-32}"
    
    # Check length
    if ! validate_length "$secret" "$min_length"; then
        error "$var_name: Secret too short (minimum $min_length characters)"
        return 1
    fi
    
    # Check for common weak patterns
    if [[ "$secret" =~ ^(password|secret|key|test|demo|development|changeme)$ ]]; then
        error "$var_name: Secret contains common weak pattern"
        return 1
    fi
    
    # Check for dictionary words (basic check)
    local common_words=("password" "secret" "admin" "user" "test" "demo" "default" "123456" "qwerty")
    for word in "${common_words[@]}"; do
        if [[ "${secret,,}" == *"$word"* ]]; then
            warning "$var_name: Secret contains common word '$word'"
        fi
    done
    
    # Check entropy (basic)
    local unique_chars
    unique_chars=$(echo "$secret" | fold -w1 | sort -u | wc -l)
    local total_chars
    total_chars=${#secret}
    local entropy_ratio
    entropy_ratio=$((unique_chars * 100 / total_chars))
    
    if [[ $entropy_ratio -lt 50 ]]; then
        warning "$var_name: Low entropy ($entropy_ratio% unique characters)"
    fi
    
    # Check character variety
    local has_upper=false
    local has_lower=false
    local has_digit=false
    local has_special=false
    
    if [[ "$secret" =~ [A-Z] ]]; then has_upper=true; fi
    if [[ "$secret" =~ [a-z] ]]; then has_lower=true; fi
    if [[ "$secret" =~ [0-9] ]]; then has_digit=true; fi
    if [[ "$secret" =~ [^a-zA-Z0-9] ]]; then has_special=true; fi
    
    local variety_score=0
    $has_upper && ((variety_score++))
    $has_lower && ((variety_score++))
    $has_digit && ((variety_score++))
    $has_special && ((variety_score++))
    
    if [[ $variety_score -lt 3 ]]; then
        warning "$var_name: Low character variety (missing uppercase, lowercase, digits, or special chars)"
    fi
    
    success "$var_name: Secret strength validation passed"
    return 0
}

# Validate URL format
validate_url() {
    local url="$1"
    local var_name="$2"
    local expected_scheme="${3:-}"
    
    # Basic URL validation
    if [[ ! "$url" =~ ^[a-zA-Z][a-zA-Z0-9+.-]*:// ]]; then
        error "$var_name: Invalid URL format"
        return 1
    fi
    
    # Check scheme if specified
    if [[ -n "$expected_scheme" && ! "$url" =~ ^${expected_scheme}:// ]]; then
        error "$var_name: URL must use $expected_scheme scheme"
        return 1
    fi
    
    # Check for localhost in production
    local node_env
    node_env=$(get_env_var "NODE_ENV")
    
    if [[ "$node_env" == "production" && "$url" =~ localhost|127\.0\.0\.1 ]]; then
        error "$var_name: localhost URLs not allowed in production"
        return 1
    fi
    
    success "$var_name: URL format validation passed"
    return 0
}

# Validate email format
validate_email() {
    local email="$1"
    local var_name="$2"
    
    if [[ ! "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        error "$var_name: Invalid email format"
        return 1
    fi
    
    # Check for disposable email domains (basic)
    local disposable_domains=("10minutemail.com" "tempmail.org" "guerrillamail.com")
    local domain
    domain=$(echo "$email" | cut -d'@' -f2)
    
    for disposable in "${disposable_domains[@]}"; do
        if [[ "$domain" == *"$disposable"* ]]; then
            warning "$var_name: Using disposable email domain"
        fi
    done
    
    success "$var_name: Email format validation passed"
    return 0
}

# Validate API key format
validate_api_key() {
    local api_key="$1"
    local var_name="$2"
    local expected_pattern="${3:-}"
    
    # Check minimum length
    if ! validate_length "$api_key" 16; then
        error "$var_name: API key too short (minimum 16 characters)"
        return 1
    fi
    
    # Check pattern if specified
    if [[ -n "$expected_pattern" && ! "$api_key" =~ $expected_pattern ]]; then
        error "$var_name: API key format doesn't match expected pattern"
        return 1
    fi
    
    # Check for common test keys
    local test_keys=("test" "demo" "example" "sample" "fake" "mock")
    for test_key in "${test_keys[@]}"; do
        if [[ "${api_key,,}" == *"$test_key"* ]]; then
            error "$var_name: API key contains test pattern"
            return 1
        fi
    done
    
    success "$var_name: API key format validation passed"
    return 0
}

# Validate database connection string
validate_database_url() {
    local db_url="$1"
    local var_name="$2"
    local db_type="$3"
    
    case "$db_type" in
        "postgresql")
            if [[ ! "$db_url" =~ ^postgres(ql)?://.*:[0-9]+/.*$ ]]; then
                error "$var_name: Invalid PostgreSQL connection string format"
                return 1
            fi
            ;;
        "mongodb")
            if [[ ! "$db_url" =~ ^mongodb://[^:]+:[^@]+@[^:]+:[0-9]+/[^/]+$ ]]; then
                error "$var_name: Invalid MongoDB connection string format"
                return 1
            fi
            ;;
        "redis")
            if [[ ! "$db_url" =~ ^redis://[^:]+:[0-9]+$ ]]; then
                error "$var_name: Invalid Redis connection string format"
                return 1
            fi
            ;;
        "neo4j")
            if [[ ! "$db_url" =~ ^(bolt|bolt\+s)://[^:]+:[0-9]+$ ]]; then
                error "$var_name: Invalid Neo4j connection string format"
                return 1
            fi
            ;;
    esac
    
    # Check for default passwords
    if [[ "$db_url" =~ :password@|:admin@|:root@|:postgres@ ]]; then
        error "$var_name: Database URL contains default password"
        return 1
    fi
    
    # Check for localhost in production
    local node_env
    node_env=$(get_env_var "NODE_ENV")
    
    if [[ "$node_env" == "production" && "$db_url" =~ localhost|127\.0\.0\.1 ]]; then
        error "$var_name: localhost database URLs not allowed in production"
        return 1
    fi
    
    success "$var_name: Database URL validation passed"
    return 0
}

# Validate feature flags consistency
validate_feature_flags() {
    info "Validating feature flags consistency..."
    
    local features
    features=$(jq -r '.featureFlags | keys[]' "$ENV_SCHEMA" 2>/dev/null || echo "")
    
    for feature in $features; do
        local feature_value
        feature_value=$(get_env_var "$feature")
        
        if [[ "$feature_value" == "true" ]]; then
            # Check conditional requirements
            local conditional_key="${feature}=true"
            local conditional_required
            conditional_required=$(jq -r ".conditionalRequired[\"$conditional_key\"][]?" "$ENV_SCHEMA" 2>/dev/null || echo "")
            
            for var in $conditional_required; do
                local var_value
                var_value=$(get_env_var "$var")
                
                if [[ -z "$var_value" ]]; then
                    error "$feature enabled but $var is not set"
                fi
            done
        fi
    done
    
    success "Feature flags consistency validated"
}

# Validate security best practices
validate_security_practices() {
    info "Validating security best practices..."
    
    local node_env
    node_env=$(get_env_var "NODE_ENV")
    
    # Check for development settings in production
    if [[ "$node_env" == "production" ]]; then
        local log_level
        log_level=$(get_env_var "LOG_LEVEL")
        
        if [[ "$log_level" == "debug" ]]; then
            warning "LOG_LEVEL=debug not recommended for production"
        fi
        
        # Check for development URLs
        local frontend_url
        frontend_url=$(get_env_var "FRONTEND_URL")
        if [[ "$frontend_url" =~ localhost|127\.0\.0\.1 ]]; then
            error "FRONTEND_URL points to localhost in production"
        fi
        
        local backend_url
        backend_url=$(get_env_var "BACKEND_URL")
        if [[ "$backend_url" =~ localhost|127\.0\.0\.1 ]]; then
            error "BACKEND_URL points to localhost in production"
        fi
    fi
    
    # Check CORS configuration
    local cors_origins
    cors_origins=$(get_env_var "CORS_ORIGINS")
    
    if [[ "$node_env" == "production" && "$cors_origins" =~ localhost|127\.0\.0\.1 ]]; then
        warning "CORS_ORIGINS includes localhost in production"
    fi
    
    # Check rate limiting
    local rate_limit_max
    rate_limit_max=$(get_env_var "RATE_LIMIT_MAX")
    
    if [[ -n "$rate_limit_max" && $rate_limit_max -gt 1000 ]]; then
        warning "RATE_LIMIT_MAX is very high ($rate_limit_max)"
    fi
    
    success "Security practices validation completed"
}

# Main validation function
run_validation() {
    info "Starting environment variables validation..."
    
    if [[ ! -f "$ENV_FILE" ]]; then
        error "Environment file not found: $ENV_FILE"
        info "Run 'tools/setup-env.sh init' to create environment file"
        exit 1
    fi
    
    # Validate required variables
    local required_vars
    required_vars=$(jq -r '.required[]' "$ENV_SCHEMA" 2>/dev/null || echo "")
    
    for var in $required_vars; do
        local var_value
        var_value=$(get_env_var "$var")
        
        if [[ -z "$var_value" ]]; then
            error "Required variable $var is not set"
            continue
        fi
        
        # Get variable configuration
        local var_config
        var_config=$(jq -r ".properties[\"$var\"]" "$ENV_SCHEMA")
        
        # Validate based on type and format
        case "$var" in
            "DATABASE_URL")
                validate_database_url "$var_value" "$var" "postgresql"
                ;;
            "REDIS_URL")
                validate_database_url "$var_value" "$var" "redis"
                ;;
            "MONGODB_URI")
                validate_database_url "$var_value" "$var" "mongodb"
                ;;
            "NEO4J_URI")
                validate_database_url "$var_value" "$var" "neo4j"
                ;;
            "JWT_SECRET"|"SESSION_SECRET"|"API_SECRET"|"ENCRYPTION_KEY"|"WEBHOOK_SECRET")
                validate_secret_strength "$var_value" "$var"
                ;;
            *"EMAIL"*)
                validate_email "$var_value" "$var"
                ;;
            *"URL"*)
                validate_url "$var_value" "$var"
                ;;
            *"API_KEY"*)
                local pattern
                pattern=$(echo "$var_config" | jq -r '.pattern // empty')
                validate_api_key "$var_value" "$var" "$pattern"
                ;;
        esac
    done
    
    # Validate conditional variables
    local conditional_features
    conditional_features=$(jq -r '.featureFlags | keys[]' "$ENV_SCHEMA" 2>/dev/null || echo "")
    
    for feature in $conditional_features; do
        local feature_value
        feature_value=$(get_env_var "$feature")
        
        if [[ "$feature_value" == "true" ]]; then
            local conditional_key="${feature}=true"
            local conditional_required
            conditional_required=$(jq -r ".conditionalRequired[\"$conditional_key\"][]?" "$ENV_SCHEMA" 2>/dev/null || echo "")
            
            for var in $conditional_required; do
                local var_value
                var_value=$(get_env_var "$var")
                
                if [[ -z "$var_value" ]]; then
                    error "Conditional variable $var is not set (required for $feature)"
                    continue
                fi
                
                # Validate conditional variables
                case "$var" in
                    *"API_KEY"*)
                        validate_api_key "$var_value" "$var"
                        ;;
                    *"URL"*)
                        validate_url "$var_value" "$var"
                        ;;
                    *"SECRET"*)
                        validate_secret_strength "$var_value" "$var"
                        ;;
                esac
            done
        fi
    done
    
    # Run additional validations
    validate_feature_flags
    validate_security_practices
    
    # Generate report
    echo ""
    info "Validation Report:"
    echo "=================="
    
    if [ ${#VALIDATION_SUCCESS[@]} -gt 0 ]; then
        echo ""
        success "Passed validations (${#VALIDATION_SUCCESS[@]}):"
        for msg in "${VALIDATION_SUCCESS[@]}"; do
            echo "  ✅ $msg"
        done
    fi
    
    if [ ${#VALIDATION_WARNINGS[@]} -gt 0 ]; then
        echo ""
        warning "Warnings (${#VALIDATION_WARNINGS[@]}):"
        for msg in "${VALIDATION_WARNINGS[@]}"; do
            echo "  ⚠️  $msg"
        done
    fi
    
    if [ ${#VALIDATION_ERRORS[@]} -gt 0 ]; then
        echo ""
        error "Errors (${#VALIDATION_ERRORS[@]}):"
        for msg in "${VALIDATION_ERRORS[@]}"; do
            echo "  ❌ $msg"
        done
        echo ""
        error "Validation failed with ${#VALIDATION_ERRORS[@]} error(s)"
        exit 1
    else
        echo ""
        success "All validations passed! 🎉"
        echo ""
        info "Your environment configuration is secure and ready for deployment."
    fi
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [options]

Options:
  --fix-secrets    Generate new secrets for failed validations
  --quiet          Suppress detailed output
  --help, -h       Show this help message

Examples:
  $0                    # Run full validation
  $0 --fix-secrets      # Fix secret validation issues
  $0 --quiet            # Run validation with minimal output

EOF
}

# Parse command line arguments
FIX_SECRETS=false
QUIET=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --fix-secrets)
            FIX_SECRETS=true
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
check_dependencies

if $QUIET; then
    # Redirect output to /dev/null for quiet mode
    run_validation >/dev/null 2>&1
else
    run_validation
fi

# Fix secrets if requested and there were validation errors
if $FIX_SECRETS && [ ${#VALIDATION_ERRORS[@]} -gt 0 ]; then
    info "Attempting to fix validation errors..."
    
    # Regenerate secrets that failed validation
    "$SCRIPT_DIR/setup-env.sh" generate
    
    # Run validation again
    info "Re-running validation after fixes..."
    run_validation
fi
