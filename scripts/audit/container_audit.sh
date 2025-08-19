#!/bin/bash

# 🐳 GOOGLE CLOUD CONTAINER AUDIT SCRIPT
# Comprehensive container analysis for cost optimization and security

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
    echo -e "${BLUE}[Container Audit]${NC} $1"
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

# Function to audit GCR (Google Container Registry)
audit_gcr() {
    log "🔍 Auditing Google Container Registry (GCR)..."
    
    # Check if gcloud container images command is available
    if ! gcloud container images list --help &> /dev/null; then
        log_error "gcloud container images command not available - skipping GCR audit"
        return 1
    fi
    
    # List all repositories in GCR
    local repositories=$(gcloud container images list --repository=gcr.io/"$PROJECT_ID" --format="table(name)" 2>/dev/null || echo "")
    
    if [ -z "$repositories" ]; then
        log "No GCR repositories found"
        return 0
    fi
    
    local total_repos=0
    local total_images=0
    local total_size_bytes=0
    local untagged_images=0
    local large_images=0
    local old_images=0
    
    # Process each repository (skip header)
    while IFS= read -r repo_line; do
        if [ -z "$repo_line" ] || echo "$repo_line" | grep -q "NAME"; then
            continue
        fi
        
        total_repos=$((total_repos + 1))
        local repo_name="$repo_line"
        
        log "Analyzing repository: $repo_name"
        
        # List all images in this repository
        local images=$(gcloud container images list-tags "$repo_name" --format="table(tags,timestamp.datetime,digest,imageSizeBytes)" --limit=100 2>/dev/null || echo "")
        
        if [ -z "$images" ]; then
            continue
        fi
        
        # Process each image (skip header)
        while IFS= read -r image_line; do
            if [ -z "$image_line" ] || echo "$image_line" | grep -q "TAGS"; then
                continue
            fi
            
            total_images=$((total_images + 1))
            
            # Parse image information
            local tags=$(echo "$image_line" | awk '{print $1}')
            local timestamp=$(echo "$image_line" | awk '{print $2}')
            local digest=$(echo "$image_line" | awk '{print $3}')
            local size_bytes=$(echo "$image_line" | awk '{print $4}')
            
            # Check if image is untagged
            if [ "$tags" == "None" ] || [ -z "$tags" ]; then
                untagged_images=$((untagged_images + 1))
                log_warning "⚠️  Untagged image found: $digest"
            fi
            
            # Check image size
            if [ "$size_bytes" != "None" ] && [ -n "$size_bytes" ]; then
                total_size_bytes=$((total_size_bytes + size_bytes))
                
                # Check if image is large (>500MB)
                if [ "$size_bytes" -gt 524288000 ]; then
                    large_images=$((large_images + 1))
                    log_warning "⚠️  Large image found: $digest ($(bytes_to_human $size_bytes))"
                fi
            fi
            
            # Check image age (older than 90 days)
            if [ "$timestamp" != "None" ] && [ -n "$timestamp" ]; then
                local image_date
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            image_date=$(date -j -f "%Y-%m-%dT%H:%M:%S" "$timestamp" +%s 2>/dev/null || echo "0")
        else
            # Linux
            image_date=$(date -d "$timestamp" +%s 2>/dev/null || echo "0")
        fi
                local current_date=$(date +%s)
                local days_old=$(((current_date - image_date) / 86400))
                
                if [ "$days_old" -gt 90 ]; then
                    old_images=$((old_images + 1))
                    log_warning "⚠️  Old image found: $digest ($days_old days old)"
                fi
            fi
            
            # Add image info to results
            jq --arg repo "$repo_name" \
               --arg tags "$tags" \
               --arg timestamp "$timestamp" \
               --arg digest "$digest" \
               --arg size "$size_bytes" \
               --arg untagged "$(echo "$tags" | grep -q "None\|^$" && echo "true" || echo "false")" \
               '.gcr.images += [{"repository": $repo, "tags": $tags, "timestamp": $timestamp, "digest": $digest, "size_bytes": ($size | tonumber), "untagged": ($untagged | test("true"))}]' \
               "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
            
        done <<< "$images"
        
    done <<< "$repositories"
    
    # Update summary
    jq --arg repos "$total_repos" \
       --arg images "$total_images" \
       --arg size "$total_size_bytes" \
       --arg untagged "$untagged_images" \
       --arg large "$large_images" \
       --arg old "$old_images" \
       '.summary.total_gcr_repositories = ($repos | tonumber) |
        .summary.total_gcr_images = ($images | tonumber) |
        .summary.total_gcr_size_bytes = ($size | tonumber) |
        .summary.untagged_gcr_images = ($untagged | tonumber) |
        .summary.large_gcr_images = ($large | tonumber) |
        .summary.old_gcr_images = ($old | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    log_success "GCR audit completed: $total_repos repositories, $total_images images, $(bytes_to_human $total_size_bytes)"
}

# Function to audit Artifact Registry
audit_artifact_registry() {
    log "🏗️ Auditing Artifact Registry..."
    
    # Check if gcloud artifacts command is available
    if ! gcloud artifacts --help &> /dev/null; then
        log_error "gcloud artifacts command not available - skipping Artifact Registry audit"
        return 1
    fi
    
    # List all repositories in Artifact Registry
    local repositories=$(gcloud artifacts repositories list --location=us-central1 --format="table(name,format,createTime)" 2>/dev/null || echo "")
    
    if [ -z "$repositories" ]; then
        log "No Artifact Registry repositories found"
        return 0
    fi
    
    local total_repos=0
    local docker_repos=0
    local maven_repos=0
    local npm_repos=0
    
    # Process each repository (skip header)
    while IFS= read -r repo_line; do
        if [ -z "$repo_line" ] || echo "$repo_line" | grep -q "NAME"; then
            continue
        fi
        
        total_repos=$((total_repos + 1))
        
        # Parse repository information
        local name=$(echo "$repo_line" | awk '{print $1}')
        local format=$(echo "$repo_line" | awk '{print $2}')
        local create_time=$(echo "$repo_line" | awk '{print $3}')
        
        log "Analyzing Artifact Registry repository: $name ($format)"
        
        # Count by format
        case "$format" in
            "DOCKER")
                docker_repos=$((docker_repos + 1))
                ;;
            "MAVEN")
                maven_repos=$((maven_repos + 1))
                ;;
            "NPM")
                npm_repos=$((npm_repos + 1))
                ;;
            *)
                log "Unknown format: $format"
                ;;
        esac
        
        # Add repository info to results
        jq --arg name "$name" \
           --arg format "$format" \
           --arg create_time "$create_time" \
           '.artifact_registry.repositories += [{"name": $name, "format": $format, "create_time": $create_time}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
        
    done <<< "$repositories"
    
    # Update summary
    jq --arg total "$total_repos" \
       --arg docker "$docker_repos" \
       --arg maven "$maven_repos" \
       --arg npm "$npm_repos" \
       '.summary.total_artifact_registry_repositories = ($total | tonumber) |
        .summary.docker_artifact_repositories = ($docker | tonumber) |
        .summary.maven_artifact_repositories = ($maven | tonumber) |
        .summary.npm_artifact_repositories = ($npm | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    log_success "Artifact Registry audit completed: $total_repos repositories"
}

