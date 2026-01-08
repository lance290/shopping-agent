#!/usr/bin/env bash

# Cross-Platform Secrets Sync Script
# Synchronizes environment variables across local, GCP, Railway, and other platforms

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_BACKUP_DIR="$PROJECT_ROOT/.env-backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Sync targets
SYNC_TARGETS=()
DRY_RUN=false
FORCE_SYNC=false

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
    
    # Check for platform-specific dependencies
    if [[ " ${SYNC_TARGETS[*]} " =~ " gcp " ]] && ! command -v gcloud &> /dev/null; then
        missing_deps+=("gcloud")
    fi
    
    if [[ " ${SYNC_TARGETS[*]} " =~ " railway " ]] && ! command -v railway &> /dev/null; then
        missing_deps+=("railway")
    fi
    
    if [[ " ${SYNC_TARGETS[*]} " =~ " aws " ]] && ! command -v aws &> /dev/null; then
        missing_deps+=("aws")
    fi
    
    if [[ " ${SYNC_TARGETS[*]} " =~ " azure " ]] && ! command -v az &> /dev/null; then
        missing_deps+=("az")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        error "Missing required dependencies: ${missing_deps[*]}"
        info "Install commands:"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            info "  brew install ${missing_deps[*]}"
        else
            info "  sudo apt-get install ${missing_deps[*]}"
        fi
        info "  npm install -g @railway/cli  # for railway"
        exit 1
    fi
}

# Create backup
create_backup() {
    local timestamp
    timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="$ENV_BACKUP_DIR/.env.$timestamp"
    
    mkdir -p "$ENV_BACKUP_DIR"
    
    if [[ -f "$ENV_FILE" ]]; then
        cp "$ENV_FILE" "$backup_file"
        success "Created backup: $backup_file"
    fi
}

# Load environment variables from file
load_env_vars() {
    local env_vars=()
    
    if [[ ! -f "$ENV_FILE" ]]; then
        error "Environment file not found: $ENV_FILE"
        return 1
    fi
    
    # Read all non-comment, non-empty lines
    while IFS= read -r line; do
        if [[ "$line" =~ ^[A-Z_][a-zA-Z0-0_]*= ]]; then
            local var_name="${line%% o}"
            local var_value="${line#*=}"
            
            # Skip empty values
            if [[ -n "$var_value" ]]; then
                env_vars+=("$var_name=$var_value")
            fi
        fi
    done < "$ENV_FILE"
    
    printf '%s\n' "${env_vars[@]}"
}

# Sync to GCP Secret Manager
sync_to_gcp() {
    info "Syncing secrets to GCP Secret Manager..."
    
    local project_id
    project_id=$(grep "^GCP_PROJECT_ID=" "$ENV_FILE" | cut -d'=' -f2 || echo "")
    
    if [[ -z "$project_id" ]]; then
        error "GCP_PROJECT_ID not set in environment file"
        return 1
    fi
    
    if $DRY_RUN; then
        info "DRY RUN: Would sync to GCP project: $project_id"
        return 0
    fi
    
    local synced_count=0
    local failed_count=0
    
    while IFS= read -r env_var; do
        if [[ -n "$env_var" ]]; then
            local var_name="${env_var%% o}"
            local var_value="${env_var#*=}"
            
            # Skip if value is empty
            if [[ -z "$var_value" ]]; then
                continue
            fi
            
            # Try to update existing secret
            if echo "$var_value" | gcloud secrets versions add "$var_name" \
                --project="$project_id" \
                --data-file=- 2>/dev/null; then
                ((synced_count++))
                success "Synced $var_name to GCP"
            else
                # Try to create secret if it doesn't exist
                if gcloud secrets create "$var_name" \
                    --project="$project_id" \
                    --replication-policy="automatic" 2>/dev/null; then
                    if echo "$var_value" | gcloud secrets versions add "$var_name" \
                        --project="$project_id" \
                        --data-file=- 2>/dev/null; then
                        ((synced_count++))
                        success "Created and synced $var_name to GCP"
                    else
                        ((failed_count++))
                        error "Failed to sync $var_name to GCP"
                    fi
                else
                    ((failed_count++))
                    error "Failed to create secret $var_name in GCP"
                fi
            fi
        fi
    done < <(load_env_vars)
    
    info "GCP sync complete: $synced_count synced, $failed_count failed"
    
    if [[ $failed_count -gt 0 ]]; then
        return 1
    fi
}

