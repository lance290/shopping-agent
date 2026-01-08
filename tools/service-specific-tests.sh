#!/usr/bin/env bash

# Service-Specific Tests Script
# Specialized tests for databases, APIs, and service integrations

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# Configuration
SERVICE="${1:-all}"
ENVIRONMENT="${2:-development}"
VERBOSE="${3:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test results
PASSED_TESTS=()
FAILED_TESTS=()
SKIPPED_TESTS=()

# Logging functions
info() { echo -e "${BLUE}ℹ️  $*${NC}"; }
success() { echo -e "${GREEN}✅ $*${NC}"; PASSED_TESTS+=("$*"); }
warning() { echo -e "${YELLOW}⚠️  $*${NC}"; SKIPPED_TESTS+=("$*"); }
error() { echo -e "${RED}❌ $*${NC}"; FAILED_TESTS+=("$*"); }
debug() { [[ "$VERBOSE" == "true" ]] && echo -e "${CYAN}🔍 DEBUG: $*${NC}"; }

timestamp() { date +"%Y-%m-%d %H:%M:%S"; }

# Load environment variables
load_env_vars() {
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    source "$ENV_FILE"
    set +a
    debug "Loaded environment variables from $ENV_FILE"
  else
    warning "No .env file found at $ENV_FILE"
    return 1
  fi
}

# Check dependencies
check_dependencies() {
  local missing_deps=()
  
  case "$SERVICE" in
    "postgresql"|"all")
      if ! command -v psql &> /dev/null; then
        missing_deps+=("postgresql-client")
      fi
      ;;
    "redis"|"all")
      if ! command -v redis-cli &> /dev/null; then
        missing_deps+=("redis-tools")
      fi
      ;;
    "mongodb"|"all")
      if ! command -v mongosh &> /dev/null; then
        missing_deps+=("mongodb-mongosh")
      fi
      ;;
    "neo4j"|"all")
      if ! command -v cypher-shell &> /dev/null; then
        missing_deps+=("neo4j-client")
      fi
      ;;
  esac
  
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

