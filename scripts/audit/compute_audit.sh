#!/bin/bash

# 💻 GOOGLE CLOUD COMPUTE AUDIT SCRIPT
# Comprehensive compute analysis for cost optimization and performance

set -euo pipefail

# Load project info
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/project_info.env" ]; then
    # Read and export variables safely
    while IFS='=' read -r key value; do
        # Skip empty lines and comments
        if [[ -n "$key" && ! "$key" =~ ^# ]]; then
            # Remove quotes from value
            value=$(echo "$value" | sed 's/^"//;s/"$//')
            export "$key=$value"
        fi
    done < "$SCRIPT_DIR/project_info.env"
else
    echo "❌ Project info not found. Run the main audit runner first."
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    echo -e "${BLUE}[Compute Audit]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to get regions
get_regions() {
    gcloud compute regions list --format="value(name)" | head -10
}

# Function to audit Cloud Run services
audit_cloud_run() {
    log "🚀 Auditing Cloud Run services..."
    
    local total_services=0
    local running_services=0
    local stopped_services=0
    local services_without_scaling=0
    local high_memory_services=0
    
    # Get regions
    local regions=$(get_regions)
    
    # Process each region
    while IFS= read -r region; do
        if [ -z "$region" ]; then
            continue
        fi
        
        log "Checking region: $region"
        
        # List Cloud Run services in this region
        local services=$(gcloud run services list --region="$region" --format="table(metadata.name,status.conditions[0].status,spec.template.spec.containers[0].resources.limits.memory,spec.template.metadata.annotations.autoscaling.knative.dev/minScale,spec.template.metadata.annotations.autoscaling.knative.dev/maxScale)" 2>/dev/null || echo "")
        
        if [ -z "$services" ]; then
            continue
        fi
        
        # Process each service (skip header)
        while IFS= read -r service_line; do
            if [ -z "$service_line" ] || echo "$service_line" | grep -q "NAME"; then
                continue
            fi
            
            total_services=$((total_services + 1))
            
            # Parse service information
            local name=$(echo "$service_line" | awk '{print $1}')
            local status=$(echo "$service_line" | awk '{print $2}')
            local memory=$(echo "$service_line" | awk '{print $3}')
            local min_scale=$(echo "$service_line" | awk '{print $4}')
            local max_scale=$(echo "$service_line" | awk '{print $5}')
            
            log "Analyzing service: $name in $region - $status"
            
            # Count by status
            if [ "$status" == "True" ]; then
                running_services=$((running_services + 1))
            else
                stopped_services=$((stopped_services + 1))
            fi
            
            # Check scaling configuration
            if [ "$min_scale" == "None" ] || [ "$max_scale" == "None" ]; then
                services_without_scaling=$((services_without_scaling + 1))
                log_warning "⚠️  Service without scaling config: $name"
            fi
            
            # Check memory allocation
            if [ "$memory" != "None" ] && [ -n "$memory" ]; then
                local memory_mb=$(echo "$memory" | sed 's/[^0-9]//g')
                if [ "$memory_mb" -gt 2048 ]; then
                    high_memory_services=$((high_memory_services + 1))
                    log_warning "⚠️  High memory service: $name (${memory}MB)"
                fi
            fi
            
            # Add service info to results
            jq --arg name "$name" \
               --arg region "$region" \
               --arg status "$status" \
               --arg memory "$memory" \
               --arg min_scale "$min_scale" \
               --arg max_scale "$max_scale" \
               '.cloud_run.services += [{"name": $name, "region": $region, "status": $status, "memory": $memory, "min_scale": $min_scale, "max_scale": $max_scale}]' \
               "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
            
        done <<< "$services"
        
    done <<< "$regions"
    
    # Update summary
    jq --arg total "$total_services" \
       --arg running "$running_services" \
       --arg stopped "$stopped_services" \
       --arg scaling "$services_without_scaling" \
       --arg memory "$high_memory_services" \
       '.summary.total_cloud_run_services = ($total | tonumber) |
        .summary.running_cloud_run_services = ($running | tonumber) |
        .summary.stopped_cloud_run_services = ($stopped | tonumber) |
        .summary.cloud_run_services_without_scaling = ($scaling | tonumber) |
        .summary.high_memory_cloud_run_services = ($memory | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    log_success "Cloud Run audit completed: $total_services services across all regions"
}

# Function to audit Compute Engine instances
audit_compute_instances() {
    log "🖥️ Auditing Compute Engine instances..."
    
    # List all instances
    local instances=$(gcloud compute instances list --format="table(name,status,zone,machineType,lastStartTimestamp,labels)" 2>/dev/null || echo "")
    
    if [ -z "$instances" ]; then
        log "No Compute Engine instances found"
        return 0
    fi
    
    local total_instances=0
    local running_instances=0
    local stopped_instances=0
    local instances_without_labels=0
    local high_cost_instances=0
    
    # Process each instance (skip header)
    while IFS= read -r instance_line; do
        if [ -z "$instance_line" ] || echo "$instance_line" | grep -q "NAME"; then
            continue
        fi
        
        total_instances=$((total_instances + 1))
        
        # Parse instance information
        local name=$(echo "$instance_line" | awk '{print $1}')
        local status=$(echo "$instance_line" | awk '{print $2}')
        local zone=$(echo "$instance_line" | awk '{print $3}')
        local machine_type=$(echo "$instance_line" | awk '{print $4}')
        local last_start=$(echo "$instance_line" | awk '{print $5}')
        local labels=$(echo "$instance_line" | awk '{for(i=6;i<=NF;i++) printf "%s ", $i; print ""}')
        
        log "Analyzing instance: $name ($machine_type) in $zone - $status"
        
        # Count by status
        if [ "$status" == "RUNNING" ]; then
            running_instances=$((running_instances + 1))
        else
            stopped_instances=$((stopped_instances + 1))
            log_warning "⚠️  Stopped instance: $name"
        fi
        
        # Check labels
        if [ -z "$labels" ] || [ "$labels" == "None" ]; then
            instances_without_labels=$((instances_without_labels + 1))
            log_warning "⚠️  Instance without labels: $name"
        fi
        
        # Check machine type cost
        if echo "$machine_type" | grep -q "n1-standard-4\|n1-standard-8\|n1-standard-16\|n1-standard-32\|n1-highmem\|n1-highcpu\|e2-standard-4\|e2-standard-8\|e2-standard-16\|e2-standard-32"; then
            high_cost_instances=$((high_cost_instances + 1))
            log_warning "⚠️  High-cost machine type: $name ($machine_type)"
        fi
        
        # Add instance info to results
        jq --arg name "$name" \
           --arg zone "$zone" \
           --arg status "$status" \
           --arg machine_type "$machine_type" \
           --arg last_start "$last_start" \
           --arg labels "$labels" \
           '.compute_instances.instances += [{"name": $name, "zone": $zone, "status": $status, "machine_type": $machine_type, "last_start": $last_start, "labels": $labels}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
        
    done <<< "$instances"
    
    # Update summary
    jq --arg total "$total_instances" \
       --arg running "$running_instances" \
       --arg stopped "$stopped_instances" \
       --arg labels "$instances_without_labels" \
       --arg cost "$high_cost_instances" \
       '.summary.total_compute_instances = ($total | tonumber) |
        .summary.running_compute_instances = ($running | tonumber) |
        .summary.stopped_compute_instances = ($stopped | tonumber) |
        .summary.compute_instances_without_labels = ($labels | tonumber) |
        .summary.high_cost_compute_instances = ($cost | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    log_success "Compute Engine instances audit completed: $total_instances instances"
}

# Function to audit Cloud Functions
audit_cloud_functions() {
    log "⚡ Auditing Cloud Functions..."
    
    # List all Cloud Functions
    local functions=$(gcloud functions list --format="table(name,status,entryPoint,runtime,updateTime,memory,timeout)" 2>/dev/null || echo "")
    
    if [ -z "$functions" ]; then
        log "No Cloud Functions found"
        return 0
    fi
    
    local total_functions=0
    local active_functions=0
    local inactive_functions=0
    local functions_without_timeout=0
    local high_memory_functions=0
    
    # Process each function (skip header)
    while IFS= read -r function_line; do
        if [ -z "$function_line" ] || echo "$function_line" | grep -q "NAME"; then
            continue
        fi
        
        total_functions=$((total_functions + 1))
        
        # Parse function information
        local name=$(echo "$function_line" | awk '{print $1}')
        local status=$(echo "$function_line" | awk '{print $2}')
        local entry_point=$(echo "$function_line" | awk '{print $3}')
        local runtime=$(echo "$function_line" | awk '{print $4}')
        local update_time=$(echo "$function_line" | awk '{print $5}')
        local memory=$(echo "$function_line" | awk '{print $6}')
        local timeout=$(echo "$function_line" | awk '{print $7}')
        
        log "Analyzing function: $name ($runtime) - $status"
        
        # Count by status
        if [ "$status" == "ACTIVE" ]; then
            active_functions=$((active_functions + 1))
        else
            inactive_functions=$((inactive_functions + 1))
            log_warning "⚠️  Inactive function: $name"
        fi
        
        # Check timeout configuration
        if [ "$timeout" == "None" ] || [ -z "$timeout" ]; then
            functions_without_timeout=$((functions_without_timeout + 1))
            log_warning "⚠️  Function without timeout: $name"
        fi
        
        # Check memory allocation
        if [ "$memory" != "None" ] && [ -n "$memory" ]; then
            local memory_mb=$(echo "$memory" | sed 's/[^0-9]//g')
            if [ "$memory_mb" -gt 1024 ]; then
                high_memory_functions=$((high_memory_functions + 1))
                log_warning "⚠️  High memory function: $name (${memory}MB)"
            fi
        fi
        
        # Add function info to results
        jq --arg name "$name" \
           --arg status "$status" \
           --arg entry_point "$entry_point" \
           --arg runtime "$runtime" \
           --arg update_time "$update_time" \
           --arg memory "$memory" \
           --arg timeout "$timeout" \
           '.cloud_functions.functions += [{"name": $name, "status": $status, "entry_point": $entry_point, "runtime": $runtime, "update_time": $update_time, "memory": $memory, "timeout": $timeout}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
        
    done <<< "$functions"
    
    # Update summary
    jq --arg total "$total_functions" \
       --arg active "$active_functions" \
       --arg inactive "$inactive_functions" \
       --arg timeout "$functions_without_timeout" \
       --arg memory "$high_memory_functions" \
       '.summary.total_cloud_functions = ($total | tonumber) |
        .summary.active_cloud_functions = ($active | tonumber) |
        .summary.inactive_cloud_functions = ($inactive | tonumber) |
        .summary.cloud_functions_without_timeout = ($timeout | tonumber) |
        .summary.high_memory_cloud_functions = ($memory | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    log_success "Cloud Functions audit completed: $total_functions functions"
}

# Function to audit App Engine applications
audit_app_engine() {
    log "🌐 Auditing App Engine applications..."
    
    # List App Engine applications
    local apps=$(gcloud app services list --format="table(id,version,traffic_split" 2>/dev/null || echo "")
    
    if [ -z "$apps" ]; then
        log "No App Engine applications found"
        return 0
    fi
    
    local total_apps=0
    local total_versions=0
    
    # Process each app (skip header)
    while IFS= read -r app_line; do
        if [ -z "$app_line" ] || echo "$app_line" | grep -q "ID"; then
            continue
        fi
        
        total_apps=$((total_apps + 1))
        
        # Parse app information
        local id=$(echo "$app_line" | awk '{print $1}')
        local version=$(echo "$app_line" | awk '{print $2}')
        local traffic_split=$(echo "$app_line" | awk '{print $3}')
        
        log "Analyzing App Engine app: $id (version: $version)"
        
        # Count versions
        if [ "$version" != "None" ] && [ -n "$version" ]; then
            total_versions=$((total_versions + 1))
        fi
        
        # Add app info to results
        jq --arg id "$id" \
           --arg version "$version" \
           --arg traffic_split "$traffic_split" \
           '.app_engine.applications += [{"id": $id, "version": $version, "traffic_split": $traffic_split}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
        
    done <<< "$apps"
    
    # Update summary
    jq --arg apps "$total_apps" \
       --arg versions "$total_versions" \
       '.summary.total_app_engine_apps = ($apps | tonumber) |
        .summary.total_app_engine_versions = ($versions | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    log_success "App Engine audit completed: $total_apps applications, $total_versions versions"
}

# Function to generate compute recommendations
generate_compute_recommendations() {
    log "🎯 Generating compute recommendations..."
    
    # Read current results
    local stopped_instances=$(jq '.summary.stopped_compute_instances' "$RESULTS_FILE")
    local instances_without_labels=$(jq '.summary.compute_instances_without_labels' "$RESULTS_FILE")
    local high_cost_instances=$(jq '.summary.high_cost_compute_instances' "$RESULTS_FILE")
    local services_without_scaling=$(jq '.summary.cloud_run_services_without_scaling' "$RESULTS_FILE")
    local high_memory_services=$(jq '.summary.high_memory_cloud_run_services' "$RESULTS_FILE")
    
    # Initialize recommendations array
    jq '.recommendations = []' "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    # Add recommendations based on findings
    if [ "$stopped_instances" -gt 0 ]; then
        jq '.recommendations += ["Review and consider deleting '${stopped_instances}' stopped Compute Engine instances to reduce costs"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$instances_without_labels" -gt 0 ]; then
        jq '.recommendations += ["Add labels to '${instances_without_labels}' Compute Engine instances for better resource management"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$high_cost_instances" -gt 0 ]; then
        jq '.recommendations += ["Review '${high_cost_instances}' high-cost machine types for potential downsizing opportunities"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$services_without_scaling" -gt 0 ]; then
        jq '.recommendations += ["Configure scaling policies for '${services_without_scaling}' Cloud Run services without scaling configuration"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$high_memory_services" -gt 0 ]; then
        jq '.recommendations += ["Review memory allocation for '${high_memory_services}' high-memory Cloud Run services"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    # Add general recommendations
    jq '.recommendations += ["Implement automated instance scheduling for non-production workloads"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    jq '.recommendations += ["Set up compute resource monitoring and cost alerts"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    jq '.recommendations += ["Consider using preemptible instances for batch processing workloads"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
}

# Main compute audit function
audit_compute() {
    log "Starting comprehensive compute audit for project: $PROJECT_ID"
    
    # Create results file
    RESULTS_FILE="$SCRIPT_DIR/compute_audit_results.json"
    
    # Initialize results structure
    cat > "$RESULTS_FILE" << EOF
{
  "audit_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project_id": "$PROJECT_ID",
  "project_name": "$PROJECT_NAME",
  "audit_type": "compute_audit",
  "summary": {
    "total_cloud_run_services": 0,
    "running_cloud_run_services": 0,
    "stopped_cloud_run_services": 0,
    "cloud_run_services_without_scaling": 0,
    "high_memory_cloud_run_services": 0,
    "total_compute_instances": 0,
    "running_compute_instances": 0,
    "stopped_compute_instances": 0,
    "compute_instances_without_labels": 0,
    "high_cost_compute_instances": 0,
    "total_cloud_functions": 0,
    "active_cloud_functions": 0,
    "inactive_cloud_functions": 0,
    "cloud_functions_without_timeout": 0,
    "high_memory_cloud_functions": 0,
    "total_app_engine_apps": 0,
    "total_app_engine_versions": 0
  },
  "cloud_run": {
    "services": []
  },
  "compute_instances": {
    "instances": []
  },
  "cloud_functions": {
    "functions": []
  },
  "app_engine": {
    "applications": []
  },
  "recommendations": []
}
EOF
    
    # Run all compute audits
    audit_cloud_run
    audit_compute_instances
    audit_cloud_functions
    audit_app_engine
    
    # Generate recommendations
    generate_compute_recommendations
    
    log_success "Compute audit completed. Results saved to: $RESULTS_FILE"
}

# Function to show audit summary
show_summary() {
    log "📊 Compute Audit Summary"
    log "========================="
    
    if [ -f "$RESULTS_FILE" ]; then
        local cloud_run=$(jq '.summary.total_cloud_run_services' "$RESULTS_FILE")
        local compute_instances=$(jq '.summary.total_compute_instances' "$RESULTS_FILE")
        local cloud_functions=$(jq '.summary.total_cloud_functions' "$RESULTS_FILE")
        local app_engine=$(jq '.summary.total_app_engine_apps' "$RESULTS_FILE")
        
        log "Cloud Run: $cloud_run services"
        log "Compute Engine: $compute_instances instances"
        log "Cloud Functions: $cloud_functions functions"
        log "App Engine: $app_engine applications"
        
        local stopped_instances=$(jq '.summary.stopped_compute_instances' "$RESULTS_FILE")
        local instances_without_labels=$(jq '.summary.compute_instances_without_labels' "$RESULTS_FILE")
        local high_cost_instances=$(jq '.summary.high_cost_compute_instances' "$RESULTS_FILE")
        
        if [ "$stopped_instances" -gt 0 ]; then
            log_warning "⚠️  Found $stopped_instances stopped instances - potential cost savings"
        fi
        
        if [ "$instances_without_labels" -gt 0 ]; then
            log_warning "⚠️  Found $instances_without_labels instances without labels - management issue"
        fi
        
        if [ "$high_cost_instances" -gt 0 ]; then
            log_warning "⚠️  Found $high_cost_instances high-cost instances - optimization opportunity"
        fi
    else
        log_error "Results file not found"
    fi
}

# Main execution
main() {
    log "🚀 Starting Google Cloud Compute Audit"
    log "======================================"
    
    # Check if jq is available for JSON processing
    if ! command -v jq &> /dev/null; then
        log_error "jq is required for JSON processing. Please install it first."
        exit 1
    fi
    
    # Run the audit
    audit_compute
    
    # Show summary
    show_summary
    
    log "✅ Compute audit completed successfully!"
}

# Run main function
main "$@"