# Sync from GCP Secret Manager
sync_from_gcp() {
    info "Syncing secrets from GCP Secret Manager..."
    
    local project_id
    project_id=$(grep "^GCP_PROJECT_ID=" "$ENV_FILE" | cut -d'=' -f2 || echo "")
    
    if [[ -z "$project_id" ]]; then
        error "GCP_PROJECT_ID not set in environment file"
        return 1
    fi
    
    if $DRY_RUN; then
        info "DRY RUN: Would sync from GCP project: $project_id"
        return 0
    fi
    
    # Get list of secrets
    local secrets
    secrets=$(gcloud secrets list --project="$project_id" --format="value(name)" 2>/dev/null || echo "")
    
    if [[ -z "$secrets" ]]; then
        warning "No secrets found in GCP project: $project_id"
        return 0
    fi
    
    local synced_count=0
    local failed_count=0
    
    for secret_name in $secrets; do
        # Get latest secret value
        local secret_value
        secret_value=$(gcloud secrets versions access "latest" \
            --secret="$secret_name" \
            --project="$project_id" 2>/dev/null || echo "")
        
        if [[ -n "$secret_value" ]]; then
            # Update or add to .env file
            if grep -q "^${secret_name}=" "$ENV_FILE"; then
                # Update existing
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s|^${secret_name}=.*|${secret_name}=${secret_value}|" "$ENV_FILE"
                else
                    sed -i "s|^${secret_name}=.*|${secret_name}=${secret_value}|" "$ENV_FILE"
                fi
            else
                # Add new
                echo "${secret_name}=${secret_value}" >> "$ENV_FILE"
            fi
            ((synced_count++))
            success "Synced $secret_name from GCP"
        else
            ((failed_count++))
            error "Failed to retrieve $secret_name from GCP"
        fi
    done
    
    info "GCP sync complete: $synced_count synced, $failed_count failed"
    
    if [[ $failed_count -gt 0 ]]; then
        return 1
    fi
}

# Sync to Railway
sync_to_railway() {
    info "Syncing secrets to Railway..."
    
    if $DRY_RUN; then
        info "DRY RUN: Would sync to Railway environment"
        return 0
    fi
    
    local synced_count=0
    local failed_count=0
    
    while IFS= read -r env_var; do
        if [[ -n "$env_var" ]]; then
            if railway variables set "$env_var" 2>/dev/null; then
                ((synced_count++))
                local var_name="${env_var%% o}"
                success "Synced $var_name to Railway"
            else
                ((failed_count++))
                local var_name="${env_var%% o}"
                error "Failed to sync $var_name to Railway"
            fi
        fi
    done < <(load_env_vars)
    
    info "Railway sync complete: $synced_count synced, $failed_count failed"
    
    if [[ $failed_count -gt 0 ]]; then
        return 1
    fi
}

# Sync from Railway
sync_from_railway() {
    info "Syncing secrets from Railway..."
    
    if $DRY_RUN; then
        info "DRY RUN: Would sync from Railway environment"
        return 0
    fi
    
    # Get current Railway variables
    local railway_vars
    railway_vars=$(railway variables 2>/dev/null || echo "")
    
    if [[ -z "$railway_vars" ]]; then
        warning "No variables found in Railway environment"
        return 0
    fi
    
    local synced_count=0
    local failed_count=0
    
    # Parse Railway variables and update .env
    while IFS= read -r line; do
        if [[ "$line" =~ ^[A-Z_][a-zA-Z0-0_]*= ]]; then
            local var_name="${line%% o}"
            local var_value="${line#*=}"
            
            # Update or add to .env file
            if grep -q "^${var_name}=" "$ENV_FILE"; then
                # Update existing
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s|^${var_name}=.*|${var_name}=${var_value}|" "$ENV_FILE"
                else
                    sed -i "s|^${var_name}=.*|${var_name}=${var_value}|" "$ENV_FILE"
                fi
            else
                # Add new
                echo "${var_name}=${var_value}" >> "$ENV_FILE"
            fi
            ((synced_count++))
            success "Synced $var_name from Railway"
        fi
    done <<< "$railway_vars"
    
    info "Railway sync complete: $synced_count synced"
}

