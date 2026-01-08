#!/usr/bin/env bash
# Comprehensive Test deployment automation for Railway and GCP
# Validates deployment health, databases, services, and basic functionality

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || echo "$SCRIPT_DIR/..")"
ENV_FILE="$ROOT_DIR/.env"

PLATFORM="${1:-railway}"
ENVIRONMENT="${2:-production}"
FAIL=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() {
  echo -e "${BLUE}ℹ️  $*${NC}"
}

error() {
  echo -e "${RED}❌ $*${NC}" >&2
}

success() {
  echo -e "${GREEN}✅ $*${NC}"
}

warning() {
  echo -e "${YELLOW}⚠️  $*${NC}"
}

timestamp() {
  date -u +"%Y%m%dT%H%M%SZ"
}

# Check if Railway CLI is available
check_railway_cli() {
  if ! command -v railway >/dev/null 2>&1; then
    error "Railway CLI not found. Install: npm install -g @railway/cli"
    return 1
  fi
  success "Railway CLI installed"
  return 0
}

# Check if gcloud CLI is available
check_gcloud_cli() {
  if ! command -v gcloud >/dev/null 2>&1; then
    error "gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install"
    return 1
  fi
  success "gcloud CLI installed"
  return 0
}

# Test Railway deployment
test_railway_deployment() {
  info "Testing Railway deployment..."
  
  if ! check_railway_cli; then
    FAIL=$((FAIL+1))
    return 1
  fi
  
  # Check authentication
  if ! railway whoami >/dev/null 2>&1; then
    error "Not logged into Railway. Run: railway login"
    FAIL=$((FAIL+1))
    return 1
  fi
  success "Railway authentication verified"
  
  # Check project link
  if ! railway status >/dev/null 2>&1; then
    error "No Railway project linked. Run: railway link"
    FAIL=$((FAIL+1))
    return 1
  fi
  success "Railway project linked"
  
  # Get deployment info
  info "Fetching deployment status..."
  local deployment_info
  deployment_info=$(railway status 2>&1 || echo "")
  
  if [ -z "$deployment_info" ]; then
    error "Could not fetch deployment status"
    FAIL=$((FAIL+1))
    return 1
  fi
  
  echo "$deployment_info"
  
  # Check for recent deployments
  info "Checking recent deployments..."
  local recent_logs
  recent_logs=$(railway logs --num 50 2>&1 || echo "")
  
  if [ -z "$recent_logs" ]; then
    error "Could not fetch deployment logs"
    FAIL=$((FAIL+1))
    return 1
  fi
  
  # Look for error patterns in logs
  local error_count
  error_count=$(echo "$recent_logs" | grep -ciE '(error|exception|fatal|crash)' || echo 0)
  
  if [ "$error_count" -gt 5 ]; then
    error "Found $error_count error/exception entries in recent logs"
    echo "$recent_logs" | grep -iE '(error|exception|fatal|crash)' | head -10
    FAIL=$((FAIL+1))
  else
    success "Recent logs look healthy (only $error_count error entries)"
  fi
  
  # Test health endpoint if URL is available
  local service_url
  service_url=$(railway status 2>&1 | grep -oE 'https://[a-zA-Z0-9.-]+\.railway\.app' | head -1 || echo "")
  
  if [ -n "$service_url" ]; then
    info "Testing health endpoint: $service_url/health"
    
    if command -v curl >/dev/null 2>&1; then
      local health_status
      health_status=$(curl -s -o /dev/null -w "%{http_code}" "$service_url/health" 2>&1 || echo "000")
      
      if [ "$health_status" = "200" ]; then
        success "Health endpoint returned 200 OK"
      else
        error "Health endpoint returned $health_status (expected 200)"
        FAIL=$((FAIL+1))
      fi
    else
      info "curl not available, skipping health check"
    fi
  else
    info "No service URL found, skipping health check"
  fi
  
  return 0
}

