#!/bin/bash

# 🗄️ GOOGLE CLOUD STORAGE AUDIT SCRIPT
# Comprehensive storage analysis for cost optimization and security

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
    echo -e "${BLUE}[Storage Audit]${NC} $1"
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

# Function to convert bytes to human readable format
bytes_to_human() {
    local bytes=$1
    if [ "$bytes" -gt 1099511627776 ]; then
        echo "$(echo "scale=2; $bytes / 1099511627776" | bc)TB"
    elif [ "$bytes" -gt 1073741824 ]; then
        echo "$(echo "scale=2; $bytes / 1073741824" | bc)GB"
    elif [ "$bytes" -gt 1048576 ]; then
        echo "$(echo "scale=2; $bytes / 1048576" | bc)MB"
    elif [ "$bytes" -gt 1024 ]; then
        echo "$(echo "scale=2; $bytes / 1024" | bc)KB"
    else
        echo "${bytes}B"
    fi
}

# Function to check if bc is available for calculations
check_bc() {
    if ! command -v bc &> /dev/null; then
        log_warning "bc not available - using basic size calculations"
        return 1
    fi
    return 0
}

# Function to audit Cloud Storage buckets
audit_cloud_storage() {
    log "🔍 Auditing Cloud Storage buckets..."
    
    # Check if gsutil is available
    if ! command -v gsutil &> /dev/null; then
        log_error "gsutil not available - skipping Cloud Storage audit"
        return 1
    fi
    
    # List all buckets
    local buckets=$(gsutil ls -b 2>/dev/null || echo "")
    
    if [ -z "$buckets" ]; then
        log "No Cloud Storage buckets found"
        return 0
    fi
    
    local bucket_count=0
    local total_size=0
    local public_buckets=0
    local buckets_without_lifecycle=0
    
    # Process each bucket
    while IFS= read -r bucket; do
        if [ -z "$bucket" ]; then
            continue
        fi
        
        bucket_count=$((bucket_count + 1))
        log "Analyzing bucket: $bucket"
        
        # Get bucket size
        local size_bytes=$(gsutil du -s "$bucket" 2>/dev/null | awk '{print $1}' || echo "0")
        total_size=$((total_size + size_bytes))
        
        # Check if bucket is public
        local iam_output=$(gsutil iam get "$bucket" 2>/dev/null || echo "")
        if echo "$iam_output" | grep -q "allUsers\|allAuthenticatedUsers"; then
            public_buckets=$((public_buckets + 1))
            log_warning "⚠️  Public bucket found: $bucket"
        fi
        
        # Check lifecycle policies
        local lifecycle_output=$(gsutil lifecycle get "$bucket" 2>/dev/null || echo "")
        if [ -z "$lifecycle_output" ] || echo "$lifecycle_output" | grep -q "No lifecycle configuration"; then
            buckets_without_lifecycle=$((buckets_without_lifecycle + 1))
            log_warning "⚠️  No lifecycle policy: $bucket"
        fi
        
        # Add bucket info to results
        jq --arg bucket "$bucket" \
           --arg size "$size_bytes" \
           --arg public "$(echo "$iam_output" | grep -q "allUsers\|allAuthenticatedUsers" && echo "true" || echo "false")" \
           --arg lifecycle "$(echo "$lifecycle_output" | grep -q "No lifecycle configuration" && echo "false" || echo "true")" \
           '.cloud_storage.buckets += [{"name": $bucket, "size_bytes": ($size | tonumber), "public": ($public | test("true")), "has_lifecycle": ($lifecycle | test("true"))}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
        
    done <<< "$buckets"
    
    # Update summary
    jq --arg count "$bucket_count" \
       --arg size "$total_size" \
       --arg public "$public_buckets" \
       --arg lifecycle "$buckets_without_lifecycle" \
       '.summary.total_buckets = ($count | tonumber) |
        .summary.total_storage_size_bytes = ($size | tonumber) |
        .summary.public_buckets = ($public | tonumber) |
        .summary.buckets_without_lifecycle = ($lifecycle | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    log_success "Cloud Storage audit completed: $bucket_count buckets, $(bytes_to_human $total_size)"
}

# Function to audit Compute Engine disks
audit_compute_disks() {
    log "💾 Auditing Compute Engine disks..."
    
    # List all disks
    local disks=$(gcloud compute disks list --format="table(name,sizeGb,users,lastAttachTimestamp,zone)" --filter="status=READY" 2>/dev/null || echo "")
    
    if [ -z "$disks" ]; then
        log "No Compute Engine disks found"
        return 0
    fi
    
    local disk_count=0
    local total_size_gb=0
    local orphaned_disks=0
    local stopped_instance_disks=0
    
    # Process each disk (skip header)
    while IFS= read -r disk_line; do
        if [ -z "$disk_line" ] || echo "$disk_line" | grep -q "NAME"; then
            continue
        fi
        
        disk_count=$((disk_count + 1))
        
        # Parse disk information
        local name=$(echo "$disk_line" | awk '{print $1}')
        local size_gb=$(echo "$disk_line" | awk '{print $2}')
        local users=$(echo "$disk_line" | awk '{print $3}')
        local last_attach=$(echo "$disk_line" | awk '{print $4}')
        local zone=$(echo "$disk_line" | awk '{print $5}')
        
        log "Analyzing disk: $name (${size_gb}GB) in $zone"
        
        total_size_gb=$((total_size_gb + size_gb))
        
        # Check if disk is orphaned
        if [ "$users" == "None" ] || [ -z "$users" ]; then
            orphaned_disks=$((orphaned_disks + 1))
            log_warning "⚠️  Orphaned disk found: $name"
        fi
        
        # Check if disk belongs to stopped instance
        if [ "$users" != "None" ] && [ -n "$users" ]; then
            local instance_status=$(gcloud compute instances describe "$users" --zone="$zone" --format="value(status)" 2>/dev/null || echo "UNKNOWN")
            if [ "$instance_status" == "STOPPED" ]; then
                stopped_instance_disks=$((stopped_instance_disks + 1))
                log_warning "⚠️  Disk belongs to stopped instance: $name -> $users"
            fi
        fi
        
        # Add disk info to results
        jq --arg name "$name" \
           --arg size_gb "$size_gb" \
           --arg users "$users" \
           --arg zone "$zone" \
           --arg orphaned "$(echo "$users" | grep -q "None\|^$" && echo "true" || echo "false")" \
           '.compute_disks.disks += [{"name": $name, "size_gb": ($size_gb | tonumber), "users": $users, "zone": $zone, "orphaned": ($orphaned | test("true"))}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
        
    done <<< "$disks"
    
    # Update summary
    jq --arg count "$disk_count" \
       --arg size "$total_size_gb" \
       --arg orphaned "$orphaned_disks" \
       --arg stopped "$stopped_instance_disks" \
       '.summary.total_disks = ($count | tonumber) |
        .summary.total_disk_size_gb = ($size | tonumber) |
        .summary.orphaned_disks = ($orphaned | tonumber) |
        .summary.stopped_instance_disks = ($stopped | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    log_success "Compute Engine disks audit completed: $disk_count disks, ${total_size_gb}GB total"
}

# Function to audit Firestore databases
audit_firestore() {
    log "🔥 Auditing Firestore databases..."
    
    # List Firestore databases
    local databases=$(gcloud firestore databases list --format="table(name,locationId,type,state)" 2>/dev/null || echo "")
    
    if [ -z "$databases" ]; then
        log "No Firestore databases found"
        return 0
    fi
    
    local db_count=0
    
    # Process each database (skip header)
    while IFS= read -r db_line; do
        if [ -z "$db_line" ] || echo "$db_line" | grep -q "NAME"; then
            continue
        fi
        
        db_count=$((db_count + 1))
        
        # Parse database information
        local name=$(echo "$db_line" | awk '{print $1}')
        local location=$(echo "$db_line" | awk '{print $2}')
        local type=$(echo "$db_line" | awk '{print $3}')
        local state=$(echo "$db_line" | awk '{print $4}')
        
        log "Analyzing Firestore database: $name ($type) in $location"
        
        # Add database info to results
        jq --arg name "$name" \
           --arg location "$location" \
           --arg type "$type" \
           --arg state "$state" \
           '.firestore.databases += [{"name": $name, "location": $location, "type": $type, "state": $state}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
        
    done <<< "$databases"
    
    # Update summary
    jq --arg count "$db_count" \
       '.summary.total_firestore_databases = ($count | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    log_success "Firestore audit completed: $db_count databases"
}

# Function to audit Cloud SQL instances
audit_cloud_sql() {
    log "🗃️ Auditing Cloud SQL instances..."
    
    # List Cloud SQL instances
    local instances=$(gcloud sql instances list --format="table(name,state,settings.tier,settings.dataDiskSizeGb,settings.backupConfiguration.enabled)" 2>/dev/null || echo "")
    
    if [ -z "$instances" ]; then
        log "No Cloud SQL instances found"
        return 0
    fi
    
    local instance_count=0
    local total_disk_gb=0
    local stopped_instances=0
    
    # Process each instance (skip header)
    while IFS= read -r instance_line; do
        if [ -z "$instance_line" ] || echo "$instance_line" | grep -q "NAME"; then
            continue
        fi
        
        instance_count=$((instance_count + 1))
        
        # Parse instance information
        local name=$(echo "$instance_line" | awk '{print $1}')
        local state=$(echo "$instance_line" | awk '{print $2}')
        local tier=$(echo "$instance_line" | awk '{print $3}')
        local disk_size=$(echo "$instance_line" | awk '{print $4}')
        local backup_enabled=$(echo "$instance_line" | awk '{print $5}')
        
        log "Analyzing Cloud SQL instance: $name ($tier) - $state"
        
        if [ "$disk_size" != "None" ] && [ -n "$disk_size" ]; then
            total_disk_gb=$((total_disk_gb + disk_size))
        fi
        
        if [ "$state" == "STOPPED" ]; then
            stopped_instances=$((stopped_instances + 1))
            log_warning "⚠️  Stopped Cloud SQL instance: $name"
        fi
        
        # Add instance info to results
        jq --arg name "$name" \
           --arg state "$state" \
           --arg tier "$tier" \
           --arg disk_size "$disk_size" \
           --arg backup "$backup_enabled" \
           '.cloud_sql.instances += [{"name": $name, "state": $state, "tier": $tier, "disk_size_gb": ($disk_size | tonumber), "backup_enabled": ($backup | test("true"))}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
        
    done <<< "$instances"
    
    # Update summary
    jq --arg count "$instance_count" \
       --arg size "$total_disk_gb" \
       --arg stopped "$stopped_instances" \
       '.summary.total_cloud_sql_instances = ($count | tonumber) |
        .summary.total_cloud_sql_disk_gb = ($size | tonumber) |
        .summary.stopped_cloud_sql_instances = ($stopped | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    log_success "Cloud SQL audit completed: $instance_count instances, ${total_disk_gb}GB total disk"
}

# Function to generate storage recommendations
generate_storage_recommendations() {
    log "🎯 Generating storage recommendations..."
    
    # Read current results
    local public_buckets=$(jq '.summary.public_buckets' "$RESULTS_FILE")
    local orphaned_disks=$(jq '.summary.orphaned_disks' "$RESULTS_FILE")
    local stopped_instances=$(jq '.summary.stopped_instance_disks' "$RESULTS_FILE")
    local buckets_without_lifecycle=$(jq '.summary.buckets_without_lifecycle' "$RESULTS_FILE")
    
    # Initialize recommendations array
    jq '.recommendations = []' "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    # Add recommendations based on findings
    if [ "$public_buckets" -gt 0 ]; then
        jq '.recommendations += ["Review and secure '${public_buckets}' public Cloud Storage buckets for security"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$orphaned_disks" -gt 0 ]; then
        jq '.recommendations += ["Clean up '${orphaned_disks}' orphaned Compute Engine disks to reduce costs"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$stopped_instances" -gt 0 ]; then
        jq '.recommendations += ["Review '${stopped_instances}' disks from stopped instances - consider deleting if not needed"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$buckets_without_lifecycle" -gt 0 ]; then
        jq '.recommendations += ["Implement lifecycle policies for '${buckets_without_lifecycle}' Cloud Storage buckets to manage costs"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    # Add general recommendations
    jq '.recommendations += ["Implement automated storage cleanup policies"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    jq '.recommendations += ["Set up storage cost monitoring and alerts"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    jq '.recommendations += ["Review storage class usage and consider moving to cheaper classes where appropriate"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
}

# Main storage audit function
audit_storage() {
    log "Starting comprehensive storage audit for project: $PROJECT_ID"
    
    # Create results file
    RESULTS_FILE="$SCRIPT_DIR/storage_audit_results.json"
    
    # Initialize results structure
    cat > "$RESULTS_FILE" << EOF
{
  "audit_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project_id": "$PROJECT_ID",
  "project_name": "$PROJECT_NAME",
  "audit_type": "storage_audit",
  "summary": {
    "total_buckets": 0,
    "total_storage_size_bytes": 0,
    "public_buckets": 0,
    "buckets_without_lifecycle": 0,
    "total_disks": 0,
    "total_disk_size_gb": 0,
    "orphaned_disks": 0,
    "stopped_instance_disks": 0,
    "total_firestore_databases": 0,
    "total_cloud_sql_instances": 0,
    "total_cloud_sql_disk_gb": 0,
    "stopped_cloud_sql_instances": 0
  },
  "cloud_storage": {
    "buckets": []
  },
  "compute_disks": {
    "disks": []
  },
  "firestore": {
    "databases": []
  },
  "cloud_sql": {
    "instances": []
  },
  "recommendations": []
}
EOF
    
    # Check if bc is available
    check_bc
    
    # Run all storage audits
    audit_cloud_storage
    audit_compute_disks
    audit_firestore
    audit_cloud_sql
    
    # Generate recommendations
    generate_storage_recommendations
    
    log_success "Storage audit completed. Results saved to: $RESULTS_FILE"
}

# Function to show audit summary
show_summary() {
    log "📊 Storage Audit Summary"
    log "========================"
    
    if [ -f "$RESULTS_FILE" ]; then
        local buckets=$(jq '.summary.total_buckets' "$RESULTS_FILE")
        local storage_size=$(jq '.summary.total_storage_size_bytes' "$RESULTS_FILE")
        local public_buckets=$(jq '.summary.public_buckets' "$RESULTS_FILE")
        local orphaned_disks=$(jq '.summary.orphaned_disks' "$RESULTS_FILE")
        local stopped_instances=$(jq '.summary.stopped_instance_disks' "$RESULTS_FILE")
        
        log "Cloud Storage: $buckets buckets, $(bytes_to_human $storage_size)"
        log "Compute Disks: $(jq '.summary.total_disks' "$RESULTS_FILE") disks, $(jq '.summary.total_disk_size_gb' "$RESULTS_FILE")GB"
        log "Firestore: $(jq '.summary.total_firestore_databases' "$RESULTS_FILE") databases"
        log "Cloud SQL: $(jq '.summary.total_cloud_sql_instances' "$RESULTS_FILE") instances"
        
        if [ "$public_buckets" -gt 0 ]; then
            log_warning "⚠️  Found $public_buckets public buckets - security risk"
        fi
        
        if [ "$orphaned_disks" -gt 0 ]; then
            log_warning "⚠️  Found $orphaned_disks orphaned disks - potential cost savings"
        fi
        
        if [ "$stopped_instances" -gt 0 ]; then
            log_warning "⚠️  Found $stopped_instances disks from stopped instances - review needed"
        fi
    else
        log_error "Results file not found"
    fi
}

# Main execution
main() {
    log "🚀 Starting Google Cloud Storage Audit"
    log "======================================"
    
    # Check if jq is available for JSON processing
    if ! command -v jq &> /dev/null; then
        log_error "jq is required for JSON processing. Please install it first."
        exit 1
    fi
    
    # Run the audit
    audit_storage
    
    # Show summary
    show_summary
    
    log "✅ Storage audit completed successfully!"
}

# Run main function
main "$@"