# Function to audit Kubernetes clusters
audit_kubernetes() {
    log "☸️ Auditing Kubernetes clusters..."
    
    # Check if gcloud container clusters command is available
    if ! gcloud container clusters list --help &> /dev/null; then
        log_error "gcloud container clusters command not available - skipping Kubernetes audit"
        return 1
    fi
    
    # List all Kubernetes clusters
    local clusters=$(gcloud container clusters list --format="table(name,location,currentMasterVersion,currentNodeCount,status,autopilot.enabled)" 2>/dev/null || echo "")
    
    if [ -z "$clusters" ]; then
        log "No Kubernetes clusters found"
        return 0
    fi
    
    local total_clusters=0
    local running_clusters=0
    local stopped_clusters=0
    local autopilot_clusters=0
    local large_clusters=0
    
    # Process each cluster (skip header)
    while IFS= read -r cluster_line; do
        if [ -z "$cluster_line" ] || echo "$cluster_line" | grep -q "NAME"; then
            continue
        fi
        
        total_clusters=$((total_clusters + 1))
        
        # Parse cluster information
        local name=$(echo "$cluster_line" | awk '{print $1}')
        local location=$(echo "$cluster_line" | awk '{print $2}')
        local version=$(echo "$cluster_line" | awk '{print $3}')
        local node_count=$(echo "$cluster_line" | awk '{print $4}')
        local status=$(echo "$cluster_line" | awk '{print $5}')
        local autopilot=$(echo "$cluster_line" | awk '{print $6}')
        
        log "Analyzing Kubernetes cluster: $name in $location - $status"
        
        # Count by status
        if [ "$status" == "RUNNING" ]; then
            running_clusters=$((running_clusters + 1))
        else
            stopped_clusters=$((stopped_clusters + 1))
            log_warning "⚠️  Stopped cluster: $name"
        fi
        
        # Check if autopilot
        if [ "$autopilot" == "True" ]; then
            autopilot_clusters=$((autopilot_clusters + 1))
        fi
        
        # Check cluster size
        if [ "$node_count" != "None" ] && [ -n "$node_count" ]; then
            if [ "$node_count" -gt 10 ]; then
                large_clusters=$((large_clusters + 1))
                log_warning "⚠️  Large cluster: $name ($node_count nodes)"
            fi
        fi
        
        # Add cluster info to results
        jq --arg name "$name" \
           --arg location "$location" \
           --arg version "$version" \
           --arg node_count "$node_count" \
           --arg status "$status" \
           --arg autopilot "$autopilot" \
           '.kubernetes.clusters += [{"name": $name, "location": $location, "version": $version, "node_count": ($node_count | tonumber), "status": $status, "autopilot": ($autopilot | test("True"))}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
        
    done <<< "$clusters"
    
    # Update summary
    jq --arg total "$total_clusters" \
       --arg running "$running_clusters" \
       --arg stopped "$stopped_clusters" \
       --arg autopilot "$autopilot_clusters" \
       --arg large "$large_clusters" \
       '.summary.total_kubernetes_clusters = ($total | tonumber) |
        .summary.running_kubernetes_clusters = ($running | tonumber) |
        .summary.stopped_kubernetes_clusters = ($stopped | tonumber) |
        .summary.autopilot_kubernetes_clusters = ($autopilot | tonumber) |
        .summary.large_kubernetes_clusters = ($large | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    log_success "Kubernetes audit completed: $total_clusters clusters"
}

# Function to generate container recommendations
generate_container_recommendations() {
    log "🎯 Generating container recommendations..."
    
    # Read current results
    local untagged_images=$(jq '.summary.untagged_gcr_images' "$RESULTS_FILE")
    local large_images=$(jq '.summary.large_gcr_images' "$RESULTS_FILE")
    local old_images=$(jq '.summary.old_gcr_images' "$RESULTS_FILE")
    local stopped_clusters=$(jq '.summary.stopped_kubernetes_clusters' "$RESULTS_FILE")
    local large_clusters=$(jq '.summary.large_kubernetes_clusters' "$RESULTS_FILE")
    
    # Initialize recommendations array
    jq '.recommendations = []' "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    # Add recommendations based on findings
    if [ "$untagged_images" -gt 0 ]; then
        jq '.recommendations += ["Clean up '${untagged_images}' untagged container images to reduce storage costs"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$large_images" -gt 0 ]; then
        jq '.recommendations += ["Review '${large_images}' large container images for optimization opportunities"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$old_images" -gt 0 ]; then
        jq '.recommendations += ["Consider removing '${old_images}' old container images to reduce storage costs"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$stopped_clusters" -gt 0 ]; then
        jq '.recommendations += ["Review and consider deleting '${stopped_clusters}' stopped Kubernetes clusters"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$large_clusters" -gt 0 ]; then
        jq '.recommendations += ["Review '${large_clusters}' large Kubernetes clusters for potential downsizing"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    # Add general recommendations
    jq '.recommendations += ["Implement container image lifecycle policies"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    jq '.recommendations += ["Set up automated container image cleanup"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    jq '.recommendations += ["Use multi-stage builds to reduce container image sizes"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    jq '.recommendations += ["Consider using Artifact Registry instead of GCR for new projects"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
}

# Main container audit function
audit_containers() {
    log "Starting comprehensive container audit for project: $PROJECT_ID"
    
    # Create results file
    RESULTS_FILE="$SCRIPT_DIR/container_audit_results.json"
    
    # Initialize results structure
    cat > "$RESULTS_FILE" << EOF
{
  "audit_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project_id": "$PROJECT_ID",
  "project_name": "$PROJECT_NAME",
  "audit_type": "container_audit",
  "summary": {
    "total_gcr_repositories": 0,
    "total_gcr_images": 0,
    "total_gcr_size_bytes": 0,
    "untagged_gcr_images": 0,
    "large_gcr_images": 0,
    "old_gcr_images": 0,
    "total_artifact_registry_repositories": 0,
    "docker_artifact_repositories": 0,
    "maven_artifact_repositories": 0,
    "npm_artifact_repositories": 0,
    "total_kubernetes_clusters": 0,
    "running_kubernetes_clusters": 0,
    "stopped_kubernetes_clusters": 0,
    "autopilot_kubernetes_clusters": 0,
    "large_kubernetes_clusters": 0
  },
  "gcr": {
    "images": []
  },
  "artifact_registry": {
    "repositories": []
  },
  "kubernetes": {
    "clusters": []
  },
  "recommendations": []
}
EOF
    
    # Check if bc is available
    check_bc
    
    # Run all container audits
    audit_gcr
    audit_artifact_registry
    audit_kubernetes
    
    # Generate recommendations
    generate_container_recommendations
    
    log_success "Container audit completed. Results saved to: $RESULTS_FILE"
}

# Function to show audit summary
show_summary() {
    log "📊 Container Audit Summary"
    log "==========================="
    
    if [ -f "$RESULTS_FILE" ]; then
        local gcr_repos=$(jq '.summary.total_gcr_repositories' "$RESULTS_FILE")
        local gcr_images=$(jq '.summary.total_gcr_images' "$RESULTS_FILE")
        local gcr_size=$(jq '.summary.total_gcr_size_bytes' "$RESULTS_FILE")
        local artifact_repos=$(jq '.summary.total_artifact_registry_repositories' "$RESULTS_FILE")
        local k8s_clusters=$(jq '.summary.total_kubernetes_clusters' "$RESULTS_FILE")
        
        log "GCR: $gcr_repos repositories, $gcr_images images, $(bytes_to_human $gcr_size)"
        log "Artifact Registry: $artifact_repos repositories"
        log "Kubernetes: $k8s_clusters clusters"
        
        local untagged=$(jq '.summary.untagged_gcr_images' "$RESULTS_FILE")
        local large_images=$(jq '.summary.large_gcr_images' "$RESULTS_FILE")
        local stopped_clusters=$(jq '.summary.stopped_kubernetes_clusters' "$RESULTS_FILE")
        
        if [ "$untagged" -gt 0 ]; then
            log_warning "⚠️  Found $untagged untagged images - potential cleanup opportunity"
        fi
        
        if [ "$large_images" -gt 0 ]; then
            log_warning "⚠️  Found $large_images large images - optimization opportunity"
        fi
        
        if [ "$stopped_clusters" -gt 0 ]; then
            log_warning "⚠️  Found $stopped_clusters stopped clusters - potential cost savings"
        fi
    else
        log_error "Results file not found"
    fi
}

# Main execution
main() {
    log "🚀 Starting Google Cloud Container Audit"
    log "========================================"
    
    # Check if jq is available for JSON processing
    if ! command -v jq &> /dev/null; then
        log_error "jq is required for JSON processing. Please install it first."
        exit 1
    fi
    
    # Run the audit
    audit_containers
    
    # Show summary
    show_summary
    
    log "✅ Container audit completed successfully!"
}

# Run main function
main "$@"
