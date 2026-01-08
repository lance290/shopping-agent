#!/usr/bin/env bash

# Platform (Railway, GCP, AWS) utilities
# Source this file after common.sh

# Prevent double-sourcing
[[ -n "${_TOOLS_LIB_PLATFORM_LOADED:-}" ]] && return 0
_TOOLS_LIB_PLATFORM_LOADED=1

# Check Railway authentication
check_railway_auth() {
    if ! command_exists railway; then
        warning "Railway CLI not available"
        return 2
    fi
    
    if railway whoami >/dev/null 2>&1; then
        success "Railway authenticated"
        return 0
    else
        error "Not logged into Railway"
        info "Run: railway login"
        return 1
    fi
}

# Check GCP authentication
check_gcp_auth() {
    if ! command_exists gcloud; then
        warning "gcloud CLI not available"
        return 2
    fi
    
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q .; then
        success "GCP authenticated"
        return 0
    else
        error "Not logged into GCP"
        info "Run: gcloud auth login"
        return 1
    fi
}

# Get Railway service URLs
get_railway_service_urls() {
    if ! command_exists railway; then
        return 1
    fi
    
    local railway_status
    railway_status=$(railway status 2>&1 || echo "")
    
    if [[ -z "$railway_status" ]]; then
        return 1
    fi
    
    echo "$railway_status" | grep -oE 'https://[a-zA-Z0-9.-]+\.railway\.app' || echo ""
}

# Get GCP Cloud Run services
get_gcp_cloudrun_services() {
    if ! command_exists gcloud; then
        return 1
    fi
    
    gcloud run services list --format="value(name,status.url)" 2>/dev/null || echo ""
}

# Get GCP project ID
get_gcp_project_id() {
    if ! command_exists gcloud; then
        return 1
    fi
    
    gcloud config get-value project 2>/dev/null || echo ""
}

# Deploy to Railway
deploy_to_railway() {
    info "Deploying to Railway..."
    
    if ! check_railway_auth; then
        return 1
    fi
    
    # Check project linkage
    if ! railway status >/dev/null 2>&1; then
        info "Linking Railway project..."
        railway link || return 1
    fi
    
    # Deploy
    railway up || return 1
    
    success "Railway deployment initiated"
}

# Sync secrets to Railway
sync_secrets_to_railway() {
    local env_file="${1:-.env}"
    
    if ! check_railway_auth; then
        return 1
    fi
    
    local synced_count=0
    local failed_count=0
    
    while IFS= read -r line; do
        if [[ "$line" =~ ^[A-Z_][A-Z0-9_]*= ]]; then
            local var_name="${line%%=*}"
            local var_value="${line#*=}"
            
            [[ -z "$var_value" ]] && continue
            
            if railway variables set "$var_name=$var_value" 2>/dev/null; then
                ((synced_count++))
                success "Synced $var_name to Railway"
            else
                ((failed_count++))
                error "Failed to sync $var_name to Railway"
            fi
        fi
    done < "$env_file"
    
    info "Railway sync: $synced_count synced, $failed_count failed"
    [[ $failed_count -eq 0 ]]
}

# Sync secrets to GCP Secret Manager
sync_secrets_to_gcp() {
    local env_file="${1:-.env}"
    local project_id="${2:-$(get_gcp_project_id)}"
    
    if [[ -z "$project_id" ]]; then
        error "GCP_PROJECT_ID not set"
        return 1
    fi
    
    if ! check_gcp_auth; then
        return 1
    fi
    
    local synced_count=0
    local failed_count=0
    
    while IFS= read -r line; do
        if [[ "$line" =~ ^[A-Z_][A-Z0-9_]*= ]]; then
            local var_name="${line%%=*}"
            local var_value="${line#*=}"
            
            [[ -z "$var_value" ]] && continue
            
            if echo "$var_value" | gcloud secrets versions add "$var_name" \
                --project="$project_id" --data-file=- 2>/dev/null; then
                ((synced_count++))
                success "Synced $var_name to GCP"
            else
                # Try to create secret first
                if gcloud secrets create "$var_name" --project="$project_id" \
                    --replication-policy="automatic" 2>/dev/null; then
                    if echo "$var_value" | gcloud secrets versions add "$var_name" \
                        --project="$project_id" --data-file=- 2>/dev/null; then
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
    done < "$env_file"
    
    info "GCP sync: $synced_count synced, $failed_count failed"
    [[ $failed_count -eq 0 ]]
}