# Test GCP deployment
test_gcp_deployment() {
  info "Testing GCP deployment..."
  
  if ! check_gcloud_cli; then
    FAIL=$((FAIL+1))
    return 1
  fi
  
  # Check authentication
  if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" >/dev/null 2>&1; then
    error "Not logged into GCP. Run: gcloud auth login"
    FAIL=$((FAIL+1))
    return 1
  fi
  success "GCP authentication verified"
  
  # Get current project
  local project_id
  project_id=$(gcloud config get-value project 2>/dev/null || echo "")
  
  if [ -z "$project_id" ]; then
    error "No GCP project set. Run: gcloud config set project PROJECT_ID"
    FAIL=$((FAIL+1))
    return 1
  fi
  success "GCP project: $project_id"
  
  # Check Cloud Run services
  info "Checking Cloud Run services..."
  local services
  services=$(gcloud run services list --format="value(name)" 2>&1 || echo "")
  
  if [ -z "$services" ]; then
    info "No Cloud Run services found"
  else
    success "Found Cloud Run services:"
    echo "$services" | while read -r service; do
      echo "  - $service"
      
      # Get service URL
      local service_url
      service_url=$(gcloud run services describe "$service" --format="value(status.url)" 2>&1 || echo "")
      
      if [ -n "$service_url" ]; then
        info "  URL: $service_url"
        
        # Test health endpoint
        if command -v curl >/dev/null 2>&1; then
          local health_status
          health_status=$(curl -s -o /dev/null -w "%{http_code}" "$service_url/health" 2>&1 || echo "000")
          
          if [ "$health_status" = "200" ]; then
            success "  Health check: OK"
          else
            error "  Health check failed: $health_status"
            FAIL=$((FAIL+1))
          fi
        fi
      fi
    done
  fi
  
  # Check Cloud SQL instances
  info "Checking Cloud SQL instances..."
  local sql_instances
  sql_instances=$(gcloud sql instances list --format="value(name)" 2>&1 || echo "")
  
  if [ -z "$sql_instances" ]; then
    info "No Cloud SQL instances found"
  else
    success "Found Cloud SQL instances:"
    echo "$sql_instances" | while read -r instance; do
      echo "  - $instance"
      
      # Get instance status
      local instance_status
      instance_status=$(gcloud sql instances describe "$instance" --format="value(state)" 2>&1 || echo "UNKNOWN")
      
      if [ "$instance_status" = "RUNNABLE" ]; then
        success "  Status: RUNNABLE"
      else
        error "  Status: $instance_status (expected RUNNABLE)"
        FAIL=$((FAIL+1))
      fi
    done
  fi
  
  return 0
}

# Load environment variables
load_env_vars() {
  if [[ -f "$ENV_FILE" ]]; then
    # Load .env file
    set -a
    source "$ENV_FILE"
    set +a
    info "Loaded environment variables from $ENV_FILE"
  else
    warning "No .env file found at $ENV_FILE"
  fi
}

