#!/usr/bin/env bash

# Health check utilities
# Source this file after common.sh and database.sh

# Prevent double-sourcing
[[ -n "${_TOOLS_LIB_HEALTH_LOADED:-}" ]] && return 0
_TOOLS_LIB_HEALTH_LOADED=1

# Health status tracking arrays
declare -ga HEALTHY_SERVICES=()
declare -ga WARNING_SERVICES=()
declare -ga FAILED_SERVICES=()

# Reset health status
reset_health_status() {
    HEALTHY_SERVICES=()
    WARNING_SERVICES=()
    FAILED_SERVICES=()
}

# Record health status
record_healthy() { HEALTHY_SERVICES+=("$*"); success "$*"; }
record_warning() { WARNING_SERVICES+=("$*"); warning "$*"; }
record_failed() { FAILED_SERVICES+=("$*"); error "$*"; }

# Test Railway services
test_railway_services() {
    info "Checking Railway services..."
    
    if ! command_exists railway; then
        record_warning "Railway CLI not available"
        return 1
    fi
    
    if ! railway whoami >/dev/null 2>&1; then
        record_failed "Not logged into Railway"
        return 1
    fi
    
    record_healthy "Railway authenticated"
    
    local railway_status
    railway_status=$(railway status 2>&1 || echo "")
    
    if [[ -z "$railway_status" ]]; then
        record_warning "Could not fetch Railway status"
        return 1
    fi
    
    local service_urls
    service_urls=$(echo "$railway_status" | grep -oE 'https://[a-zA-Z0-9.-]+\.railway\.app' || echo "")
    
    if [[ -z "$service_urls" ]]; then
        record_warning "No Railway service URLs found"
        return 1
    fi
    
    echo "$service_urls" | while read -r url; do
        if [[ -n "$url" ]]; then
            if test_http_endpoint "$url" "Railway Service" 10 3 200; then
                record_healthy "Railway: $url accessible"
            else
                record_warning "Railway: $url not accessible"
            fi
        fi
    done
}

# Test GCP services
test_gcp_services() {
    info "Checking GCP services..."
    
    if ! command_exists gcloud; then
        record_warning "gcloud CLI not available"
        return 1
    fi
    
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" >/dev/null 2>&1; then
        record_failed "Not logged into GCP"
        return 1
    fi
    
    record_healthy "GCP authenticated"
    
    local services
    services=$(gcloud run services list --format="value(name,status.url)" 2>/dev/null || echo "")
    
    if [[ -z "$services" ]]; then
        record_warning "No Cloud Run services found"
        return 1
    fi
    
    echo "$services" | while read -r name url; do
        if [[ -n "$name" && -n "$url" ]]; then
            if test_http_endpoint "$url" "GCP $name" 10 3 200; then
                record_healthy "GCP: $name accessible"
            else
                record_warning "GCP: $name not accessible"
            fi
        fi
    done
}

# Test local services
test_local_services() {
    info "Checking local services..."
    
    local endpoints=(
        "http://localhost:3000:Frontend"
        "http://localhost:8080:Backend"
        "http://localhost:4000:API"
    )
    
    for endpoint in "${endpoints[@]}"; do
        local url="${endpoint%%:*}:${endpoint#*:}"
        url="${url%:*}"
        local name="${endpoint##*:}"
        
        if test_http_endpoint "$url" "$name" 5 2 200; then
            record_healthy "Local $name: accessible"
        fi
    done
}

# Test external services
test_external_services() {
    info "Checking external services..."
    
    # Stripe
    if [[ -n "${STRIPE_SECRET_KEY:-}" ]]; then
        local http_code
        http_code=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "Authorization: Bearer $STRIPE_SECRET_KEY" \
            "https://api.stripe.com/v1/account" 2>/dev/null || echo "000")
        
        if [[ "$http_code" == "200" ]]; then
            record_healthy "Stripe: API key valid"
        else
            record_failed "Stripe: API key invalid (HTTP $http_code)"
        fi
    else
        record_warning "STRIPE_SECRET_KEY not configured"
    fi
    
    # Pinecone
    if [[ -n "${PINECONE_API_KEY:-}" ]]; then
        local pinecone_env="${PINECONE_ENVIRONMENT:-us-west1-gcp}"
        local http_code
        http_code=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "Api-Key: $PINECONE_API_KEY" \
            "https://controller.$pinecone_env.pinecone.io/databases" 2>/dev/null || echo "000")
        
        if [[ "$http_code" == "200" ]]; then
            record_healthy "Pinecone: API key valid"
        else
            record_failed "Pinecone: API key invalid (HTTP $http_code)"
        fi
    else
        record_warning "PINECONE_API_KEY not configured"
    fi
}

# Check system resources
check_system_resources() {
    info "Checking system resources..."
    
    # Disk space
    local disk_usage
    disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [[ $disk_usage -lt 80 ]]; then
        record_healthy "Disk usage: ${disk_usage}%"
    elif [[ $disk_usage -lt 90 ]]; then
        record_warning "Disk usage: ${disk_usage}% (getting high)"
    else
        record_failed "Disk usage: ${disk_usage}% (critical)"
    fi
    
    # CPU load
    if command_exists uptime; then
        local load_avg
        load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
        local load_int
        load_int=$(echo "$load_avg" | cut -d. -f1)
        
        if [[ $load_int -lt 4 ]]; then
            record_healthy "CPU load: $load_avg"
        else
            record_warning "CPU load: $load_avg (high)"
        fi
    fi
}

# Generate health report
generate_health_report() {
    local timestamp_report
    timestamp_report=$(timestamp)
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 Health Check Report - $timestamp_report"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    local total_services=$((${#HEALTHY_SERVICES[@]} + ${#WARNING_SERVICES[@]} + ${#FAILED_SERVICES[@]}))
    
    echo "📈 Summary:"
    echo "  Total: $total_services"
    echo "  ✅ Healthy: ${#HEALTHY_SERVICES[@]}"
    echo "  ⚠️  Warnings: ${#WARNING_SERVICES[@]}"
    echo "  ❌ Failed: ${#FAILED_SERVICES[@]}"
    echo ""
    
    if [[ ${#FAILED_SERVICES[@]} -eq 0 ]]; then
        if [[ ${#WARNING_SERVICES[@]} -eq 0 ]]; then
            success "🎉 All systems operational!"
        else
            warning "⚠️  Systems operational with ${#WARNING_SERVICES[@]} warning(s)"
        fi
    else
        error "🚨 ${#FAILED_SERVICES[@]} service(s) failing!"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Save health report to file
save_health_report() {
    local report_dir="${1:-$PROJECT_ROOT/.health-reports}"
    mkdir -p "$report_dir"
    
    local report_file="$report_dir/health-check-$(timestamp_file).json"
    
    cat > "$report_file" <<EOF
{
  "timestamp": "$(timestamp)",
  "summary": {
    "total": $((${#HEALTHY_SERVICES[@]} + ${#WARNING_SERVICES[@]} + ${#FAILED_SERVICES[@]})),
    "healthy": ${#HEALTHY_SERVICES[@]},
    "warnings": ${#WARNING_SERVICES[@]},
    "failed": ${#FAILED_SERVICES[@]}
  }
}
EOF
    
    info "Health report saved to: $report_file"
}
