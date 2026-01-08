#!/usr/bin/env bash

# Monorepo Environment Setup Script
# Automates environment variable setup, validation, and synchronization

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_SCHEMA="$PROJECT_ROOT/.env.schema.json"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }

# Check dependencies
check_dependencies() {
    local missing_deps=()
    
    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi
    
    if ! command -v openssl &> /dev/null; then
        missing_deps+=("openssl")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        error "Missing required dependencies: ${missing_deps[*]}"
        info "Install with:"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            info "  brew install ${missing_deps[*]}"
        else
            info "  sudo apt-get install ${missing_deps[*]}"
        fi
        exit 1
    fi
}

# Load and validate schema
load_schema() {
    if [[ ! -f "$ENV_SCHEMA" ]]; then
        error "Environment schema not found: $ENV_SCHEMA"
        exit 1
    fi
    
    if ! jq empty "$ENV_SCHEMA" 2>/dev/null; then
        error "Invalid JSON in environment schema: $ENV_SCHEMA"
        exit 1
    fi
    
    info "Loaded environment schema from $ENV_SCHEMA"
}

# Generate secure secret
generate_secret() {
    local length="${1:-32}"
    local type="${2:-base64}"
    
    case "$type" in
        "hex")
            openssl rand -hex "$length"
            ;;
        "base64")
            openssl rand -base64 "$length"
            ;;
        "alphanumeric")
            openssl rand -base64 "$length" | tr -d "=+/" | cut -c1-"$length"
            ;;
        *)
            openssl rand -base64 "$length"
            ;;
    esac
}

