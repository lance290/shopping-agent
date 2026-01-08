#!/usr/bin/env bash

# Comprehensive Health Monitoring Script
# Real-time monitoring of all services, databases, and infrastructure components

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# Configuration
ENVIRONMENT="${1:-development}"
PLATFORM="${2:-all}"
CONTINUOUS="${3:-false}"
INTERVAL="${4:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Health status tracking
HEALTH_STATUS=()
FAILED_SERVICES=()
WARNING_SERVICES=()
HEALTHY_SERVICES=()

# Logging functions
info() { echo -e "${BLUE}ℹ️  $*${NC}"; }
success() { echo -e "${GREEN}✅ $*${NC}"; HEALTHY_SERVICES+=("$*"); }
warning() { echo -e "${YELLOW}⚠️  $*${NC}"; WARNING_SERVICES+=("$*"); }
error() { echo -e "${RED}❌ $*${NC}"; FAILED_SERVICES+=("$*"); }
critical() { echo -e "${PURPLE}🚨 CRITICAL: $*${NC}"; FAILED_SERVICES+=("CRITICAL: $*"); }
debug() { [[ "${DEBUG:-false}" == "true" ]] && echo -e "${CYAN}🔍 DEBUG: $*${NC}"; }

timestamp() { date -u +"%Y-%m-%d %H:%M:%S UTC"; }
timestamp_short() { date +"%H:%M:%S"; }

# Load environment variables
load_env_vars() {
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    source "$ENV_FILE"
    set +a
    debug "Loaded environment variables from $ENV_FILE"
  else
    warning "No .env file found at $ENV_FILE"
  fi
}

# Check dependencies
check_dependencies() {
  local missing_deps=()
  
  if ! command -v curl &> /dev/null; then
    missing_deps+=("curl")
  fi
  
  if ! command -v jq &> /dev/null; then
    missing_deps+=("jq")
  fi
  
  if [ ${#missing_deps[@]} -gt 0 ]; then
    error "Missing dependencies: ${missing_deps[*]}"
    info "Install with: brew install ${missing_deps[*]}"
    return 1
  fi
  
  return 0
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
  
  while [ $attempt -le $retries ]; do
    status_code=$(curl -s -o /dev/null -w "%{http_code}" \
      --max-time "$timeout" \
      --retry 1 \
      "$url" 2>/dev/null || echo "000")
    
    debug "Attempt $attempt: HTTP $status_code for $service_name"
    
    if [[ "$status_code" == "$expected_status" ]]; then
      success "$service_name: HTTP $status_code"
      return 0
    elif [[ "$status_code" =~ ^[45][0-9][0-9]$ ]]; then
      error "$service_name: HTTP $status_code (server error)"
      return 1
    fi
    
    ((attempt++))
    sleep 2
  done
  
  if [[ "$status_code" == "000" ]]; then
    error "$service_name: Connection timeout/failure"
  else
    warning "$service_name: HTTP $status_code (unexpected)"
  fi
  
  return 1
}

# Test database connection
test_database_connection() {
  local db_type="$1"
  local connection_string="$2"
  local service_name="$3"
  
  debug "Testing $db_type connection for $service_name"
  
  case "$db_type" in
    "postgresql")
      if command -v psql &> /dev/null; then
        if PGPASSWORD="${connection_string#*://*:*@}" psql "$connection_string" -c "SELECT 1;" >/dev/null 2>&1; then
          success "$service_name: PostgreSQL connection OK"
          return 0
        else
          error "$service_name: PostgreSQL connection failed"
          return 1
        fi
      else
        warning "$service_name: psql not available"
        return 2
      fi
      ;;
    "redis")
      if command -v redis-cli &> /dev/null; then
        if redis-cli -u "$connection_string" ping >/dev/null 2>&1; then
          success "$service_name: Redis connection OK"
          return 0
        else
          error "$service_name: Redis connection failed"
          return 1
        fi
      else
        warning "$service_name: redis-cli not available"
        return 2
      fi
      ;;
    "mongodb")
      if command -v mongosh &> /dev/null; then
        if mongosh "$connection_string" --eval "db.runCommand({ping: 1})" >/dev/null 2>&1; then
          success "$service_name: MongoDB connection OK"
          return 0
        else
          error "$service_name: MongoDB connection failed"
          return 1
        fi
      else
        warning "$service_name: mongosh not available"
        return 2
      fi
      ;;
    "neo4j")
      if command -v cypher-shell &> /dev/null; then
        if cypher-shell -a "$connection_string" -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD}" "RETURN 1;" >/dev/null 2>&1; then
          success "$service_name: Neo4j connection OK"
          return 0
        else
          error "$service_name: Neo4j connection failed"
          return 1
        fi
      else
        warning "$service_name: cypher-shell not available"
        return 2
      fi
      ;;
  esac
  
  return 1
}

