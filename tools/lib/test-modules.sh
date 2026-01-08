#!/usr/bin/env bash

# Service test utilities
# Source this file after common.sh and database.sh

# Prevent double-sourcing
[[ -n "${_TOOLS_LIB_TESTS_LOADED:-}" ]] && return 0
_TOOLS_LIB_TESTS_LOADED=1

# Test results tracking
declare -ga PASSED_TESTS=()
declare -ga FAILED_TESTS=()
declare -ga SKIPPED_TESTS=()

# Reset test results
reset_test_results() {
    PASSED_TESTS=()
    FAILED_TESTS=()
    SKIPPED_TESTS=()
}

# Record test results
test_passed() { PASSED_TESTS+=("$*"); success "$*"; }
test_failed() { FAILED_TESTS+=("$*"); error "$*"; }
test_skipped() { SKIPPED_TESTS+=("$*"); warning "$*"; }

# PostgreSQL specific tests
test_postgresql_ops() {
    info "Running PostgreSQL specific tests..."
    
    if [[ -z "${DATABASE_URL:-}" ]]; then
        test_skipped "PostgreSQL: DATABASE_URL not configured"
        return 0
    fi
    
    if ! command_exists psql; then
        test_skipped "PostgreSQL: psql not available"
        return 0
    fi
    
    # Basic connection
    if ! PGPASSWORD="${DATABASE_URL#*://*:*@}" psql "$DATABASE_URL" -c "SELECT 1;" >/dev/null 2>&1; then
        test_failed "PostgreSQL: Basic connection failed"
        return 1
    fi
    test_passed "PostgreSQL: Basic connection OK"
    
    # Transaction support
    if PGPASSWORD="${DATABASE_URL#*://*:*@}" psql "$DATABASE_URL" -c "BEGIN; SELECT 1; ROLLBACK;" >/dev/null 2>&1; then
        test_passed "PostgreSQL: Transaction support OK"
    else
        test_failed "PostgreSQL: Transaction support failed"
    fi
    
    return 0
}

# Redis specific tests
test_redis_ops() {
    info "Running Redis specific tests..."
    
    if [[ -z "${REDIS_URL:-}" ]]; then
        test_skipped "Redis: REDIS_URL not configured"
        return 0
    fi
    
    if ! command_exists redis-cli; then
        test_skipped "Redis: redis-cli not available"
        return 0
    fi
    
    # Basic connection
    if ! redis-cli -u "$REDIS_URL" ping >/dev/null 2>&1; then
        test_failed "Redis: Basic connection failed"
        return 1
    fi
    test_passed "Redis: Basic connection OK"
    
    # Basic operations
    local test_key="test_key_$(date +%s)"
    if redis-cli -u "$REDIS_URL" set "$test_key" "test_value" >/dev/null 2>&1 && \
       redis-cli -u "$REDIS_URL" del "$test_key" >/dev/null 2>&1; then
        test_passed "Redis: Basic operations OK"
    else
        test_failed "Redis: Basic operations failed"
    fi
    
    return 0
}

# MongoDB specific tests
test_mongodb_ops() {
    info "Running MongoDB specific tests..."
    
    if [[ -z "${MONGODB_URI:-}" ]]; then
        test_skipped "MongoDB: MONGODB_URI not configured"
        return 0
    fi
    
    if ! command_exists mongosh; then
        test_skipped "MongoDB: mongosh not available"
        return 0
    fi
    
    # Basic connection
    if ! mongosh "$MONGODB_URI" --eval "db.runCommand({ping: 1})" >/dev/null 2>&1; then
        test_failed "MongoDB: Basic connection failed"
        return 1
    fi
    test_passed "MongoDB: Basic connection OK"
    
    return 0
}

# API service tests
test_api_service() {
    info "Running API service tests..."
    
    local base_url="${BACKEND_URL:-http://localhost:8080}"
    
    # Health endpoint
    local health_status
    health_status=$(curl -s -o /dev/null -w "%{http_code}" "$base_url/health" 2>/dev/null || echo "000")
    
    if [[ "$health_status" == "000" ]]; then
        test_skipped "API: Service not reachable at $base_url"
        return 1
    elif [[ "$health_status" == "200" ]]; then
        test_passed "API: Health endpoint OK"
    else
        test_failed "API: Health endpoint returned $health_status"
    fi
    
    return 0
}

# Frontend service tests
test_frontend_service() {
    info "Running frontend service tests..."
    
    local base_url="${FRONTEND_URL:-http://localhost:3000}"
    
    local main_status
    main_status=$(curl -s -o /dev/null -w "%{http_code}" "$base_url" 2>/dev/null || echo "000")
    
    if [[ "$main_status" == "000" ]]; then
        test_skipped "Frontend: Service not reachable at $base_url"
        return 1
    elif [[ "$main_status" == "200" ]]; then
        test_passed "Frontend: Main page OK"
    else
        test_failed "Frontend: Main page returned $main_status"
    fi
    
    return 0
}

# Generate test report
generate_test_report() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🧪 Service-Specific Test Report - $(timestamp)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📊 Summary:"
    echo "  ✅ Passed: ${#PASSED_TESTS[@]}"
    echo "  ❌ Failed: ${#FAILED_TESTS[@]}"
    echo "  ⚠️  Skipped: ${#SKIPPED_TESTS[@]}"
    echo ""
    
    if [[ ${#FAILED_TESTS[@]} -eq 0 ]]; then
        success "🎉 All tests passed!"
    else
        error "🚨 ${#FAILED_TESTS[@]} test(s) failed!"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Save test results
save_test_results() {
    local results_dir="${1:-${PROJECT_ROOT:-.}/.test-results}"
    mkdir -p "$results_dir"
    
    local results_file="$results_dir/service-tests-$(timestamp_file).json"
    
    cat > "$results_file" <<EOF
{
  "timestamp": "$(timestamp)",
  "summary": {
    "passed": ${#PASSED_TESTS[@]},
    "failed": ${#FAILED_TESTS[@]},
    "skipped": ${#SKIPPED_TESTS[@]}
  }
}
EOF
    
    info "Test results saved to: $results_file"
}