# Sync to AWS Secrets Manager
sync_to_aws() {
    info "Syncing secrets to AWS Secrets Manager..."
    
    local aws_region
    aws_region=$(grep "^AWS_REGION=" "$ENV_FILE" | cut -d'=' -f2 || echo "us-west-2")
    
    if $DRY_RUN; then
        info "DRY RUN: Would sync to AWS Secrets Manager (region: $aws_region)"
        return 0
    fi
    
    local synced_count=0
    local failed_count=0
    
    while IFS= read -r env_var; do
        if [[ -n "$env_var" ]]; then
            local var_name="${env_var%% o}"
            local var_value="${env_var#*=}"
            
            # Create or update secret
            if aws secretsmanager describe-secret \
                --secret-id="$var_name" \
                --region="$aws_region" &>/dev/null; then
                # Update existing
                aws secretsmanager put-secret-value \
                    --secret-id="$var_name" \
                    --secret-string="$var_value" \
                    --region="$aws_region" 2>/dev/null && ((synced_count++))
            else
                # Create new
                aws secretsmanager create-secret \
                    --name="$var_name" \
                    --secret-string="$var_value" \
                    --region="$aws_region" 2>/dev/null && ((synced_count++))
            fi
            
            if [[ $? -eq 0 ]]; then
                success "Synced $var_name to AWS"
            else
                ((failed_count++))
                error "Failed to sync $var_name to AWS"
            fi
        fi
    done < <(load_env_vars)
    
    info "AWS sync complete: $synced_count synced, $failed_count failed"
    
    if [[ $failed_count -gt 0 ]]; then
        return 1
    fi
}

# Sync from AWS Secrets Manager
sync_from_aws() {
    info "Syncing secrets from AWS Secrets Manager..."
    
    local aws_region
    aws_region=$(grep "^AWS_REGION=" "$ENV_FILE" | cut -d'=' -f2 || echo "us-west-2")
    
    if $DRY_RUN; then
        info "DRY RUN: Would sync from AWS Secrets Manager (region: $aws_region)"
        return 0
    fi
    
    # Get list of secrets
    local secrets
    secrets=$(aws secretsmanager list-secrets \
        --region="$aws_region" \
        --query "SecretList[].Name" \
        --output text 2>/dev/null || echo "")
    
    if [[ -z "$secrets" ]]; then
        warning "No secrets found in AWS Secrets Manager"
        return 0
    fi
    
    local synced_count=0
    local failed_count=0
    
    for secret_name in $secrets; do
        # Get secret value
        local secret_value
        secret_value=$(aws secretsmanager get-secret-value \
            --secret-id="$secret_name" \
            --region="$aws_region" \
            --query "SecretString" \
            --output text 2>/dev/null || echo "")
        
        if [[ -n "$secret_value" ]]; then
            # Update or add to .env file
            if grep -q "^${secret_name}=" "$ENV_FILE"; then
                # Update existing
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s|^${secret_name}=.*|${secret_name}=${secret_value}|" "$ENV_FILE"
                else
                    sed -i "s|^${secret_name}=.*|${secret_name}=${secret_value}|" "$ENV_FILE"
                fi
            else
                # Add new
                echo "${secret_name}=${secret_value}" >> "$ENV_FILE"
            fi
            ((synced_count++))
            success "Synced $secret_name from AWS"
        else
            ((failed_count++))
            error "Failed to retrieve $secret_name from AWS"
        fi
    done
    
    info "AWS sync complete: $synced_count synced, $failed_count failed"
    
    if [[ $failed_count -gt 0 ]]; then
        return 1
    fi
}