# PostgreSQL specific tests
test_postgresql() {
  info "Running PostgreSQL specific tests..."
  
  if [[ -z "${DATABASE_URL:-}" ]]; then
    warning "DATABASE_URL not configured, skipping PostgreSQL tests"
    return 0
  fi
  
  debug "Testing PostgreSQL at: $DATABASE_URL"
  
  # Test 1: Basic connection
  if ! PGPASSWORD="${DATABASE_URL#*://*:**@}" psql "$DATABASE_URL" -c "SELECT 1;" >/dev/null 2>&1; then
    error "PostgreSQL: Basic connection failed"
    return 1
  fi
  success "PostgreSQL: Basic connection OK"
  
  # Test 2: Database permissions
  local db_name
  db_name=$(echo "$DATABASE_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
  
  if PGPASSWORD="${DATABASE_URL#*://*:**@}" psql "$DATABASE_URL" -c "
    CREATE TABLE IF NOT EXISTS test_permissions (
      id SERIAL PRIMARY KEY,
      test_data TEXT
    );
    INSERT INTO test_permissions (test_data) VALUES ('permission_test');
    DROP TABLE test_permissions;
  " >/dev/null 2>&1; then
    success "PostgreSQL: Database permissions OK"
  else
    error "PostgreSQL: Database permissions failed"
    return 1
  fi
  
  # Test 3: Transaction support
  if PGPASSWORD="${DATABASE_URL#*://*:**@}" psql "$DATABASE_URL" -c "
    BEGIN TRANSACTION;
    CREATE TEMP TABLE transaction_test (id INTEGER);
    INSERT INTO transaction_test VALUES (1);
    SELECT COUNT(*) FROM transaction_test;
    ROLLBACK;
  " >/dev/null 2>&1; then
    success "PostgreSQL: Transaction support OK"
  else
    error "PostgreSQL: Transaction support failed"
    return 1
  fi
  
  # Test 4: Index operations
  if PGPASSWORD="${DATABASE_URL#*://*:**@}" psql "$DATABASE_URL" -c "
    CREATE TEMP TABLE index_test (
      id SERIAL PRIMARY KEY,
      name TEXT,
      email TEXT
    );
    CREATE INDEX idx_test_name ON index_test(name);
    CREATE INDEX idx_test_email ON index_test(email);
    INSERT INTO index_test (name, email) 
    SELECT 'user_' || generate_series, 'user' || generate_series || '@test.com' 
    FROM generate_series(1, 100);
    EXPLAIN ANALYZE SELECT * FROM index_test WHERE name = 'user_50';
    DROP TABLE index_test;
  " >/dev/null 2>&1; then
    success "PostgreSQL: Index operations OK"
  else
    warning "PostgreSQL: Index operations failed"
  fi
  
  # Test 5: Connection pooling (if configured)
  local max_connections
  max_connections=$(PGPASSWORD="${DATABASE_URL#*://*:*@}" psql "$DATABASE_URL" -t -c "SHOW setting FROM pg_settings WHERE name = 'max_connections'" 2>/dev/null | tr -d ' ' || echo "unknown")
  
  if [[ "$max_connections" != "unknown" && $max_connections -gt 50 ]]; then
    success "PostgreSQL: Connection pooling available (max: $max_connections)"
  else
    warning "PostgreSQL: Limited connection pooling (max: $max_connections)"
  fi
  
  return 0
}

# Redis specific tests
test_redis() {
  info "Running Redis specific tests..."
  
  if [[ -z "${REDIS_URL:-}" ]]; then
    warning "REDIS_URL not configured, skipping Redis tests"
    return 0
  fi
  
  debug "Testing Redis at: $REDIS_URL"
  
  # Test 1: Basic connection
  if ! redis-cli -u "$REDIS_URL" ping >/dev/null 2>&1; then
    error "Redis: Basic connection failed"
    return 1
  fi
  success "Redis: Basic connection OK"
  
  # Test 2: Basic operations
  local test_key="test_key_$(date +%s)"
  local test_value="test_value_$(date +%s)"
  
  if redis-cli -u "$REDIS_URL" set "$test_key" "$test_value" >/dev/null 2>&1 && \
     redis-cli -u "$REDIS_URL" get "$test_key" | grep -q "$test_value" && \
     redis-cli -u "$REDIS_URL" del "$test_key" >/dev/null 2>&1; then
    success "Redis: Basic operations OK"
  else
    error "Redis: Basic operations failed"
    return 1
  fi
  
  # Test 3: Data type operations
  if redis-cli -u "$REDIS_URL" \
    set "test_string" "string_value" && \
    hset "test_hash" "field1" "value1" "field2" "value2" && \
    lpush "test_list" "item1" "item2" "item3" && \
    sadd "test_set" "member1" "member2" && \
    zadd "test_zset" 1 "score1" 2 "score2" >/dev/null 2>&1; then
    success "Redis: Data type operations OK"
    
    # Cleanup
    redis-cli -u "$REDIS_URL" del "test_string" "test_hash" "test_list" "test_set" "test_zset" >/dev/null 2>&1
  else
    error "Redis: Data type operations failed"
    return 1
  fi
  
  # Test 4: Expiration
  local expire_key="expire_test_$(date +%s)"

  if redis-cli -u "$REDIS_URL" setex "$expire_key" 1 "expire_value" >/dev/null 2>&1; then
    sleep 2
    if ! redis-cli -u "$REDIS_URL" exists "$expire_key" | grep -q "1"; then
      success "Redis: Expiration OK"
    else
      error "Redis: Expiration failed"
      return 1
    fi
  else
    error "Redis: Expiration test failed"
    return 1
  fi
  
  # Test 5: Memory usage
  local memory_info
  memory_info=$(redis-cli -u "$REDIS_URL" info memory 2>/dev/null | grep "used_memory_human" | cut -d: -f2 | tr -d '\r' || echo "unknown")
  
  if [[ "$memory_info" != "unknown" ]]; then
    success "Redis: Memory usage $memory_info"
  else
    warning "Redis: Could not get memory info"
  fi
  
  # Test 6: Pub/Sub (basic)
  local pubsub_test="pubsub_test_$(date +%s)"

  # Start a subscriber in background
  redis-cli -u "$REDIS_URL" subscribe "$pubsub_test" >/dev/null 2>&1 &
  local subscriber_pid=$!
  
  sleep 1
  
  # Publish message
  if redis-cli -u "$REDIS_URL" publish "$pubsub_test" "test_message" >/dev/null 2>&1; then
    success "Redis: Pub/Sub OK"
  else
    warning "Redis: Pub/Sub test failed"
  fi
  
  # Clean up
  kill $subscriber_pid 2>/dev/null || true
  
  return 0
}

# MongoDB specific tests
test_mongodb() {
  info "Running MongoDB specific tests..."
  
  if [[ -z "${MONGODB_URI:-}" ]]; then
    warning "MONGODB_URI not configured, skipping MongoDB tests"
    return 0
  fi
  
  debug "Testing MongoDB at: $MONGODB_URI"
  
  # Test 1: Basic connection
  if ! mongosh "$MONGODB_URI" --eval "db.runCommand({ping: 1})" >/dev/null 2>&1; then
    error "MongoDB: Basic connection failed"
    return 1
  fi
  success "MongoDB: Basic connection OK"
  
  # Test 2: Database operations
  local test_result
  test_result=$(mongosh "$MONGODB_URI" --eval "
    db.test_collection.insertOne({
      name: 'test_doc',
      timestamp: new Date(),
      data: { field1: 'value1', field2: 42 }
    });
    const doc = db.test_collection.findOne({name: 'test_doc'});
    db.test_collection.deleteMany({name: 'test_doc'});
    doc ? 'success' : 'failed';
  " 2>/dev/null | tail -1 || echo "failed")
  
  if [[ "$test_result" == "success" ]]; then
    success "MongoDB: CRUD operations OK"
  else
    error "MongoDB: CRUD operations failed"
    return 1
  fi
  
  # Test 3: Index operations
  local index_result
  index_result=$(mongosh "$MONGODB_URI" --eval "
    db.test_index.insertMany([
      {name: 'doc1', category: 'A'},
      {name: 'doc2', category: 'b'},
      {name: 'doc3', category: 'a'}
    ]);
    db.test_index.createIndex({name: 1});
    db.test_index.createIndex({category: 1});
    const explainResult = db.test_index.find({category: 'a'}).explain('executionStats');
    db.test_index.drop();
    explainResult.executionStats.totalDocsExamined < 3 ? 'success' : 'failed';
  " 2>/dev/null | tail -1 || echo "failed")
  
  if [[ "$index_result" == "success" ]]; then
    success "MongoDB: Index operations OK"
  else
    warning "MongoDB: Index operations test failed"
  fi
  
  # Test 4: Aggregation
  local agg_result
  agg_result=$(mongosh "$MONGODB_URI" --eval "
    db.test_agg.insertMany([
      {category: 'A', value: 10},
      {category: 'b', value: 20},
      {category: 'a', value: 15}
    ]);
    const result = db.test_agg.aggregate([
      {\$group: {_id: '\$category', total: {\$sum: '\$value'}}},
      {\$sort: {total: -1}}
    ]).toArray();
    db.test_agg.drop();
    result.length > 0 ? 'success' : 'failed';
  " 2>/dev/null | tail -1 || echo "failed")
  
  if [[ "$agg_result" == "success" ]]; then
    success "MongoDB: Aggregation operations OK"
  else
    warning "MongoDB: Aggregation operations test failed"
  fi
  
  # Test 5: Connection info
  local server_info
  server_info=$(mongosh "$MONGODB_URI" --eval "
    const info = db.runCommand({serverStatus: 1});
    JSON.stringify({
      version: info.version,
      connections: info.connections.current,
      uptime: info.uptime
    });
  " 2>/dev/null | tail -1 || echo "{}")
  
  if [[ "$server_info" != "{}" ]]; then
    success "MongoDB: Server info retrieved"
    debug "MongoDB info: $server_info"
  else
    warning "MongoDB: Could not retrieve server info"
  fi
  
  return 0
}

# Neo4j specific tests
test_neo4j() {
  info "Running Neo4j specific tests..."
  
  if [[ -z "${NEO4J_URI:-}" ]]; then
    warning "NEO4J_URI not configured, skipping Neo4j tests"
    return 0
  fi
  
  debug "Testing Neo4j at: $NEO4J_URI"
  
  # Test 1: Basic connection
  if ! cypher-shell -a "$NEO4J_URI" -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD}" "RETURN 1;" >/dev/null 2>&1; then
    error "Neo4j: Basic connection failed"
    return 1
  fi
  success "Neo4j: Basic connection OK"
  
  # Test 2: Node operations
  local node_result
  node_result=$(cypher-shell -a "$NEO4J_URI" -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD}" "
    CREATE (n:TestNode {name: 'test_node', timestamp: timestamp()});
    MATCH (n:TestNode {name: 'test_node'}) RETURN count(n) as count;
    DELETE (n:TestNode {name: 'test_node'});
  " 2>/dev/null | grep -E "^[0-9]+$" || echo "0")
  
  if [[ "$node_result" -gt 0 ]]; then
    success "Neo4j: Node operations OK"
  else
    error "Neo4j: Node operations failed"
    return 1
  fi
  
  # Test 3: Relationship operations
  local rel_result
  rel_result=$(cypher-shell -a "$NEO4J_URI" -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD}" "
    CREATE (a:Person {name: 'Alice'}), (b:Person {name: 'Bob'});
    CREATE (a)-[:KNOWS {since: 202}]->(b);
    MATCH (a:Person {name: 'Alice'})-[:KNOWS]->(b:Person {name: 'Bob'}) 
    RETURN count(a) as count;
    DELETE (a), (b);
  " 2>/dev/null | grep -E "^[0-9]+$" || echo "0")
  
  if [[ "$rel_result" -gt 0 ]]; then
    success "Neo4j: Relationship operations OK"
  else
    error "Neo4j: Relationship operations failed"
    return 1
  fi
  
  # Test 4: Query performance
  local query_result
  query_result=$(cypher-shell -a "$NEO4J_URI" -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD}" "
    CREATE (n:TestNode {id: 1});
    CREATE INDEX test_index IF NOT EXISTS FOR (n:TestNode) ON (n.id);
    EXPLAIN MATCH (n:TestNode {id: 1}) RETURN n;
    DELETE (n:TestNode);
    DROP INDEX test_index IF NOT EXISTS;
  " 2>/dev/null | grep -q "IndexScan" && echo "success" || echo "failed")
  
  if [[ "$query_result" == "success" ]]; then
    success "Neo4j: Query optimization OK"
  else
    warning "Neo4j: Query optimization test failed"
  fi
  
  # Test 5: Database info
  local db_info
  db_info=$(cypher-shell -a "$NEO4J_URI" -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD}" "
    CALL dbms.components() Y Y version, editions YIELD name, versions, editions
    RETURN name, versions[0] as version;
  " 2>/dev/null | grep -v "name" | head -1 || echo "unknown")
  
  if [[ "$db_info" != "unknown" ]]; then
    success "Neo4j: Database info retrieved"
    debug "Neo4j info: $db_info"
  else
    warning "Neo4j: Could not retrieve database info"
  fi
  
  return 0
}

# API service tests
test_api_service() {
  info "Running API service tests..."
  
  local base_url="${BACKEND_URL:-http://localhost:8080}"
  
  # Test 1: Health endpoint
  local health_status
  health_status=$(curl -s -o /dev/null -w "%{http_code}" "$base_url/health" 2>/dev/null || echo "000")
  
  if [[ "$health_status" == "000" ]]; then
    warning "API service not reachable at $base_url"
    return 1
  elif [[ "$health_status" == "200" ]]; then
    success "API: Health endpoint OK"
  else
    warning "API: Health endpoint returned $health_status"
  fi
  
  # Test 2: API endpoints
  local endpoints=("/api/status" "/api/version" "/api/users")
  
  for endpoint in "${endpoints[@]}"; do
    local endpoint_status
    endpoint_status=$(curl -s -o /dev/null -w "%{http_code}" "$base_url$endpoint" 2>/dev/null || echo "000")
    
    if [[ "$endpoint_status" == "200" ]]; then
      success "API: $endpoint OK"
    elif [[ "$endpoint_status" == "404" ]]; then
      warning "API: $endpoint not implemented"
    else
      warning "API: $endpoint returned $endpoint_status"
    fi
  done
  
  # Test 3: CORS headers
  local cors_headers
  cors_headers=$(curl -s -I "$base_url/api/status" 2>/dev/null | grep -i "access-control-allow-origin" || echo "")
  
  if [[ -n "$cors_headers" ]]; then
    success "API: CORS headers present"
  else
    warning "API: CORS headers missing"
  fi
  
  # Test 4: Rate limiting (basic test)
  local rate_limit_test=0
  for i in {1..10}; do
    local rate_status
    rate_status=$(curl -s -o /dev/null -w "%{http_code}" "$base_url/api/status" 2>/dev/null || echo "000")
    
    if [[ "$rate_status" == "429" ]]; then
      ((rate_limit_test++))
    fi
    sleep 0.1
  done
  
  if [[ $rate_limit_test -gt 0 ]]; then
    success "API: Rate limiting active"
  else
    warning "API: Rate limiting not detected"
  fi
  
  return 0
}

# Frontend service tests
test_frontend_service() {
  info "Running frontend service tests..."
  
  local base_url="${FRONTEND_URL:-http://localhost:3000}"
  
  # Test 1: Main page
  local main_status
  main_status=$(curl -s -o /dev/null -w "%{http_code}" "$base_url" 2>/dev/null || echo "000")
  
  if [[ "$main_status" == "000" ]]; then
    warning "Frontend service not reachable at $base_url"
    return 1
  elif [[ "$main_status" == "200" ]]; then
    success "Frontend: Main page OK"
  else
    warning "Frontend: Main page returned $main_status"
  fi
  
  # Test 2: Static assets
  local assets=("/static/js/main.js" "/static/css/main.css" "/favicon.ico")
  
  for asset in "${assets[@]}"; do
    local asset_status
    asset_status=$(curl -s -o /dev/null -w "%{http_code}" "$base_url$asset" 2>/dev/null || echo "000")
    
    if [[ "$asset_status" == "200" ]]; then
      success "Frontend: $asset OK"
    elif [[ "$asset_status" == "404" ]]; then
      warning "Frontend: $asset not found"
    else
      warning "Frontend: $asset returned $asset_status"
    fi
  done
  
  # Test 3: Security headers
  local security_headers
  security_headers=$(curl -s -I "$base_url" 2>/dev/null | grep -i -E "(x-frame-options|x-content-type-options|content-security-policy)" || echo "")
  
  if [[ -n "$security_headers" ]]; then
    success "Frontend: Security headers present"
  else
    warning "Frontend: Security headers missing"
  fi
  
  # Test 4: Page size (basic performance)
  local page_size
  page_size=$(curl -s "$base_url" | wc -c 2>/dev/null || echo "0")
  
  if [[ $page_size -gt 0 ]]; then
    if [[ $page_size -lt 1000000 ]]; then
      success "Frontend: Page size reasonable (${page_size} bytes)"
    else
      warning "Frontend: Page size large (${page_size} bytes)"
    fi
  else
    warning "Frontend: Could not determine page size"
  fi
  
  return 0
}

# Integration tests
test_integrations() {
  info "Running integration tests..."
  
  # Test 1: Database to API integration
  if [[ -n "${DATABASE_URL:-}" && -n "${BACKEND_URL:-}" ]]; then
    local api_db_status
    api_db_status=$(curl -s "$BACKEND_URL/api/status" 2>/dev/null | jq -r '.database // "unknown"' || echo "unknown")
    
    if [[ "$api_db_status" == "connected" ]]; then
      success "Integration: API to Database OK"
    else
      warning "Integration: API to Database status: $api_db_status"
    fi
  else
    warning "Integration: Database or API URL not configured"
  fi
  
  # Test 2: External API integrations
  if [[ -n "${STRIPE_SECRET_KEY:-}" ]]; then
    local stripe_status
    stripe_status=$(curl -s -o /dev/null -w "%{http_code}" \
      -H "Authorization: Bearer $STRIPE_SECRET_KEY" \
      "https://api.stripe.com/v1/account" 2>/dev/null || echo "000")
    
    if [[ "$stripe_status" == "200" ]]; then
      success "Integration: Stripe API OK"
    else
      error "Integration: Stripe API failed (HTTP $stripe_status)"
    fi
  else
    warning "Integration: Stripe not configured"
  fi
  
  if [[ -n "${PINECONE_API_KEY:-}" ]]; then
    local pinecone_status
    pinecone_status=$(curl -s -o /dev/null -w "%{http_code}" \
      -H "Api-Key: $PINECONE_API_KEY" \
      "https://controller.${PINECONE_ENVIRONMENT:-us-west1-gcp}.pinecone.io/databases" 2>/dev/null || echo "000")
    
    if [[ "$pinecone_status" == "200" ]]; then
      success "Integration: Pinecone API OK"
    else
      error "Integration: Pinecone API failed (HTTP $pinecone_status)"
    fi
  else
    warning "Integration: Pinecone not configured"
  fi
  
  return 0
}

# Generate test report
generate_test_report() {
  local timestamp_report
  timestamp_report=$(timestamp)
  
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🧪 Service-Specific Test Report - $timestamp_report"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "📊 Summary:"
  echo "  ✅ Passed: ${#PASSED_TESTS[@]}"
  echo "  ❌ Failed: ${#FAILED_TESTS[@]}"
  echo "  ⚠️  Skipped: ${#SKIPPED_TESTS[@]}"
  echo ""
  
  # Overall status
  if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
    success "🎉 All tests passed!"
  else
    error "🚨 ${#FAILED_TESTS[@]} test(s) failed!"
  fi
  
  echo ""
  
  # Detailed results
  if [ ${#PASSED_TESTS[@]} -gt 0 ]; then
    echo "✅ Passed Tests:"
    for test in "${PASSED_TESTS[@]}"; do
      echo "  • $test"
    done
    echo ""
  fi
  
  if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
    echo "❌ Failed Tests:"
    for test in "${FAILED_TESTS[@]}"; do
      echo "  • $test"
    done
    echo ""
  fi
  
  if [ ${#SKIPPED_TESTS[@]} -gt 0 ]; then
    echo "⚠️  Skipped Tests:"
    for test in "${SKIPPED_TESTS[@]}"; do
      echo "  • $test"
    done
    echo ""
  fi
  
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Save test results
save_test_results() {
  local results_dir="$PROJECT_ROOT/.test-results"
  mkdir -p "$results_dir"
  
  local results_file="$results_dir/service-tests-$(date +"%Y%m%d_%H%M%S").json"
  
  cat > "$results_file" <<EOF
{
  "timestamp": "$(timestamp)",
  "service": "$SERVICE",
  "environment": "$ENVIRONMENT",
  "summary": {
    "passed": ${#PASSED_TESTS[@]},
    "failed": ${#FAILED_TESTS[@]},
    "skipped": ${#SKIPPED_TESTS[@]}
  },
  "passed_tests": [$(printf '"%s",' "${PASSED_TESTS[@]}" | sed 's/,$//')],
  "failed_tests": [$(printf '"%s",' "${FAILED_TESTS[@]}" | sed 's/,$//')],
  "skipped_tests": [$(printf '"%s",' "${SKIPPED_TESTS[@]}" | sed 's/,$//')]
}
EOF
  
  info "Test results saved to: $results_file"
}

# Show usage
show_usage() {
  cat << EOF
Usage: $0 [service] [environment] [verbose]

Service:
  postgresql, redis, mongodb, neo4j, api, frontend, integration, all (default: all)

Environment:
  development, staging, production (default: development)

Verbose:
  true, false (default: false)

Examples:
  $0                          # Test all services in development
  $0 postgresql production    # Test PostgreSQL in production
  $0 api staging true         # Test API in staging with verbose output
  $0 integration              # Test integrations only

EOF
}

# Main execution
main() {
  SERVICE="${1:-all}"
  ENVIRONMENT="${2:-development}"
  VERBOSE="${3:-false}"
  
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🧪 Service-Specific Test Suite"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  info "Service: $SERVICE"
  info "Environment: $ENVIRONMENT"
  info "Verbose: $VERBOSE"
  echo ""
  
  # Check dependencies
  if ! check_dependencies; then
    exit 1
  fi
  
  # Load environment variables
  load_env_vars
  
  # Run tests based on service
  case "$SERVICE" in
    "postgresql")
      test_postgresql
      ;;
    "redis")
      test_redis
      ;;
    "mongodb")
      test_mongodb
      ;;
    "neo4j")
      test_neo4j
      ;;
    "api")
      test_api_service
      ;;
    "frontend")
      test_frontend_service
      ;;
    "integration")
      test_integrations
      ;;
    "all")
      test_postgresql
      test_redis
      test_mongodb
      test_neo4j
      test_api_service
      test_frontend_service
      test_integrations
      ;;
    *)
      error "Unknown service: $SERVICE"
      show_usage
      exit 1
      ;;
  esac
  
  # Generate report
  generate_test_report
  save_test_results
  
  # Exit with appropriate code
  if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
    exit 1
  elif [ ${#SKIPPED_TESTS[@]} -gt 0 ]; then
    exit 2
  else
    exit 0
  fi
}

# Run main function
main "$@"