# Test API service health
test_api_health() {
  local base_url="$1"
  local service_name="$2"
  
  # Test health endpoint
  test_http_endpoint "$base_url/health" "$service_name Health" 10 3 200
  
  # Test API endpoints
  local endpoints=("/api/status" "/api/version" "/api/health")
  
  for endpoint in "${endpoints[@]}"; do
    test_http_endpoint "$base_url$endpoint" "$service_name $endpoint" 5 2 "200|404"
  done
}

# Test frontend service
test_frontend_health() {
  local url="$1"
  local service_name="$2"
  
  # Test main page
  test_http_endpoint "$url" "$service_name Main" 10 3 200
  
  # Test static assets
  local assets=("/static/js/main.js" "/static/css/main.css" "/favicon.ico")
  
  for asset in "${assets[@]}"; do
    test_http_endpoint "$url$asset" "$service_name $asset" 5 2 "200|404"
  done
}

# Test Railway services
test_railway_services() {
  info "Checking Railway services..."
  
  if ! command -v railway &> /dev/null; then
    warning "Railway CLI not available"
    return 1
  fi
  
  if ! railway whoami >/dev/null 2>&1; then
    error "Not logged into Railway"
    return 1
  fi
  
  # Get service URLs
  local railway_status
  railway_status=$(railway status 2>&1 || echo "")
  
  if [[ -z "$railway_status" ]]; then
    error "Could not fetch Railway status"
    return 1
  fi
  
  # Extract service URLs
  local service_urls
  service_urls=$(echo "$railway_status" | grep -oE 'https://[a-zA-Z0-9.-]+\.railway\.app' || echo "")
  
  if [[ -z "$service_urls" ]]; then
    warning "No Railway service URLs found"
    return 1
  fi
  
  echo "$service_urls" | while read -r url; do
    if [[ -n "$url" ]]; then
      local service_name="Railway Service"
      
      # Determine service type by URL pattern
      if [[ "$url" =~ frontend ]]; then
        service_name="Railway Frontend"
        test_frontend_health "$url" "$service_name"
      elif [[ "$url" =~ backend|api ]]; then
        service_name="Railway Backend"
        test_api_health "$url" "$service_name"
      elif [[ "$url" =~ admin ]]; then
        service_name="Railway Admin"
        test_http_endpoint "$url" "$service_name" 10 3 "200|401|403"
      else
        test_http_endpoint "$url" "$service_name" 10 3 200
      fi
    fi
  done
}

# Test GCP services
test_gcp_services() {
  info "Checking GCP services..."
  
  if ! command -v gcloud &> /dev/null; then
    warning "gcloud CLI not available"
    return 1
  fi
  
  if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" >/dev/null 2>&1; then
    error "Not logged into GCP"
    return 1
  fi
  
  # Check Cloud Run services
  local services
  services=$(gcloud run services list --format="value(name,status.url)" 2>/dev/null || echo "")
  
  if [[ -z "$services" ]]; then
    warning "No Cloud Run services found"
    return 1
  fi
  
  echo "$services" | while read -r name url; do
    if [[ -n "$name" && -n "$url" ]]; then
      local service_name="GCP $name"
      
      if [[ "$name" =~ frontend ]]; then
        test_frontend_health "$url" "$service_name"
      elif [[ "$name" =~ backend|api ]]; then
        test_api_health "$url" "$service_name"
      elif [[ "$name" =~ admin ]]; then
        test_http_endpoint "$url" "$service_name" 10 3 "200|401|403"
      else
        test_http_endpoint "$url" "$service_name" 10 3 200
      fi
    fi
  done
  
  # Check Cloud SQL instances
  local sql_instances
  sql_instances=$(gcloud sql instances list --format="value(name,state)" 2>/dev/null || echo "")
  
  echo "$sql_instances" | while read -r name state; do
    if [[ -n "$name" && -n "$state" ]]; then
      if [[ "$state" == "RUNNABLE" ]]; then
        success "GCP SQL $name: $state"
      else
        error "GCP SQL $name: $state"
      fi
    fi
  done
}

# Test local services
test_local_services() {
  info "Checking local services..."
  
  # Test frontend
  if [[ -n "${FRONTEND_URL:-}" ]]; then
    test_frontend_health "$FRONTEND_URL" "Local Frontend"
  else
    test_http_endpoint "http://localhost:3000" "Local Frontend" 5 2 200
  fi
  
  # Test backend
  if [[ -n "${BACKEND_URL:-}" ]]; then
    test_api_health "$BACKEND_URL" "Local Backend"
  else
    test_api_health "http://localhost:8080" "Local Backend"
  fi
  
  # Test admin
  if [[ -n "${ADMIN_URL:-}" ]]; then
    test_http_endpoint "$ADMIN_URL" "Local Admin" 5 2 "200|401|403"
  else
    test_http_endpoint "http://localhost:3001" "Local Admin" 5 2 "200|401|403"
  fi
}

# Test databases
test_databases() {
  info "Checking databases..."
  
  # PostgreSQL
  if [[ -n "${DATABASE_URL:-}" ]]; then
    test_database_connection "postgresql" "$DATABASE_URL" "PostgreSQL"
  else
    warning "DATABASE_URL not configured"
  fi
  
  # Redis
  if [[ -n "${REDIS_URL:-}" ]]; then
    test_database_connection "redis" "$REDIS_URL" "Redis"
  else
    warning "REDIS_URL not configured"
  fi
  
  # MongoDB
  if [[ -n "${MONGODB_URI:-}" ]]; then
    test_database_connection "mongodb" "$MONGODB_URI" "MongoDB"
  else
    warning "MONGODB_URI not configured"
  fi
  
  # Neo4j
  if [[ -n "${NEO4J_URI:-}" ]]; then
    test_database_connection "neo4j" "$NEO4J_URI" "Neo4j"
  else
    warning "NEO4J_URI not configured"
  fi
}

# Test external services
test_external_services() {
  info "Checking external services..."
  
  # Pinecone
  if [[ -n "${PINECONE_API_KEY:-}" ]]; then
    local pinecone_env="${PINECONE_ENVIRONMENT:-us-west1-gcp}"
    local pinecone_url="https://controller.$pinecone_env.pinecone.io/databases"
    
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
      -H "Api-Key: $PINECONE_API_KEY" \
      "$pinecone_url" 2>/dev/null || echo "000")
    
    if [[ "$http_code" == "200" ]]; then
      success "Pinecone: API key valid"
    else
      error "Pinecone: API key invalid (HTTP $http_code)"
    fi
  else
    warning "PINECONE_API_KEY not configured"
  fi
  
  # Stripe
  if [[ -n "${STRIPE_SECRET_KEY:-}" ]]; then
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
      -H "Authorization: Bearer $STRIPE_SECRET_KEY" \
      "https://api.stripe.com/v1/account" 2>/dev/null || echo "000")
    
    if [[ "$http_code" == "200" ]]; then
      success "Stripe: API key valid"
    else
      error "Stripe: API key invalid (HTTP $http_code)"
    fi
  else
    warning "STRIPE_SECRET_KEY not configured"
  fi
}