# Show sync status
show_status() {
    info "Secrets Sync Status:"
    echo "==================="
    
    if [[ -f "$ENV_FILE" ]]; then
        local var_count
        var_count=$(grep -c "^[A-Z_][a-zA-Z0 o_]*=" "$ENV_FILE" || echo "0")
        echo "Local environment file: $ENV_FILE"
        echo "Variables: $var_count"
        
        # Check platform availability
        echo ""
        echo "Platform Status:"
        
        if command -v gcloud &> /dev/null; then
            local project_id
            project_id=$(grep "^GCP_PROJECT_ID=" "$ENV_FILE" | cut -d'=' -f2 || echo "not set")
            if [[ "$project_id" != "not set" ]]; then
                echo "  ✅ GCP Secret Manager (project: $project_id)"
            else
                echo "  ❌ GCP Secret Manager (project not configured)"
            fi
        else
            echo "  ❌ GCP Secret Manager (gcloud CLI not installed)"
        fi
        
        if command -v railway &> /dev/null; then
            echo "  ✅ Railway (CLI available)"
        else
            echo "  ❌ Railway (CLI not installed)"
        fi
        
        if command -v aws &> /dev/null; then
            local aws_region
            aws_region=$(grep "^AWS_REGION=" "$ENV_FILE" | cut -d'=' -f2 || echo "not set")
            if [[ "$aws_region" != "not set" ]]; then
                echo "  ✅ AWS Secrets Manager (region: $aws_region)"
            else
                echo "  ❌ AWS Secrets Manager (region not configured)"
            fi
        else
            echo "  ❌ AWS Secrets Manager (AWS CLI not installed)"
        fi
    else
        echo "Local environment file: Not found"
        echo "Run 'tools/setup-env.sh init' to create environment file"
    fi
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 <command> [targets] [options]

Commands:
  push [targets]    Push secrets to specified targets
  pull [targets]    Pull secrets from specified targets
  status            Show sync status
  help              Show this help message

Targets:
  gcp               Google Cloud Secret Manager
  railway           Railway environment variables
  aws               AWS Secrets Manager
  all               All available targets (default)

Options:
  --dry-run         Show what would be synced without doing it
  --force           Skip confirmation prompts
  --backup          Create backup before syncing

Examples:
  $0 push gcp                    # Push to GCP Secret Manager
  $0 pull railway                 # Pull from Railway
  $0 push all --backup            # Push to all targets with backup
  $0 status                       # Show sync status
  $0 push gcp railway --dry-run   # Preview sync to GCP and Railway

EOF
}

# Parse command line arguments
COMMAND="${1:-help}"
shift

# Parse targets
while [[ $# -gt 0 && ! "$1" =~ ^-- ]]; do
    case "$1" in
        gcp|railway|aws|all)
            SYNC_TARGETS+=("$1")
            ;;
        *)
            error "Unknown target: $1"
            show_usage
            exit 1
            ;;
    esac
    shift
done

# Default to all targets if none specified
if [ ${#SYNC_TARGETS[@]} -eq 0 ]; then
    SYNC_TARGETS=("all")
fi

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE_SYNC=true
            shift
            ;;
        --backup)
            create_backup
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

case "$COMMAND" in
    "push")
        info "Pushing secrets to targets: ${SYNC_TARGETS[*]}"
        
        if ! $FORCE_SYNC && ! $DRY_RUN; then
            echo ""
            read -p "This will overwrite secrets on remote platforms. Continue? [y/N] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                info "Aborted"
                exit 0
            fi
        fi
        
        local exit_code=0
        
        for target in "${SYNC_TARGETS[@]}"; do
            case "$target" in
                "gcp")
                    sync_to_gcp || exit_code=1
                    ;;
                "railway")
                    sync_to_railway || exit_code=1
                    ;;
                "aws")
                    sync_to_aws || exit_code=1
                    ;;
                "all")
                    sync_to_gcp || true
                    sync_to_railway || true
                    sync_to_aws || true
                    ;;
            esac
        done
        
        if [[ $exit_code -eq 0 ]]; then
            success "All secrets synced successfully! 🚀"
        else
            error "Some secrets failed to sync"
            exit 1
        fi
        ;;
    "pull")
        info "Pulling secrets from targets: ${SYNC_TARGETS[*]}"
        
        local exit_code=0
        
        for target in "${SYNC_TARGETS[@]}"; do
            case "$target" in
                "gcp")
                    sync_from_gcp || exit_code=1
                    ;;
                "railway")
                    sync_from_railway || exit_code=1
                    ;;
                "aws")
                    sync_from_aws || exit_code=1
                    ;;
                "all")
                    sync_from_gcp || true
                    sync_from_railway || true
                    sync_from_aws || true
                    ;;
            esac
        done
        
        if [[ $exit_code -eq 0 ]]; then
            success "All secrets pulled successfully! 🚀"
        else
            error "Some secrets failed to pull"
            exit 1
        fi
        ;;
    "status")
        show_status
        ;;
    "help"|"--help"|"-h")
        show_usage
        ;;
    *)
        error "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac
