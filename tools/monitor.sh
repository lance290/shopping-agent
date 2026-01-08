#!/bin/bash

# 📊 Monitoring & Observability Script
# Comprehensive monitoring for development and production environments

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
MONITOR_DIR="$PROJECT_ROOT/.monitoring"
LOG_FILE="$MONITOR_DIR/monitor.log"
METRICS_FILE="$MONITOR_DIR/metrics.json"

# Create monitoring directory
mkdir -p "$MONITOR_DIR"

# Unicode symbols
SYMBOL_CHECK="✅"
SYMBOL_CROSS="❌"
SYMBOL_WARNING="⚠️"
SYMBOL_INFO="ℹ️"
SYMBOL_MONITOR="📊"
SYMBOL_ALERT="🚨"
SYMBOL_CHART="📈"
SYMBOL_HEART="💚"
SYMBOL_DATABASE="🗄️"
SYMBOL_CLOUD="☁️"
SYMBOL_TRAIN="🚂"

# Logging functions
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

save_metric() {
    local metric=$1
    local value=$2
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    echo "{\"timestamp\":\"$timestamp\",\"metric\":\"$metric\",\"value\":\"$value\"}" >> "$METRICS_FILE.tmp"
}

# Colored output functions
print_header() {
    echo -e "${PURPLE}${SYMBOL_MONITOR} $1${NC}"
}

print_section() {
    echo -e "${CYAN}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}${SYMBOL_CHECK} $1${NC}"
}

print_error() {
    echo -e "${RED}${SYMBOL_CROSS} $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}${SYMBOL_WARNING} $1${NC}"
}

print_info() {
    echo -e "${BLUE}${SYMBOL_INFO} $1${NC}"
}

print_alert() {
    echo -e "${RED}${SYMBOL_ALERT} $1${NC}"
}

print_metric() {
    local label=$1
    local value=$2
    local status=${3:-"normal"}
    
    case $status in
        "good") echo -e "  ${GREEN}${SYMBOL_CHECK}${NC} $label: ${GREEN}$value${NC}" ;;
        "warning") echo -e "  ${YELLOW}${SYMBOL_WARNING}${NC} $label: ${YELLOW}$value${NC}" ;;
        "critical") echo -e "  ${RED}${SYMBOL_CROSS}${NC} $label: ${RED}$value${NC}" ;;
        *) echo -e "  ${WHITE}$label:${NC} $value" ;;
    esac
}