# Check system resources
check_system_resources() {
  info "Checking system resources..."
  
  # Disk space
  local disk_usage
  disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
  
  if [[ $disk_usage -lt 80 ]]; then
    success "Disk usage: ${disk_usage}%"
  elif [[ $disk_usage -lt 90 ]]; then
    warning "Disk usage: ${disk_usage}% (getting high)"
  else
    critical "Disk usage: ${disk_usage}% (critical)"
  fi
  
  # Memory usage
  if command -v free &> /dev/null; then
    local mem_usage
    mem_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    
    if [[ $mem_usage -lt 80 ]]; then
      success "Memory usage: ${mem_usage}%"
    elif [[ $mem_usage -lt 90 ]]; then
      warning "Memory usage: ${mem_usage}% (getting high)"
    else
      critical "Memory usage: ${mem_usage}% (critical)"
    fi
  fi
  
  # CPU load
  if command -v uptime &> /dev/null; then
    local load_avg
    load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    
    # Convert to integer for comparison
    local load_int
    load_int=$(echo "$load_avg" | cut -d. -f1)
    
    if [[ $load_int -lt 2 ]]; then
      success "CPU load: $load_avg"
    elif [[ $load_int -lt 4 ]]; then
      warning "CPU load: $load_avg (moderate)"
    else
      warning "CPU load: $load_avg (high)"
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
  
  # Summary
  local total_services=$((${#HEALTHY_SERVICES[@]} + ${#WARNING_SERVICES[@]} + ${#FAILED_SERVICES[@]}))
  local healthy_count=${#HEALTHY_SERVICES[@]}
  local warning_count=${#WARNING_SERVICES[@]}
  local failed_count=${#FAILED_SERVICES[@]}
  
  echo "📈 Summary:"
  echo "  Total Services: $total_services"
  echo "  ✅ Healthy: $healthy_count"
  echo "  ⚠️  Warnings: $warning_count"
  echo "  ❌ Failed: $failed_count"
  echo ""
  
  # Overall status
  if [[ $failed_count -eq 0 ]]; then
    if [[ $warning_count -eq 0 ]]; then
      success "🎉 All systems operational!"
    else
      warning "⚠️  Systems operational with $warning_count warning(s)"
    fi
  else
    error "🚨 $failed_count service(s) failing - attention required!"
  fi
  
  echo ""
  
  # Detailed results
  if [ ${#HEALTHY_SERVICES[@]} -gt 0 ]; then
    echo "✅ Healthy Services:"
    for service in "${HEALTHY_SERVICES[@]}"; do
      echo "  • $service"
    done
    echo ""
  fi
  
  if [ ${#WARNING_SERVICES[@]} -gt 0 ]; then
    echo "⚠️  Warning Services:"
    for service in "${WARNING_SERVICES[@]}"; do
      echo "  • $service"
    done
    echo ""
  fi
  
  if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
    echo "❌ Failed Services:"
    for service in "${FAILED_SERVICES[@]}"; do
      echo "  • $service"
    done
    echo ""
  fi
  
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Save health report to file
save_health_report() {
  local report_dir="$PROJECT_ROOT/.health-reports"
  mkdir -p "$report_dir"
  
  local report_file="$report_dir/health-check-$(date +"%Y%m%d_%H%M%S").json"
  
  cat > "$report_file" <<EOF
{
  "timestamp": "$(timestamp)",
  "environment": "$ENVIRONMENT",
  "platform": "$PLATFORM",
  "summary": {
    "total": $((${#HEALTHY_SERVICES[@]} + ${#WARNING_SERVICES[@]} + ${#FAILED_SERVICES[@]})),
    "healthy": ${#HEALTHY_SERVICES[@]},
    "warnings": ${#WARNING_SERVICES[@]},
    "failed": ${#FAILED_SERVICES[@]}
  },
  "healthy_services": [$(printf '"%s",' "${HEALTHY_SERVICES[@]}" | sed 's/,$//')],
  "warning_services": [$(printf '"%s",' "${WARNING_SERVICES[@]}" | sed 's/,$//')],
  "failed_services": [$(printf '"%s",' "${FAILED_SERVICES[@]}" | sed 's/,$//')]
}
EOF
  
  info "Health report saved to: $report_file"
}

# Continuous monitoring loop
continuous_monitoring() {
  info "Starting continuous monitoring (interval: ${INTERVAL}s)"
  info "Press Ctrl+C to stop monitoring"
  echo ""
  
  local iteration=1
  
  while true; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔄 Health Check #$iteration - $(timestamp_short)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Reset status arrays
    HEALTHY_SERVICES=()
    WARNING_SERVICES=()
    FAILED_SERVICES=()
    
    # Run health checks
    run_health_checks
    
    # Generate report
    generate_health_report
    save_health_report
    
    echo ""
    info "Next check in ${INTERVAL}s... (Ctrl+C to stop)"
    echo ""
    
    sleep "$INTERVAL"
    ((iteration++))
  done
}

# Run all health checks
run_health_checks() {
  load_env_vars
  
  case "$PLATFORM" in
    "railway")
      test_railway_services
      test_databases
      test_external_services
      ;;
    "gcp")
      test_gcp_services
      test_databases
      test_external_services
      ;;
    "local")
      test_local_services
      test_databases
      test_external_services
      ;;
    "all")
      test_local_services
      test_railway_services
      test_gcp_services
      test_databases
      test_external_services
      check_system_resources
      ;;
    *)
      error "Unknown platform: $PLATFORM"
      return 1
      ;;
  esac
}

# Show usage
show_usage() {
  cat << EOF
Usage: $0 [environment] [platform] [continuous] [interval]

Environment:
  development, staging, production (default: development)

Platform:
  railway, gcp, local, all (default: all)

Continuous:
  true, false (default: false)

Interval:
  Seconds between checks for continuous mode (default: 30)

Examples:
  $0                          # Check all platforms in development
  $0 production railway        # Check Railway in production
  $0 staging all true 60       # Continuous monitoring every 60s
  $0 development local         # Check local services only

EOF
}

# Main execution
main() {
  # Parse arguments
  ENVIRONMENT="${1:-development}"
  PLATFORM="${2:-all}"
  CONTINUOUS="${3:-false}"
  INTERVAL="${4:-30}"
  
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🏥 Comprehensive Health Monitoring"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  info "Environment: $ENVIRONMENT"
  info "Platform: $PLATFORM"
  info "Continuous: $CONTINUOUS"
  [[ "$CONTINUOUS" == "true" ]] && info "Interval: ${INTERVAL}s"
  echo ""
  
  # Check dependencies
  if ! check_dependencies; then
    exit 1
  fi
  
  # Run health checks or continuous monitoring
  if [[ "$CONTINUOUS" == "true" ]]; then
    continuous_monitoring
  else
    run_health_checks
    generate_health_report
    save_health_report
    
    # Exit with appropriate code
    if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
      exit 1
    elif [ ${#WARNING_SERVICES[@]} -gt 0 ]; then
      exit 2
    else
      exit 0
    fi
  fi
}

# Handle script interruption
trap 'echo ""; info "Health monitoring stopped"; exit 0' INT TERM

# Run main function
main "$@"
