#!/usr/bin/env bash

# Database testing and connection utilities
# Source this file after common.sh

# Prevent double-sourcing
[[ -n "${_TOOLS_LIB_DATABASE_LOADED:-}" ]] && return 0
_TOOLS_LIB_DATABASE_LOADED=1

# Test PostgreSQL connection
test_postgresql_connection() {
    local connection_string="${1:-$DATABASE_URL}"
    local service_name="${2:-PostgreSQL}"
    
    if [[ -z "$connection_string" ]]; then
        warning "$service_name: DATABASE_URL not configured"
        return 2
    fi
    
    if ! command_exists psql; then
        warning "$service_name: psql not available"
        return 2
    fi
    
    if PGPASSWORD="${connection_string#*://*:*@}" psql "$connection_string" -c "SELECT 1;" >/dev/null 2>&1; then
        success "$service_name: Connection OK"
        return 0
    else
        error "$service_name: Connection failed"
        return 1
    fi
}

# Test Redis connection
test_redis_connection() {
    local connection_string="${1:-$REDIS_URL}"
    local service_name="${2:-Redis}"
    
    if [[ -z "$connection_string" ]]; then
        warning "$service_name: REDIS_URL not configured"
        return 2
    fi
    
    if ! command_exists redis-cli; then
        warning "$service_name: redis-cli not available"
        return 2
    fi
    
    if redis-cli -u "$connection_string" ping 2>/dev/null | grep -q PONG; then
        success "$service_name: Connection OK"
        return 0
    else
        error "$service_name: Connection failed"
        return 1
    fi
}

# Test MongoDB connection
test_mongodb_connection() {
    local connection_string="${1:-$MONGODB_URI}"
    local service_name="${2:-MongoDB}"
    
    if [[ -z "$connection_string" ]]; then
        warning "$service_name: MONGODB_URI not configured"
        return 2
    fi
    
    if ! command_exists mongosh; then
        warning "$service_name: mongosh not available"
        return 2
    fi
    
    if mongosh "$connection_string" --eval "db.runCommand({ping: 1})" >/dev/null 2>&1; then
        success "$service_name: Connection OK"
        return 0
    else
        error "$service_name: Connection failed"
        return 1
    fi
}

# Test Neo4j connection
test_neo4j_connection() {
    local connection_string="${1:-$NEO4J_URI}"
    local service_name="${2:-Neo4j}"
    local user="${NEO4J_USER:-neo4j}"
    local password="${NEO4J_PASSWORD:-}"
    
    if [[ -z "$connection_string" ]]; then
        warning "$service_name: NEO4J_URI not configured"
        return 2
    fi
    
    if ! command_exists cypher-shell; then
        warning "$service_name: cypher-shell not available"
        return 2
    fi
    
    if cypher-shell -a "$connection_string" -u "$user" -p "$password" "RETURN 1;" >/dev/null 2>&1; then
        success "$service_name: Connection OK"
        return 0
    else
        error "$service_name: Connection failed"
        return 1
    fi
}

# Test all database connections
test_all_databases() {
    info "Testing database connections..."
    
    local results=()
    
    test_postgresql_connection && results+=("postgresql:ok") || results+=("postgresql:fail")
    test_redis_connection && results+=("redis:ok") || results+=("redis:fail")
    test_mongodb_connection && results+=("mongodb:ok") || results+=("mongodb:fail")
    test_neo4j_connection && results+=("neo4j:ok") || results+=("neo4j:fail")
    
    printf '%s\n' "${results[@]}"
}

# Get PostgreSQL stats
get_postgresql_stats() {
    local connection_string="${1:-$DATABASE_URL}"
    
    if [[ -z "$connection_string" ]] || ! command_exists psql; then
        return 1
    fi
    
    local connections db_size
    connections=$(PGPASSWORD="${connection_string#*://*:*@}" psql "$connection_string" -t -c \
        "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs || echo "0")
    db_size=$(PGPASSWORD="${connection_string#*://*:*@}" psql "$connection_string" -t -c \
        "SELECT pg_size_pretty(pg_database_size(current_database()));" 2>/dev/null | xargs || echo "0")
    
    echo "connections=$connections"
    echo "db_size=$db_size"
}

# Get Redis stats
get_redis_stats() {
    local connection_string="${1:-$REDIS_URL}"
    
    if [[ -z "$connection_string" ]] || ! command_exists redis-cli; then
        return 1
    fi
    
    local memory connections
    memory=$(redis-cli -u "$connection_string" info memory 2>/dev/null | grep "used_memory_human" | cut -d: -f2 | tr -d '\r' || echo "0")
    connections=$(redis-cli -u "$connection_string" info clients 2>/dev/null | grep "connected_clients" | cut -d: -f2 | tr -d '\r' || echo "0")
    
    echo "memory=$memory"
    echo "connections=$connections"
}