# Draw separator
draw_separator() {
    echo -e "${GRAY}─────────────────────────────────────────────────────────────────${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Get system metrics
get_system_metrics() {
    print_section "System Metrics"
    draw_separator
    
    # CPU usage
    local cpu_usage=0
    if command_exists top; then
        cpu_usage=$(top -l 1 -n 0 | grep "CPU usage" | awk '{print $3}' | sed 's/%//' || echo "0")
    fi
    
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        print_metric "CPU Usage" "${cpu_usage}%" "critical"
        save_metric "cpu_usage" "$cpu_usage"
    elif (( $(echo "$cpu_usage > 60" | bc -l) )); then
        print_metric "CPU Usage" "${cpu_usage}%" "warning"
        save_metric "cpu_usage" "$cpu_usage"
    else
        print_metric "CPU Usage" "${cpu_usage}%" "good"
        save_metric "cpu_usage" "$cpu_usage"
    fi
    
    # Memory usage
    local memory_usage=0
    local free_memory=0
    if command_exists vm_stat; then
        local page_size=$(vm_stat | head -1 | sed 's/.*page size of \([0-9]*\).*/\1/')
        local free_pages=$(vm_stat | grep "Pages free" | awk '{print $3}' | sed 's/\.//')
        local inactive_pages=$(vm_stat | grep "Pages inactive" | awk '{print $3}' | sed 's/\.//' || echo "0")
        local active_pages=$(vm_stat | grep "Pages active" | awk '{print $3}' | sed 's/\.//' || echo "0")
        local wired_pages=$(vm_stat | grep "Pages wired down" | awk '{print $4}' | sed 's/\.//' || echo "0")
        
        local total_pages=$((free_pages + inactive_pages + active_pages + wired_pages))
        local used_pages=$((active_pages + wired_pages))
        
        if [[ $total_pages -gt 0 ]]; then
            memory_usage=$((used_pages * 100 / total_pages))
            free_memory=$((free_pages * page_size / 1024 / 1024))
        fi
    fi
    
    if (( memory_usage > 85 )); then
        print_metric "Memory Usage" "${memory_usage}%" "critical"
        save_metric "memory_usage" "$memory_usage"
    elif (( memory_usage > 70 )); then
        print_metric "Memory Usage" "${memory_usage}%" "warning"
        save_metric "memory_usage" "$memory_usage"
    else
        print_metric "Memory Usage" "${memory_usage}%" "good"
        save_metric "memory_usage" "$memory_usage"
    fi
    
    print_metric "Free Memory" "${free_memory}MB"
    save_metric "free_memory_mb" "$free_memory"
    
    # Disk usage
    local disk_usage=0
    if command_exists df; then
        disk_usage=$(df -h "$PROJECT_ROOT" | awk 'NR==2 {print $5}' | sed 's/%//')
    fi
    
    if (( disk_usage > 90 )); then
        print_metric "Disk Usage" "${disk_usage}%" "critical"
        save_metric "disk_usage" "$disk_usage"
    elif (( disk_usage > 80 )); then
        print_metric "Disk Usage" "${disk_usage}%" "warning"
        save_metric "disk_usage" "$disk_usage"
    else
        print_metric "Disk Usage" "${disk_usage}%" "good"
        save_metric "disk_usage" "$disk_usage"
    fi
    
    # Load average
    if command_exists uptime; then
        local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
        print_metric "Load Average" "$load_avg"
        save_metric "load_average" "$load_avg"
    fi
    
    echo ""
}

# Get application metrics
get_application_metrics() {
    print_section "Application Metrics"
    draw_separator
    
    # Node.js processes
    if command_exists node; then
        local node_processes=$(pgrep -f node | wc -l)
        print_metric "Node.js Processes" "$node_processes"
        save_metric "node_processes" "$node_processes"
        
        # Check for memory leaks in Node processes
        while read -r pid; do
            if [[ -n "$pid" ]]; then
                local memory=$(ps -p "$pid" -o rss= | awk '{print int($1/1024)"MB"}')
                print_metric "Node Process $pid" "$memory"
                save_metric "node_process_${pid}_memory" "$memory"
            fi
        done < <(pgrep -f node)
    fi
    
    # Port usage
    local common_ports=(8080 3000 4000 5000 8000 9000)
    for port in "${common_ports[@]}"; do
        if lsof -i :$port &>/dev/null; then
            local process=$(lsof -i :$port | awk 'NR==2 {print $1}')
            print_metric "Port $port" "$process"
            save_metric "port_${port}_process" "$process"
        fi
    done
    
    # Application logs
    local log_errors=0
    local log_warnings=0
    
    if [[ -d "$PROJECT_ROOT/.logs" ]]; then
        log_errors=$(find "$PROJECT_ROOT/.logs" -name "*.log" -exec grep -l "ERROR" {} \; 2>/dev/null | wc -l)
        log_warnings=$(find "$PROJECT_ROOT/.logs" -name "*.log" -exec grep -l "WARNING" {} \; 2>/dev/null | wc -l)
    fi
    
    print_metric "Log Errors" "$log_errors"
    save_metric "log_errors" "$log_errors"
    print_metric "Log Warnings" "$log_warnings"
    save_metric "log_warnings" "$log_warnings"
    
    echo ""
}

# Get database metrics
get_database_metrics() {
    print_section "${SYMBOL_DATABASE} Database Metrics"
    draw_separator
    
    # PostgreSQL
    if command_exists psql; then
        local pg_status="disconnected"
        local pg_connections=0
        local pg_db_size=0
        
        if PGPASSWORD=postgres psql -h localhost -U postgres -d monorepo_dev -c "SELECT 1;" &>/dev/null; then
            pg_status="connected"
            pg_connections=$(PGPASSWORD=postgres psql -h localhost -U postgres -d monorepo_dev -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs || echo "0")
            pg_db_size=$(PGPASSWORD=postgres psql -h localhost -U postgres -d monorepo_dev -t -c "SELECT pg_size_pretty(pg_database_size('monorepo_dev'));" 2>/dev/null | xargs || echo "0")
        fi
        
        if [[ "$pg_status" == "connected" ]]; then
            print_metric "PostgreSQL" "$pg_status" "good"
            print_metric "PG Connections" "$pg_connections"
            print_metric "PG DB Size" "$pg_db_size"
        else
            print_metric "PostgreSQL" "$pg_status" "critical"
        fi
        
        save_metric "postgresql_status" "$pg_status"
        save_metric "postgresql_connections" "$pg_connections"
    fi
    
    # Redis
    if command_exists redis-cli; then
        local redis_status="disconnected"
        local redis_memory=0
        local redis_connections=0
        
        if redis-cli -h localhost ping | grep -q PONG; then
            redis_status="connected"
            redis_memory=$(redis-cli -h localhost info memory | grep "used_memory_human" | cut -d':' -f2 | tr -d '\r' || echo "0")
            redis_connections=$(redis-cli -h localhost info clients | grep "connected_clients" | cut -d':' -f2 | tr -d '\r' || echo "0")
        fi
        
        if [[ "$redis_status" == "connected" ]]; then
            print_metric "Redis" "$redis_status" "good"
            print_metric "Redis Memory" "$redis_memory"
            print_metric "Redis Connections" "$redis_connections"
        else
            print_metric "Redis" "$redis_status" "critical"
        fi
        
        save_metric "redis_status" "$redis_status"
        save_metric "redis_memory" "$redis_memory"
    fi
    
    # MongoDB
    if command_exists mongosh; then
        local mongo_status="disconnected"
        local mongo_db_size=0
        
        if mongosh mongodb://admin:password@localhost:27017/monorepo_dev --eval "db.runCommand('ping')" &>/dev/null; then
            mongo_status="connected"
            mongo_db_size=$(mongosh mongodb://admin:password@localhost:27017/monorepo_dev --eval "db.stats().storageSize" --quiet 2>/dev/null | xargs || echo "0")
        fi
        
        if [[ "$mongo_status" == "connected" ]]; then
            print_metric "MongoDB" "$mongo_status" "good"
            print_metric "MongoDB Size" "${mongo_db_size} bytes"
        else
            print_metric "MongoDB" "$mongo_status" "critical"
        fi
        
        save_metric "mongodb_status" "$mongo_status"
    fi
    
    echo ""
}

# Get deployment metrics
get_deployment_metrics() {
    print_section "Deployment Metrics"
    draw_separator
    
    # Railway metrics
    if command_exists railway; then
        local railway_status="not_authenticated"
        local railway_services=0
        local railway_running=0
        
        if railway whoami &>/dev/null; then
            railway_status="authenticated"
            if railway status &>/dev/null; then
                railway_services=$(railway status --json 2>/dev/null | jq length 2>/dev/null || echo "0")
                railway_running=$(railway status --json 2>/dev/null | jq '.[] | select(.status == "running") | .name' 2>/dev/null | wc -l || echo "0")
            fi
        fi
        
        if [[ "$railway_status" == "authenticated" ]]; then
            print_metric "Railway" "$railway_status" "good"
            print_metric "Railway Services" "$railway_services"
            print_metric "Railway Running" "$railway_running"
        else
            print_metric "Railway" "$railway_status" "warning"
        fi
        
        save_metric "railway_status" "$railway_status"
        save_metric "railway_services" "$railway_services"
    fi
    
    # GCP metrics
    if command_exists gcloud; then
        local gcp_status="not_authenticated"
        local gcp_services=0
        local gcp_running=0
        
        if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
            gcp_status="authenticated"
            local project=$(gcloud config get-value project 2>/dev/null || echo "not_set")
            if [[ "$project" != "not_set" ]]; then
                gcp_services=$(gcloud run services list --format="value(name)" 2>/dev/null | wc -l || echo "0")
                gcp_running=$(gcloud run services list --filter="status=RUNNING" --format="value(name)" 2>/dev/null | wc -l || echo "0")
            fi
        fi
        
        if [[ "$gcp_status" == "authenticated" ]]; then
            print_metric "GCP" "$gcp_status" "good"
            print_metric "GCP Services" "$gcp_services"
            print_metric "GCP Running" "$gcp_running"
        else
            print_metric "GCP" "$gcp_status" "warning"
        fi
        
        save_metric "gcp_status" "$gcp_status"
        save_metric "gcp_services" "$gcp_services"
    fi
    
    echo ""
}

# Get security metrics
get_security_metrics() {
    print_section "Security Metrics"
    draw_separator
    
    # Check for exposed secrets
    local exposed_secrets=0
    local secret_patterns=("sk_test\|sk_live" "password\|secret" "api_key\|apikey" "token")
    
    for pattern in "${secret_patterns[@]}"; do
        local count=$(grep -r -i "$pattern" --include="*.js" --include="*.ts" --include="*.json" --exclude-dir=node_modules --exclude-dir=.git "$PROJECT_ROOT" 2>/dev/null | wc -l || echo "0")
        exposed_secrets=$((exposed_secrets + count))
    done
    
    if (( exposed_secrets > 0 )); then
        print_metric "Exposed Secrets" "$exposed_secrets" "warning"
    else
        print_metric "Exposed Secrets" "$exposed_secrets" "good"
    fi
    
    save_metric "exposed_secrets" "$exposed_secrets"
    
    # Check for vulnerable dependencies
    local vulnerabilities=0
    if [[ -f "$PROJECT_ROOT/package.json" ]]; then
        cd "$PROJECT_ROOT"
        vulnerabilities=$(npm audit --json 2>/dev/null | jq '.vulnerabilities | keys | length' 2>/dev/null || echo "0")
    fi
    
    if (( vulnerabilities > 10 )); then
        print_metric "Vulnerabilities" "$vulnerabilities" "critical"
    elif (( vulnerabilities > 0 )); then
        print_metric "Vulnerabilities" "$vulnerabilities" "warning"
    else
        print_metric "Vulnerabilities" "$vulnerabilities" "good"
    fi
    
    save_metric "vulnerabilities" "$vulnerabilities"
    
    # Check git security
    local git_security_issues=0
    if git rev-parse --git-dir &> /dev/null; then
        # Check for sensitive files in git
        if git ls-files | grep -E "\.(key|pem|p12)$" &>/dev/null; then
            ((git_security_issues++))
        fi
        
        # Check for .env files in git
        if git ls-files | grep -E "\.env" &>/dev/null; then
            ((git_security_issues++))
        fi
    fi
    
    if (( git_security_issues > 0 )); then
        print_metric "Git Security Issues" "$git_security_issues" "critical"
    else
        print_metric "Git Security Issues" "$git_security_issues" "good"
    fi
    
    save_metric "git_security_issues" "$git_security_issues"
    
    echo ""
}

# Get performance metrics
get_performance_metrics() {
    print_section "Performance Metrics"
    draw_separator
    
    # Response time testing
    local response_times=()
    local test_urls=("http://localhost:8080/health" "http://localhost:3000" "http://localhost:4000")
    
    for url in "${test_urls[@]}"; do
        local response_time=$(curl -o /dev/null -s -w '%{time_total}' "$url" 2>/dev/null || echo "0")
        local response_ms=$(echo "$response_time * 1000" | bc 2>/dev/null || echo "0")
        
        if (( $(echo "$response_ms > 0" | bc -l) )); then
            if (( $(echo "$response_ms > 5000" | bc -l) )); then
                print_metric "$url" "${response_ms}ms" "critical"
            elif (( $(echo "$response_ms > 2000" | bc -l) )); then
                print_metric "$url" "${response_ms}ms" "warning"
            else
                print_metric "$url" "${response_ms}ms" "good"
            fi
            save_metric "response_time_${url//[^a-zA-Z0-9]/_}" "$response_ms"
        else
            print_metric "$url" "no response" "warning"
        fi
    done
    
    # Database query performance
    if command_exists psql; then
        local slow_queries=0
        if PGPASSWORD=postgres psql -h localhost -U postgres -d monorepo_dev -c "SELECT 1;" &>/dev/null; then
            slow_queries=$(PGPASSWORD=postgres psql -h localhost -U postgres -d monorepo_dev -t -c "SELECT count(*) FROM pg_stat_statements WHERE mean_time > 1000;" 2>/dev/null | xargs || echo "0")
        fi
        
        if (( slow_queries > 10 )); then
            print_metric "Slow Queries" "$slow_queries" "critical"
        elif (( slow_queries > 0 )); then
            print_metric "Slow Queries" "$slow_queries" "warning"
        else
            print_metric "Slow Queries" "$slow_queries" "good"
        fi
        
        save_metric "slow_queries" "$slow_queries"
    fi
    
    echo ""
}

# Generate alerts
generate_alerts() {
    print_section "Active Alerts"
    draw_separator
    
    local alerts=0
    
    # Check for critical issues
    if [[ -f "$METRICS_FILE" ]]; then
        # Check CPU usage
        local cpu_usage=$(tail -10 "$METRICS_FILE" | jq -r 'select(.metric == "cpu_usage") | .value' | tail -1 || echo "0")
        if (( $(echo "$cpu_usage > 80" | bc -l) )); then
            print_alert "High CPU usage: ${cpu_usage}%"
            ((alerts++))
        fi
        
        # Check memory usage
        local memory_usage=$(tail -10 "$METRICS_FILE" | jq -r 'select(.metric == "memory_usage") | .value' | tail -1 || echo "0")
        if (( memory_usage > 85 )); then
            print_alert "High memory usage: ${memory_usage}%"
            ((alerts++))
        fi
        
        # Check disk usage
        local disk_usage=$(tail -10 "$METRICS_FILE" | jq -r 'select(.metric == "disk_usage") | .value' | tail -1 || echo "0")
        if (( disk_usage > 90 )); then
            print_alert "High disk usage: ${disk_usage}%"
            ((alerts++))
        fi
        
        # Check database status
        local pg_status=$(tail -10 "$METRICS_FILE" | jq -r 'select(.metric == "postgresql_status") | .value' | tail -1 || echo "unknown")
        if [[ "$pg_status" == "disconnected" ]]; then
            print_alert "PostgreSQL database disconnected"
            ((alerts++))
        fi
        
        local redis_status=$(tail -10 "$METRICS_FILE" | jq -r 'select(.metric == "redis_status") | .value' | tail -1 || echo "unknown")
        if [[ "$redis_status" == "disconnected" ]]; then
            print_alert "Redis database disconnected"
            ((alerts++))
        fi
        
        # Check security issues
        local vulnerabilities=$(tail -10 "$METRICS_FILE" | jq -r 'select(.metric == "vulnerabilities") | .value' | tail -1 || echo "0")
        if (( vulnerabilities > 10 )); then
            print_alert "High number of security vulnerabilities: $vulnerabilities"
            ((alerts++))
        fi
    fi
    
    if (( alerts == 0 )); then
        print_success "No active alerts"
    else
        print_warning "$alerts active alerts detected"
    fi
    
    echo ""
}

# Save metrics to file
save_metrics() {
    # Combine temporary metrics file
    if [[ -f "$METRICS_FILE.tmp" ]]; then
        cat "$METRICS_FILE.tmp" >> "$METRICS_FILE"
        rm "$METRICS_FILE.tmp"
    fi
    
    # Keep only last 1000 entries
    if [[ -f "$METRICS_FILE" ]]; then
        tail -1000 "$METRICS_FILE" > "$METRICS_FILE.tmp" && mv "$METRICS_FILE.tmp" "$METRICS_FILE"
    fi
}

# Generate monitoring report
generate_report() {
    print_header "Monitoring Report"
    
    echo ""
    echo -e "${CYAN}📊 Monitoring Summary${NC}"
    echo ""
    
    # Overall health score
    local total_checks=0
    local passed_checks=0
    
    # Count metrics from recent entries
    if [[ -f "$METRICS_FILE" ]]; then
        local recent_metrics=$(tail -50 "$METRICS_FILE")
        
        # System health
        local cpu_usage=$(echo "$recent_metrics" | jq -r 'select(.metric == "cpu_usage") | .value' | tail -1 || echo "0")
        local memory_usage=$(echo "$recent_metrics" | jq -r 'select(.metric == "memory_usage") | .value' | tail -1 || echo "0")
        local disk_usage=$(echo "$recent_metrics" | jq -r 'select(.metric == "disk_usage") | .value' | tail -1 || echo "0")
        
        ((total_checks++))
        if (( $(echo "$cpu_usage < 80" | bc -l) )); then ((passed_checks++)); fi
        
        ((total_checks++))
        if (( memory_usage < 85 )); then ((passed_checks++)); fi
        
        ((total_checks++))
        if (( disk_usage < 90 )); then ((passed_checks++)); fi
        
        # Database health
        local pg_status=$(echo "$recent_metrics" | jq -r 'select(.metric == "postgresql_status") | .value' | tail -1 || echo "disconnected")
        local redis_status=$(echo "$recent_metrics" | jq -r 'select(.metric == "redis_status") | .value' | tail -1 || echo "disconnected")
        
        ((total_checks++))
        if [[ "$pg_status" == "connected" ]]; then ((passed_checks++)); fi
        
        ((total_checks++))
        if [[ "$redis_status" == "connected" ]]; then ((passed_checks++)); fi
        
        # Security health
        local vulnerabilities=$(echo "$recent_metrics" | jq -r 'select(.metric == "vulnerabilities") | .value' | tail -1 || echo "0")
        
        ((total_checks++))
        if (( vulnerabilities < 10 )); then ((passed_checks++)); fi
    fi
    
    # Calculate health score
    local health_score=0
    if [[ $total_checks -gt 0 ]]; then
        health_score=$((passed_checks * 100 / total_checks))
    fi
    
    echo -e "${WHITE}Health Score:${NC} "
    if (( health_score >= 90 )); then
        echo -e "${GREEN}$health_score%${NC} ${GREEN}Excellent${NC}"
    elif (( health_score >= 75 )); then
        echo -e "${YELLOW}$health_score%${NC} ${YELLOW}Good${NC}"
    elif (( health_score >= 50 )); then
        echo -e "${YELLOW}$health_score%${NC} ${YELLOW}Fair${NC}"
    else
        echo -e "${RED}$health_score%${NC} ${RED}Poor${NC}"
    fi
    
    echo ""
    echo -e "${WHITE}Checks Passed:${NC} $passed_checks/$total_checks"
    echo -e "${WHITE}Last Updated:${NC} $(date)"
    echo -e "${WHITE}Metrics File:${NC} $METRICS_FILE"
    echo -e "${WHITE}Log File:${NC} $LOG_FILE"
    echo ""
    
    # Recommendations
    echo -e "${BLUE}Recommendations:${NC}"
    
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        echo "  ⚠️  Consider scaling up or optimizing CPU usage"
    fi
    
    if (( memory_usage > 85 )); then
        echo "  ⚠️  Monitor memory usage and consider optimization"
    fi
    
    if (( disk_usage > 90 )); then
        echo "  ⚠️  Clean up disk space or expand storage"
    fi
    
    if [[ "$pg_status" == "disconnected" ]]; then
        echo "  ⚠️  Check PostgreSQL database connection"
    fi
    
    if [[ "$redis_status" == "disconnected" ]]; then
        echo "  ⚠️  Check Redis database connection"
    fi
    
    if (( vulnerabilities > 10 )); then
        echo "  ⚠️  Update dependencies to fix security vulnerabilities"
    fi
    
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  • Set up automated monitoring alerts"
    echo "  • Configure log aggregation and analysis"
    echo "  • Implement performance baseline tracking"
    echo "  • Set up automated remediation for common issues"
    echo ""
    
    success "Monitoring complete!"
}

# Main function
main() {
    echo -e "${PURPLE}"
    echo "📊 Monitoring & Observability"
    echo "============================="
    echo -e "${NC}"
    
    get_system_metrics
    get_application_metrics
    get_database_metrics
    get_deployment_metrics
    get_security_metrics
    get_performance_metrics
    generate_alerts
    save_metrics
    generate_report
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --watch, -w    Watch mode (monitor every 60 seconds)"
        echo "  --section, -s  Monitor specific section only"
        echo "  --report, -r   Generate report only"
        echo ""
        echo "Available sections:"
        echo "  system, app, database, deploy, security, perf, alerts"
        exit 0
        ;;
    --watch|-w)
        while true; do
            clear
            main
            echo -e "${BLUE}Monitoring... (Press Ctrl+C to stop)${NC}"
            sleep 60
        done
        ;;
    --section|-s)
        section="${2:-}"
        case "$section" in
            "system") get_system_metrics ;;
            "app") get_application_metrics ;;
            "database") get_database_metrics ;;
            "deploy") get_deployment_metrics ;;
            "security") get_security_metrics ;;
            "perf") get_performance_metrics ;;
            "alerts") generate_alerts ;;
            *)
                echo "Unknown section: $section"
                echo "Available: system, app, database, deploy, security, perf, alerts"
                exit 1
                ;;
        esac
        ;;
    --report|-r)
        generate_report
        ;;
    "")
        main
        ;;
    *)
        echo "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