# Check if feature is enabled
is_feature_enabled() {
    local feature="$1"
    local value
    
    if [[ -f "$ENV_FILE" ]]; then
        value=$(grep "^${feature}=" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' || echo "false")
    else
        value="false"
    fi
    
    [[ "$value" == "true" ]]
}

# Validate required environment variables
validate_required() {
    local missing_vars=()
    local required_vars
    
    required_vars=$(jq -r '.required[]' "$ENV_SCHEMA" 2>/dev/null || echo "")
    
    for var in $required_vars; do
        if ! grep -q "^${var}=" "$ENV_FILE" 2>/dev/null; then
            missing_vars+=("$var")
        fi
    done
    
    # Check conditional requirements
    local conditional_features
    conditional_features=$(jq -r '.featureFlags | keys[]' "$ENV_SCHEMA" 2>/dev/null || echo "")
    
    for feature in $conditional_features; do
        if is_feature_enabled "$feature"; then
            local conditional_key="${feature}=true"
            local conditional_required
            
            conditional_required=$(jq -r ".conditionalRequired[\"$conditional_key\"][]?" "$ENV_SCHEMA" 2>/dev/null || echo "")
            
            for var in $conditional_required; do
                if ! grep -q "^${var}=" "$ENV_FILE" 2>/dev/null; then
                    missing_vars+=("$var (required for $feature)")
                fi
            done
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            error "  - $var"
        done
        return 1
    fi
    
    success "All required environment variables are present"
}

# Generate missing secrets
generate_missing_secrets() {
    local generated_any=false
    
    info "Checking for missing secrets that can be generated..."
    
    # Get all variables with generator property
    local generatable_vars
    generatable_vars=$(jq -r '.properties | to_entries[] | select(.value.generator) | .key' "$ENV_SCHEMA" 2>/dev/null || echo "")
    
    for var in $generatable_vars; do
        if ! grep -q "^${var}=" "$ENV_FILE" 2>/dev/null; then
            local var_config
            var_config=$(jq -r ".properties[\"$var\"]" "$ENV_SCHEMA")
            
            local generator_type
            generator_type=$(echo "$var_config" | jq -r '.generator // "openssl"')
            
            local generated_value
            local command
            
            command=$(echo "$var_config" | jq -r '.generated // empty')
            if [[ -n "$command" ]]; then
                generated_value=$(eval "$command")
            else
                generated_value=$(generate_secret 32 base64)
            fi
            
            echo "${var}=${generated_value}" >> "$ENV_FILE"
            success "Generated $var"
            generated_any=true
        fi
    done
    
    if $generated_any; then
        info "Generated secrets written to $ENV_FILE"
    else
        info "No missing secrets to generate"
    fi
}

# Set default values
set_defaults() {
    local defaults_set=false
    
    info "Setting default values for optional variables..."
    
    # Get all variables with default property
    local default_vars
    default_vars=$(jq -r '.properties | to_entries[] | select(.value.default) | .key' "$ENV_SCHEMA" 2>/dev/null || echo "")
    
    for var in $default_vars; do
        if ! grep -q "^${var}=" "$ENV_FILE" 2>/dev/null; then
            local default_value
            default_value=$(jq -r ".properties[\"$var\"].default" "$ENV_SCHEMA")
            
            echo "${var}=${default_value}" >> "$ENV_FILE"
            success "Set default for $var: $default_value"
            defaults_set=true
        fi
    done
    
    if $defaults_set; then
        info "Default values written to $ENV_FILE"
    else
        info "All optional variables already set"
    fi
}

# Create example environment file
create_example() {
    info "Creating example environment file..."
    
    cat > "$ENV_EXAMPLE" << 'EOF'
# Monorepo Environment Variables
# Copy this file to .env and fill in your values

# Core Application Settings
NODE_ENV=development
PORT=8080
LOG_LEVEL=info

# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/myapp
REDIS_URL=redis://localhost:6379

# Security (Auto-generated by setup script)
JWT_SECRET=
SESSION_SECRET=
API_SECRET=
ENCRYPTION_KEY=

# Feature Flags
mongodb=false
neo4j=false
pinecone=false
email=false
aws=false
gcp=false
sentry=false
analytics=false
stripe=false
github=false
google=false

# Optional Services (uncomment and configure as needed)
# MONGODB_URI=mongodb://localhost:27017/myapp
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=password
# PINECONE_API_KEY=your-pinecone-api-key
# PINECONE_ENVIRONMENT=us-west1-gcp
EOF
    
    success "Created example environment file: $ENV_EXAMPLE"
}

# Validate environment file format
validate_format() {
    info "Validating environment file format..."
    
    if [[ ! -f "$ENV_FILE" ]]; then
        error "Environment file not found: $ENV_FILE"
        info "Run '$0 init' to create a new environment file"
        return 1
    fi
    
    # Check for invalid lines
    local invalid_lines
    invalid_lines=$(grep -v "^#" "$ENV_FILE" | grep -v "^$" | grep -v "^[A-Z_][A-Z0-9_]*=" || true)
    
    if [[ -n "$invalid_lines" ]]; then
        error "Invalid environment variable format:"
        echo "$invalid_lines" | while read -r line; do
            error "  $line"
        done
        error "Expected format: VARIABLE_NAME=value"
        return 1
    fi
    
    success "Environment file format is valid"
}

# Test database connections
test_connections() {
    info "Testing database connections..."
    
    local db_url
    db_url=$(grep "^DATABASE_URL=" "$ENV_FILE" | cut -d'=' -f2- || echo "")
    
    if [[ -n "$db_url" ]]; then
        if command -v psql &> /dev/null; then
            if PGPASSWORD="${db_url#*://*:*@}" psql "$db_url" -c "SELECT 1;" &>/dev/null; then
                success "PostgreSQL connection successful"
            else
                warning "PostgreSQL connection failed (database may not be running)"
            fi
        else
            warning "psql not available - skipping PostgreSQL connection test"
        fi
    fi
    
    local redis_url
    redis_url=$(grep "^REDIS_URL=" "$ENV_FILE" | cut -d'=' -f2- || echo "")
    
    if [[ -n "$redis_url" ]]; then
        if command -v redis-cli &> /dev/null; then
            if redis-cli -u "$redis_url" ping &>/dev/null; then
                success "Redis connection successful"
            else
                warning "Redis connection failed (Redis may not be running)"
            fi
        else
            warning "redis-cli not available - skipping Redis connection test"
        fi
    fi
}

# Sync to GCP Secret Manager
sync_gcp() {
    info "Syncing secrets to GCP Secret Manager..."
    
    if ! command -v gcloud &> /dev/null; then
        error "gcloud CLI not found. Install with: curl https://sdk.cloud.google.com | bash"
        return 1
    fi
    
    local project_id
    project_id=$(grep "^GCP_PROJECT_ID=" "$ENV_FILE" | cut -d'=' -f2 || echo "")
    
    if [[ -z "$project_id" ]]; then
        error "GCP_PROJECT_ID not set in environment file"
        return 1
    fi
    
    # Read all non-comment, non-empty lines from .env
    while IFS= read -r line; do
        if [[ "$line" =~ ^[A-Z_][A-Z0-9_]*= ]]; then
            local var_name="${line%%=*}"
            local var_value="${line#*=}"
            
            # Skip if value is empty
            if [[ -z "$var_value" ]]; then
                continue
            fi
            
            echo "$var_value" | gcloud secrets versions add "$var_name" \
                --project="$project_id" \
                --data-file=- \
                2>/dev/null || {
                # Create secret if it doesn't exist
                gcloud secrets create "$var_name" \
                    --project="$project_id" \
                    --replication-policy="automatic" && \
                echo "$var_value" | gcloud secrets versions add "$var_name" \
                    --project="$project_id" \
                    --data-file=-
            }
            
            success "Synced $var_name to GCP Secret Manager"
        fi
    done < "$ENV_FILE"
    
    success "All secrets synced to GCP Secret Manager"
}

# Sync to Railway
sync_railway() {
    info "Syncing secrets to Railway..."
    
    if ! command -v railway &> /dev/null; then
        error "Railway CLI not found. Install with: npm install -g @railway/cli"
        return 1
    fi
    
    # Read all non-comment, non-empty lines from .env
    while IFS= read -r line; do
        if [[ "$line" =~ ^[A-Z_][A-Z0-9_]*= ]]; then
            local var_name="${line%%=*}"
            local var_value="${line#*=}"
            
            # Skip if value is empty
            if [[ -z "$var_value" ]]; then
                continue
            fi
            
            railway variables set "$var_name=$var_value" 2>/dev/null || true
            success "Synced $var_name to Railway"
        fi
    done < "$ENV_FILE"
    
    success "All secrets synced to Railway"
}

# Show environment status
show_status() {
    info "Environment Status:"
    echo "=================="
    
    if [[ -f "$ENV_FILE" ]]; then
        local var_count
        var_count=$(grep -c "^[A-Z_][A-Z0-9_]*=" "$ENV_FILE" || echo "0")
        echo "Environment file: $ENV_FILE"
        echo "Variables set: $var_count"
        
        echo ""
        echo "Enabled features:"
        local features
        features=$(jq -r '.featureFlags | keys[]' "$ENV_SCHEMA" 2>/dev/null || echo "")
        
        for feature in $features; do
            if is_feature_enabled "$feature"; then
                echo "  ✅ $feature"
            else
                echo "  ❌ $feature"
            fi
        done
    else
        echo "Environment file: Not found"
        echo "Run '$0 init' to create environment file"
    fi
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 <command> [options]

Commands:
  init                    Initialize new environment file
  validate                Validate existing environment file
  generate                Generate missing secrets and defaults
  test                    Test database connections
  sync-gcp                Sync secrets to GCP Secret Manager
  sync-railway            Sync secrets to Railway environment
  status                  Show environment status
  help                    Show this help message

Examples:
  $0 init                 # Create new .env file with defaults
  $0 validate             # Check current .env file
  $0 generate             # Generate missing secrets
  $0 sync-gcp              # Sync to GCP Secret Manager
  $0 sync-railway          # Sync to Railway

EOF
}

# Main function
main() {
    local command="${1:-help}"
    
    check_dependencies
    load_schema
    
    case "$command" in
        "init")
            info "Initializing new environment file..."
            if [[ -f "$ENV_FILE" ]]; then
                warning "Environment file already exists: $ENV_FILE"
                read -p "Overwrite? [y/N] " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    info "Aborted"
                    exit 0
                fi
            fi
            
            create_example
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            generate_missing_secrets
            set_defaults
            success "Environment file initialized: $ENV_FILE"
            info "Review and customize the values in $ENV_FILE"
            ;;
        "validate")
            validate_format
            validate_required
            success "Environment validation passed"
            ;;
        "generate")
            if [[ ! -f "$ENV_FILE" ]]; then
                error "Environment file not found. Run '$0 init' first"
                exit 1
            fi
            generate_missing_secrets
            set_defaults
            success "Environment generation complete"
            ;;
        "test")
            if [[ ! -f "$ENV_FILE" ]]; then
                error "Environment file not found. Run '$0 init' first"
                exit 1
            fi
            validate_format
            test_connections
            ;;
        "sync-gcp")
            if [[ ! -f "$ENV_FILE" ]]; then
                error "Environment file not found. Run '$0 init' first"
                exit 1
            fi
            validate_format
            sync_gcp
            ;;
        "sync-railway")
            if [[ ! -f "$ENV_FILE" ]]; then
                error "Environment file not found. Run '$0 init' first"
                exit 1
            fi
            validate_format
            sync_railway
            ;;
        "status")
            show_status
            ;;
        "help"|"--help"|"-h")
            show_usage
            ;;
        *)
            error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
