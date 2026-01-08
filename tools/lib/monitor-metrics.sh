#!/usr/bin/env bash

# Monitoring and metrics utilities
# Source this file after common.sh

# Prevent double-sourcing
[[ -n "${_TOOLS_LIB_MONITOR_LOADED:-}" ]] && return 0
_TOOLS_LIB_MONITOR_LOADED=1

# Get system metrics
get_system_metrics() {
    print_section "System Metrics"
    draw_separator
    
    # CPU usage (macOS)
    local cpu_usage=0
    if command_exists top; then
        cpu_usage=$(top -l 1 -n 0 2>/dev/null | grep "CPU usage" | awk '{print $3}' | sed 's/%//' || echo "0")
    fi
    
    if (( $(echo "$cpu_usage > 80" | bc -l 2>/dev/null || echo 0) )); then
        print_metric "CPU Usage" "${cpu_usage}%" "critical"
    elif (( $(echo "$cpu_usage > 60" | bc -l 2>/dev/null || echo 0) )); then
        print_metric "CPU Usage" "${cpu_usage}%" "warning"
    else
        print_metric "CPU Usage" "${cpu_usage}%" "good"
    fi
    
    # Memory usage (macOS)
    local memory_usage=0
    if command_exists vm_stat; then
        local page_size free_pages active_pages wired_pages
        page_size=$(vm_stat 2>/dev/null | head -1 | sed 's/.*page size of \([0-9]*\).*/\1/' || echo "4096")
        free_pages=$(vm_stat 2>/dev/null | grep "Pages free" | awk '{print $3}' | sed 's/\.//' || echo "0")
        active_pages=$(vm_stat 2>/dev/null | grep "Pages active" | awk '{print $3}' | sed 's/\.//' || echo "0")
        wired_pages=$(vm_stat 2>/dev/null | grep "Pages wired down" | awk '{print $4}' | sed 's/\.//' || echo "0")
        
        local total_pages=$((free_pages + active_pages + wired_pages))
        local used_pages=$((active_pages + wired_pages))
        
        if [[ $total_pages -gt 0 ]]; then
            memory_usage=$((used_pages * 100 / total_pages))
        fi
    fi
    
    if (( memory_usage > 85 )); then
        print_metric "Memory Usage" "${memory_usage}%" "critical"
    elif (( memory_usage > 70 )); then
        print_metric "Memory Usage" "${memory_usage}%" "warning"
    else
        print_metric "Memory Usage" "${memory_usage}%" "good"
    fi
    
    # Disk usage
    local disk_usage=0
    if command_exists df; then
        disk_usage=$(df -h "${PROJECT_ROOT:-.}" 2>/dev/null | awk 'NR==2 {print $5}' | sed 's/%//' || echo "0")
    fi
    
    if (( disk_usage > 90 )); then
        print_metric "Disk Usage" "${disk_usage}%" "critical"
    elif (( disk_usage > 80 )); then
        print_metric "Disk Usage" "${disk_usage}%" "warning"
    else
        print_metric "Disk Usage" "${disk_usage}%" "good"
    fi
    
    echo ""
}

# Get application metrics
get_application_metrics() {
    print_section "Application Metrics"
    draw_separator
    
    # Node.js processes
    if command_exists node; then
        local node_processes
        node_processes=$(pgrep -f node 2>/dev/null | wc -l || echo "0")
        print_metric "Node.js Processes" "$node_processes"
    fi
    
    # Port usage
    local common_ports=(8080 3000 4000 5000)
    for port in "${common_ports[@]}"; do
        if lsof -i :"$port" &>/dev/null; then
            local process
            process=$(lsof -i :"$port" 2>/dev/null | awk 'NR==2 {print $1}' || echo "unknown")
            print_metric "Port $port" "$process"
        fi
    done
    
    echo ""
}

# Get deployment metrics
get_deployment_metrics() {
    print_section "Deployment Metrics"
    draw_separator
    
    # Railway metrics
    if command_exists railway; then
        if railway whoami &>/dev/null; then
            print_metric "Railway" "authenticated" "good"
        else
            print_metric "Railway" "not authenticated" "warning"
        fi
    fi
    
    # GCP metrics
    if command_exists gcloud; then
        if gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q .; then
            print_metric "GCP" "authenticated" "good"
        else
            print_metric "GCP" "not authenticated" "warning"
        fi
    fi
    
    echo ""
}

# Get security metrics
get_security_metrics() {
    print_section "Security Metrics"
    draw_separator
    
    local exposed_secrets=0
    local secret_patterns=("sk_test\|sk_live" "password\|secret" "api_key\|apikey")
    
    for pattern in "${secret_patterns[@]}"; do
        local count
        count=$(grep -r -i "$pattern" --include="*.js" --include="*.ts" --include="*.json" \
            --exclude-dir=node_modules --exclude-dir=.git "${PROJECT_ROOT:-.}" 2>/dev/null | wc -l || echo "0")
        exposed_secrets=$((exposed_secrets + count))
    done
    
    if (( exposed_secrets > 0 )); then
        print_metric "Potential Secrets" "$exposed_secrets" "warning"
    else
        print_metric "Potential Secrets" "$exposed_secrets" "good"
    fi
    
    # Vulnerabilities
    local vulnerabilities=0
    if [[ -f "${PROJECT_ROOT:-.}/package.json" ]]; then
        vulnerabilities=$(npm audit --json 2>/dev/null | jq '.vulnerabilities | keys | length' 2>/dev/null || echo "0")
    fi
    
    if (( vulnerabilities > 10 )); then
        print_metric "Vulnerabilities" "$vulnerabilities" "critical"
    elif (( vulnerabilities > 0 )); then
        print_metric "Vulnerabilities" "$vulnerabilities" "warning"
    else
        print_metric "Vulnerabilities" "$vulnerabilities" "good"
    fi
    
    echo ""
}