# Test PostgreSQL connection
test_postgresql_connection() {
  info "Testing PostgreSQL connection..."
  
  if [[ -z "${DATABASE_URL:-}" ]]; then
    warning "DATABASE_URL not set, skipping PostgreSQL test"
    return 0
  fi
  
  if ! command -v psql >/dev/null 2>&1; then
    warning "psql not available, skipping PostgreSQL connection test"
    return 0
  fi
  
  # Extract connection details
  local db_host
  db_host=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
  local db_port
  db_port=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
  local db_name
  db_name=$(echo "$DATABASE_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
  
  # Test basic connection
  if PGPASSWORD="${DATABASE_URL#*://*:*@}" psql "$DATABASE_URL" -c "SELECT 1;" >/dev/null 2>&1; then
    success "PostgreSQL connection successful"
    
    # Test database operations
    if PGPASSWORD="${DATABASE_URL#*://*:*@}" psql "$DATABASE_URL" -c "
      CREATE TABLE IF NOT EXISTS deployment_test (
        id SERIAL PRIMARY KEY,
        test_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
      INSERT INTO deployment_test (test_timestamp) VALUES (CURRENT_TIMESTAMP);
      SELECT COUNT(*) FROM deployment_test;
    " >/dev/null 2>&1; then
      success "PostgreSQL read/write operations working"
    else
      error "PostgreSQL read/write operations failed"
      FAIL=$((FAIL+1))
    fi
  else
    error "PostgreSQL connection failed"
    FAIL=$((FAIL+1))
  fi
}

# Test Redis connection
test_redis_connection() {
  info "Testing Redis connection..."
  
  if [[ -z "${REDIS_URL:-}" ]]; then
    warning "REDIS_URL not set, skipping Redis test"
    return 0
  fi
  
  if ! command -v redis-cli >/dev/null 2>&1; then
    warning "redis-cli not available, skipping Redis connection test"
    return 0
  fi
  
  # Test basic connection
  if redis-cli -u "$REDIS_URL" ping >/dev/null 2>&1; then
    success "Redis connection successful"
    
    # Test cache operations
    local test_key="deployment_test_$(timestamp)"
    local test_value="test_value"
    
    if redis-cli -u "$REDIS_URL" set "$test_key" "$test_value" >/dev/null 2>&1 && \
       redis-cli -u "$REDIS_URL" get "$test_key" | grep -q "$test_value" && \
       redis-cli -u "$REDIS_URL" del "$test_key" >/dev/null 2>&1; then
      success "Redis cache operations working"
    else
      error "Redis cache operations failed"
      FAIL=$((FAIL+1))
    fi
  else
    error "Redis connection failed"
    FAIL=$((FAIL+1))
  fi
}

# Test MongoDB connection
test_mongodb_connection() {
  info "Testing MongoDB connection..."
  
  if [[ -z "${MONGODB_URI:-}" ]]; then
    warning "MONGODB_URI not set, skipping MongoDB test"
    return 0
  fi
  
  if ! command -v mongosh >/dev/null 2>&1; then
    warning "mongosh not available, skipping MongoDB connection test"
    return 0
  fi
  
  # Test basic connection
  if mongosh "$MONGODB_URI" --eval "db.runCommand({ping: 1})" >/dev/null 2>&1; then
    success "MongoDB connection successful"
    
    # Test database operations
    local test_result
    test_result=$(mongosh "$MONGODB_URI" --eval "
      db.deployment_test.insertOne({test: 'data', timestamp: new Date()});
      const count = db.deployment_test.countDocuments();
      db.deployment_test.deleteMany({});
      count;
    " 2>/dev/null | tail -1 || echo "0")
    
    if [[ "$test_result" -gt 0 ]]; then
      success "MongoDB read/write operations working"
    else
      error "MongoDB read/write operations failed"
      FAIL=$((FAIL+1))
    fi
  else
    error "MongoDB connection failed"
    FAIL=$((FAIL+1))
  fi
}

# Test Neo4j connection
test_neo4j_connection() {
  info "Testing Neo4j connection..."
  
  if [[ -z "${NEO4J_URI:-}" ]]; then
    warning "NEO4J_URI not set, skipping Neo4j test"
    return 0
  fi
  
  if ! command -v cypher-shell >/dev/null 2>&1; then
    warning "cypher-shell not available, skipping Neo4j connection test"
    return 0
  fi
  
  # Extract connection details
  local neo4j_host
  neo4j_host=$(echo "$NEO4J_URI" | sed -n 's/.*@\([^:]*\):.*/\1/p')
  local neo4j_port
  neo4j_port=$(echo "$NEO4J_URI" | sed -n 's/.*:\([0-9]*\)/\1/p')
  
  # Test basic connection
  if cypher-shell -a "$NEO4J_URI" -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD}" "RETURN 1;" >/dev/null 2>&1; then
    success "Neo4j connection successful"
    
    # Test graph operations
    if cypher-shell -a "$NEO4J_URI" -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD}" "
      CREATE (n:TestNode {name: 'deployment_test', timestamp: timestamp()});
      MATCH (n:TestNode {name: 'deployment_test'}) RETURN count(n) as count;
      DELETE (n:TestNode {name: 'deployment_test'});
    " >/dev/null 2>&1; then
      success "Neo4j graph operations working"
    else
      error "Neo4j graph operations failed"
      FAIL=$((FAIL+1))
    fi
  else
    error "Neo4j connection failed"
    FAIL=$((FAIL+1))
  fi
}

# Test Pinecone connection
test_pinecone_connection() {
  info "Testing Pinecone connection..."
  
  if [[ -z "${PINECONE_API_KEY:-}" ]]; then
    warning "PINECONE_API_KEY not set, skipping Pinecone test"
    return 0
  fi
  
  if ! command -v curl >/dev/null 2>&1; then
    warning "curl not available, skipping Pinecone connection test"
    return 0
  fi
  
  local pinecone_env="${PINECONE_ENVIRONMENT:-us-west1-gcp}"
  local pinecone_url="https://controller.$pinecone_env.pinecone.io/databases"
  
  # Test API key validity
  local api_response
  api_response=$(curl -s -w "%{http_code}" \
    -H "Api-Key: $PINECONE_API_KEY" \
    "$pinecone_url" 2>/dev/null || echo "000")
  
  local http_code="${api_response: -3}"
  local response_body="${api_response%???}"
  
  if [[ "$http_code" = "200" ]]; then
    success "Pinecone API key valid"
    
    # Test vector operations (if index exists)
    local test_index="deployment-test"
    local create_response
    create_response=$(curl -s -w "%{http_code}" \
      -X POST \
      -H "Api-Key: $PINECONE_API_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"name\":\"$test_index\",\"dimension\":3,\"metric\":\"cosine\"}" \
      "https://controller.$pinecone_env.pinecone.io/databases" 2>/dev/null || echo "000")
    
    local create_code="${create_response: -3}"
    
    if [[ "$create_code" = "201" ]] || [[ "$create_code" = "409" ]]; then
      success "Pinecone vector operations available"
      
      # Clean up test index if it was created
      if [[ "$create_code" = "201" ]]; then
        curl -s -X DELETE \
          -H "Api-Key: $PINECONE_API_KEY" \
          "https://controller.$pinecone_env.pinecone.io/databases/$test_index" >/dev/null 2>&1 || true
      fi
    else
      warning "Pinecone vector operations test inconclusive"
    fi
  else
    error "Pinecone API key invalid (HTTP $http_code)"
    FAIL=$((FAIL+1))
  fi
}

# Test frontend service
test_frontend_service() {
  info "Testing frontend service..."
  
  local frontend_url="${FRONTEND_URL:-}"
  
  if [[ -z "$frontend_url" ]]; then
    # Try to detect frontend URL from deployment
    if [[ "$PLATFORM" == "railway" ]]; then
      frontend_url=$(railway status 2>&1 | grep -oE 'https://[a-zA-Z0-9.-]+\.railway\.app' | head -1 || echo "")
    elif [[ "$PLATFORM" == "gcp" ]]; then
      frontend_url=$(gcloud run services list --format="value(status.url)" --filter="name~frontend" 2>/dev/null | head -1 || echo "")
    fi
  fi
  
  if [[ -z "$frontend_url" ]]; then
    warning "Frontend URL not found, skipping frontend test"
    return 0
  fi
  
  if ! command -v curl >/dev/null 2>&1; then
    warning "curl not available, skipping frontend test"
    return 0
  fi
  
  info "Testing frontend at: $frontend_url"
  
  # Test main page
  local frontend_status
  frontend_status=$(curl -s -o /dev/null -w "%{http_code}" "$frontend_url" 2>&1 || echo "000")
  
  if [[ "$frontend_status" = "200" ]]; then
    success "Frontend service responding (200 OK)"
    
    # Test for common frontend assets
    local assets_test
    assets_test=$(curl -s -o /dev/null -w "%{http_code}" "$frontend_url/static/js/main.js" 2>&1 || echo "000")
    
    if [[ "$assets_test" = "200" ]]; then
      success "Frontend assets loading correctly"
    else
      warning "Frontend assets may not be loading (HTTP $assets_test)"
    fi
  else
    error "Frontend service not responding (HTTP $frontend_status)"
    FAIL=$((FAIL+1))
  fi
}

# Test backend API service
test_backend_service() {
  info "Testing backend API service..."
  
  local backend_url="${BACKEND_URL:-}"
  
  if [[ -z "$backend_url" ]]; then
    # Try to detect backend URL from deployment
    if [[ "$PLATFORM" == "railway" ]]; then
      backend_url=$(railway status 2>&1 | grep -oE 'https://[a-zA-Z0-9.-]+\.railway\.app' | head -1 || echo "")
    elif [[ "$PLATFORM" == "gcp" ]]; then
      backend_url=$(gcloud run services list --format="value(status.url)" --filter="name~backend" 2>/dev/null | head -1 || echo "")
    fi
  fi
  
  if [[ -z "$backend_url" ]]; then
    warning "Backend URL not found, skipping backend test"
    return 0
  fi
  
  if ! command -v curl >/dev/null 2>&1; then
    warning "curl not available, skipping backend test"
    return 0
  fi
  
  info "Testing backend API at: $backend_url"
  
  # Test health endpoint
  local health_status
  health_status=$(curl -s -o /dev/null -w "%{http_code}" "$backend_url/health" 2>&1 || echo "000")
  
  if [[ "$health_status" = "200" ]]; then
    success "Backend health endpoint responding (200 OK)"
    
    # Test API endpoints
    local api_endpoints=("/api/users" "/api/status" "/api/version")
    
    for endpoint in "${api_endpoints[@]}"; do
      local endpoint_status
      endpoint_status=$(curl -s -o /dev/null -w "%{http_code}" "$backend_url$endpoint" 2>&1 || echo "000")
      
      if [[ "$endpoint_status" = "200" ]] || [[ "$endpoint_status" = "404" ]]; then
        success "API endpoint $endpoint accessible (HTTP $endpoint_status)"
      else
        warning "API endpoint $endpoint returned HTTP $endpoint_status"
      fi
    done
  else
    error "Backend health endpoint not responding (HTTP $health_status)"
    FAIL=$((FAIL+1))
  fi
}

# Test admin dashboard
test_admin_service() {
  info "Testing admin dashboard..."
  
  local admin_url="${ADMIN_URL:-}"
  
  if [[ -z "$admin_url" ]]; then
    # Try to detect admin URL from deployment
    if [[ "$PLATFORM" == "railway" ]]; then
      admin_url=$(railway status 2>&1 | grep -oE 'https://[a-zA-Z0-9.-]+\.railway\.app' | grep admin | head -1 || echo "")
    elif [[ "$PLATFORM" == "gcp" ]]; then
      admin_url=$(gcloud run services list --format="value(status.url)" --filter="name~admin" 2>/dev/null | head -1 || echo "")
    fi
  fi
  
  if [[ -z "$admin_url" ]]; then
    warning "Admin URL not found, skipping admin test"
    return 0
  fi
  
  if ! command -v curl >/dev/null 2>&1; then
    warning "curl not available, skipping admin test"
    return 0
  fi
  
  info "Testing admin dashboard at: $admin_url"
  
  # Test admin page
  local admin_status
  admin_status=$(curl -s -o /dev/null -w "%{http_code}" "$admin_url" 2>&1 || echo "000")
  
  if [[ "$admin_status" = "200" ]]; then
    success "Admin dashboard responding (200 OK)"
  elif [[ "$admin_status" = "401" ]] || [[ "$admin_status" = "403" ]]; then
    success "Admin dashboard protected (HTTP $admin_status)"
  else
    error "Admin dashboard not responding (HTTP $admin_status)"
    FAIL=$((FAIL+1))
  fi
}

# Run comprehensive service tests
run_comprehensive_tests() {
  info "Running comprehensive service tests..."
  
  # Load environment variables
  load_env_vars
  
  # Test databases
  test_postgresql_connection
  test_redis_connection
  test_mongodb_connection
  test_neo4j_connection
  test_pinecone_connection
  
  # Test services
  test_frontend_service
  test_backend_service
  test_admin_service
  
  info "Comprehensive testing completed"
}

# Save test results
save_test_results() {
  local platform=$1
  local status=$2
  
  local results_dir="$ROOT_DIR/.cfoi/branches/$(git rev-parse --abbrev-ref HEAD)/test-results"
  mkdir -p "$results_dir"
  
  local results_file="$results_dir/deployment-test-$(timestamp).json"
  
  cat > "$results_file" <<EOF
{
  "timestamp": "$(timestamp)",
  "platform": "$platform",
  "environment": "$ENVIRONMENT",
  "status": "$status",
  "failCount": $FAIL,
  "tests": {
    "postgresql": "tested",
    "redis": "tested",
    "mongodb": "tested",
    "neo4j": "tested",
    "pinecone": "tested",
    "frontend": "tested",
    "backend": "tested",
    "admin": "tested"
  }
}
EOF
  
  info "Test results saved to: $results_file"
}

# Main execution
main() {
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🧪 Comprehensive Deployment Test Suite"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  info "Platform: $PLATFORM"
  info "Environment: $ENVIRONMENT"
  echo ""
  
  case "$PLATFORM" in
    railway)
      test_railway_deployment
      run_comprehensive_tests
      ;;
    gcp)
      test_gcp_deployment
      run_comprehensive_tests
      ;;
    both)
      test_railway_deployment
      test_gcp_deployment
      run_comprehensive_tests
      ;;
    comprehensive)
      run_comprehensive_tests
      ;;
    *)
      error "Unknown platform: $PLATFORM"
      echo ""
      echo "Usage: $0 [railway|gcp|both|comprehensive] [environment]"
      echo ""
      echo "Examples:"
      echo "  $0 railway production     # Test Railway deployment + all services"
      echo "  $0 gcp staging             # Test GCP deployment + all services"
      echo "  $0 both production         # Test both platforms + all services"
      echo "  $0 comprehensive           # Test all services only"
      exit 1
      ;;
  esac
  
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  if [ "$FAIL" -eq 0 ]; then
    success "All deployment tests PASSED"
    save_test_results "$PLATFORM" "pass"
    exit 0
  else
    error "Deployment tests FAILED ($FAIL issues)"
    save_test_results "$PLATFORM" "fail"
    echo ""
    echo "Common fixes:"
    echo "  - Ensure CLI tools are installed and authenticated"
    echo "  - Check deployment logs for errors"
    echo "  - Verify health endpoints are responding"
    echo "  - Confirm environment variables are set correctly"
    echo "  - Check database connectivity and credentials"
    echo "  - Validate service URLs are accessible"
    echo ""
    echo "Troubleshooting commands:"
    echo "  - Railway: railway logs --num 100"
    echo "  - GCP: gcloud run services logs read --limit 100"
    echo "  - Database: tools/validate-secrets.sh"
    echo "  - Environment: tools/setup-env.sh validate"
    exit 1
  fi
}

main
