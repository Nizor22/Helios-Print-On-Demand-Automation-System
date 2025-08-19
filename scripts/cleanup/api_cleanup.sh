#!/bin/bash

# 🔌 GOOGLE CLOUD API CLEANUP SCRIPT
# Automated cleanup of unused APIs with safety checks

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
    echo -e "${BLUE}[API Cleanup]${NC} $1"
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

# Configuration
DRY_RUN=${DRY_RUN:-true}
FORCE_DISABLE=${FORCE_DISABLE:-false}
CLEANUP_UNUSED_APIS=${CLEANUP_UNUSED_APIS:-true}
CLEANUP_EXPENSIVE_APIS=${CLEANUP_EXPENSIVE_APIS:-false}

# Essential APIs for Helios system (NEVER disable these)
ESSENTIAL_APIS=(
    "compute.googleapis.com"
    "run.googleapis.com"
    "storage.googleapis.com"
    "firestore.googleapis.com"
    "cloudbuild.googleapis.com"
    "secretmanager.googleapis.com"
    "logging.googleapis.com"
    "monitoring.googleapis.com"
    "cloudscheduler.googleapis.com"
    "pubsub.googleapis.com"
    "iam.googleapis.com"
    "cloudkms.googleapis.com"
    "vertexai.googleapis.com"
    "aiplatform.googleapis.com"
    "cloudfunctions.googleapis.com"
    "cloudresourcemanager.googleapis.com"
    "servicenetworking.googleapis.com"
    "vpcaccess.googleapis.com"
    "redis.googleapis.com"
    "sqladmin.googleapis.com"
)

# Optional APIs that might be useful but not critical
OPTIONAL_APIS=(
    "bigquery.googleapis.com"
    "dataproc.googleapis.com"
    "dataflow.googleapis.com"
    "composer.googleapis.com"
    "datastore.googleapis.com"
    "cloudtasks.googleapis.com"
    "workflows.googleapis.com"
    "cloudtrace.googleapis.com"
    "cloudprofiler.googleapis.com"
    "errorreporting.googleapis.com"
)

# Potentially expensive APIs to monitor
EXPENSIVE_APIS=(
    "aiplatform.googleapis.com"
    "vertexai.googleapis.com"
    "bigquery.googleapis.com"
    "dataproc.googleapis.com"
    "dataflow.googleapis.com"
    "composer.googleapis.com"
    "cloudkms.googleapis.com"
)

# Function to confirm cleanup
confirm_cleanup() {
    if [ "$DRY_RUN" = "true" ]; then
        log "🔍 DRY RUN MODE - No APIs will be disabled"
        return 0
    fi
    
    echo -e "${YELLOW}⚠️  WARNING: This script will DISABLE APIs from your Google Cloud project!${NC}"
    echo -e "${YELLOW}Project: $PROJECT_NAME ($PROJECT_ID)${NC}"
    echo ""
    echo "The following cleanup operations will be performed:"
    echo "- Disable unused APIs (with safety checks)"
    echo "- Review expensive APIs for optimization"
    echo "- Preserve essential APIs for Helios system"
    echo ""
    echo "Essential APIs that will NEVER be disabled:"
    for api in "${ESSENTIAL_APIS[@]}"; do
        echo "  - $api"
    done
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " confirmation
    
    if [ "$confirmation" != "yes" ]; then
        log "API cleanup cancelled by user"
        exit 0
    fi
    
    log "API cleanup confirmed - proceeding with API management"
}

# Function to check if API is essential
is_essential_api() {
    local api_name=$1
    for essential in "${ESSENTIAL_APIS[@]}"; do
        if [ "$api_name" = "$essential" ]; then
            return 0
        fi
    done
    return 1
}

# Function to check if API is optional
is_optional_api() {
    local api_name=$1
    for optional in "${OPTIONAL_APIS[@]}"; do
        if [ "$api_name" = "$optional" ]; then
            return 0
        fi
    done
    return 1
}

# Function to check if API is expensive
is_expensive_api() {
    local api_name=$1
    for expensive in "${EXPENSIVE_APIS[@]}"; do
        if [ "$api_name" = "$expensive" ]; then
            return 0
        fi
    done
    return 1
}

# Function to check API usage
check_api_usage() {
    local api_name=$1
    local usage=$(gcloud services list --enabled --filter="config.name=$api_name" --format="value(usage)" 2>/dev/null || echo "N/A")
    echo "$usage"
}

# Function to check API dependencies
check_api_dependencies() {
    local api_name=$1
    
    # Check if other services depend on this API
    local dependent_services=$(gcloud services list --enabled --filter="config.name:*" --format="value(config.name)" 2>/dev/null | while read -r service; do
        if gcloud services list --enabled --filter="config.name=$service" --format="value(config.name)" | grep -q "$api_name"; then
            echo "$service"
        fi
    done)
    
    if [ -n "$dependent_services" ]; then
        echo "$dependent_services"
    else
        echo ""
    fi
}

# Function to safely disable API
safely_disable_api() {
    local api_name=$1
    local usage=$2
    local dependencies=$3
    
    log "Analyzing API: $api_name"
    
    # Check if API is essential
    if is_essential_api "$api_name"; then
        log "  ⚠️  Essential API - NEVER disabling: $api_name"
        return 1
    fi
    
    # Check usage
    if [ "$usage" != "0" ] && [ "$usage" != "null" ] && [ "$usage" != "N/A" ]; then
        log "  ⚠️  API has usage ($usage) - skipping: $api_name"
        return 1
    fi
    
    # Check dependencies
    if [ -n "$dependencies" ]; then
        log "  ⚠️  API has dependencies - skipping: $api_name"
        log "    Dependencies: $dependencies"
        return 1
    fi
    
    # Check if expensive API
    if is_expensive_api "$api_name"; then
        log "  💰 Expensive API - review recommended: $api_name"
        if [ "$CLEANUP_EXPENSIVE_APIS" != "true" ]; then
            log "    Skipping expensive API cleanup (disabled)"
            return 1
        fi
    fi
    
    # Safe to disable
    log "  ✅ Safe to disable: $api_name"
    
    if [ "$DRY_RUN" = "true" ]; then
        log "    [DRY RUN] Would disable API: $api_name"
        return 0
    fi
    
    # Actually disable the API
    log "    Disabling API: $api_name"
    if gcloud services disable "$api_name" --quiet 2>/dev/null; then
        log_success "    Successfully disabled API: $api_name"
        return 0
    else
        log_error "    Failed to disable API: $api_name"
        return 1
    fi
}

# Function to cleanup unused APIs
cleanup_unused_apis() {
    if [ "$CLEANUP_UNUSED_APIS" != "true" ]; then
        log "Skipping unused API cleanup (disabled)"
        return 0
    fi
    
    log "🔍 Finding and analyzing enabled APIs..."
    
    # Get all enabled APIs
    local enabled_apis=$(gcloud services list --enabled --format="value(config.name)" 2>/dev/null || echo "")
    
    if [ -z "$enabled_apis" ]; then
        log_error "Failed to retrieve enabled APIs"
        return 1
    fi
    
    local total_apis=0
    local essential_count=0
    local optional_count=0
    local expensive_count=0
    local unused_count=0
    local disabled_count=0
    local skipped_count=0
    
    # Process each API
    while IFS= read -r api; do
        if [ -z "$api" ]; then
            continue
        fi
        
        total_apis=$((total_apis + 1))
        
        # Categorize API
        if is_essential_api "$api"; then
            essential_count=$((essential_count + 1))
            log "Essential API: $api"
        elif is_optional_api "$api"; then
            optional_count=$((optional_count + 1))
            log "Optional API: $api"
        else
            log "Other API: $api"
        fi
        
        # Check if expensive
        if is_expensive_api "$api"; then
            expensive_count=$((expensive_count + 1))
        fi
        
        # Check usage and dependencies
        local usage=$(check_api_usage "$api")
        local dependencies=$(check_api_dependencies "$api")
        
        # Try to disable if safe
        if safely_disable_api "$api" "$usage" "$dependencies"; then
            disabled_count=$((disabled_count + 1))
        else
            skipped_count=$((skipped_count + 1))
        fi
        
        # Count unused APIs
        if [ "$usage" = "0" ] || [ "$usage" = "null" ] || [ "$usage" = "N/A" ]; then
            unused_count=$((unused_count + 1))
        fi
        
    done <<< "$enabled_apis"
    
    # Show summary
    log "📊 API Analysis Summary"
    log "======================="
    log "Total Enabled APIs: $total_apis"
    log "Essential APIs: $essential_count"
    log "Optional APIs: $optional_count"
    log "Expensive APIs: $expensive_count"
    log "Unused APIs: $unused_count"
    
    if [ "$DRY_RUN" = "true" ]; then
        log "DRY RUN: Would disable $disabled_count APIs, skipped $skipped_count APIs"
    else
        log "Cleanup: Disabled $disabled_count APIs, skipped $skipped_count APIs"
    fi
}

# Function to review expensive APIs
review_expensive_apis() {
    log "💰 Reviewing expensive APIs..."
    
    local expensive_apis_found=0
    
    # Get all enabled APIs
    local enabled_apis=$(gcloud services list --enabled --format="value(config.name)" 2>/dev/null || echo "")
    
    if [ -z "$enabled_apis" ]; then
        return 1
    fi
    
    # Process each API
    while IFS= read -r api; do
        if [ -z "$api" ]; then
            continue
        fi
        
        # Check if expensive
        if is_expensive_api "$api"; then
            expensive_apis_found=$((expensive_apis_found + 1))
            local usage=$(check_api_usage "$api")
            
            log "Expensive API: $api (usage: $usage)"
            
            if [ "$usage" = "0" ] || [ "$usage" = "null" ] || [ "$usage" = "N/A" ]; then
                log_warning "  ⚠️  Expensive API with no usage - consider disabling"
            else
                log "  ✅ Expensive API with usage - monitor costs"
            fi
        fi
        
    done <<< "$enabled_apis"
    
    if [ "$expensive_apis_found" -eq 0 ]; then
        log "No expensive APIs found"
    else
        log "Found $expensive_apis_found expensive APIs to review"
    fi
}

# Function to show cleanup summary
show_summary() {
    log "📊 API Cleanup Summary"
    log "======================"
    
    if [ "$DRY_RUN" = "true" ]; then
        log "🔍 DRY RUN COMPLETED - No APIs were actually disabled"
        log "Review the output above to see what would be disabled"
        log "Run with DRY_RUN=false to perform actual API cleanup"
    else
        log "🔌 API CLEANUP COMPLETED - APIs have been disabled"
        log "Review the output above to see what was disabled"
    fi
    
    log ""
    log "To run this script again:"
    log "  DRY_RUN=true bash $0     # Preview what would be disabled"
    log "  DRY_RUN=false bash $0    # Actually disable APIs"
    log ""
    log "Essential APIs are always preserved:"
    for api in "${ESSENTIAL_APIS[@]}"; do
        log "  - $api"
    done
}

# Function to show help
show_help() {
    echo "🔌 Google Cloud API Cleanup Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dry-run              Preview what would be disabled (default)"
    echo "  --execute              Actually disable APIs"
    echo "  --help                 Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  DRY_RUN                    Set to 'false' to actually disable APIs"
    echo "  FORCE_DISABLE              Force disable APIs (use with caution)"
    echo "  CLEANUP_UNUSED_APIS       Enable/disable unused API cleanup (default: true)"
    echo "  CLEANUP_EXPENSIVE_APIS    Enable/disable expensive API cleanup (default: false)"
    echo ""
    echo "Examples:"
    echo "  $0 --dry-run              # Preview API cleanup (safe)"
    echo "  $0 --execute              # Perform API cleanup"
    echo "  DRY_RUN=false $0          # Perform API cleanup (alternative)"
    echo ""
    echo "⚠️  WARNING: This script will disable APIs. Essential APIs for Helios are always preserved."
    echo ""
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --execute)
                DRY_RUN=false
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Main cleanup function
main_cleanup() {
    log "🚀 Starting Google Cloud API Cleanup"
    log "===================================="
    log "Project: $PROJECT_NAME ($PROJECT_ID)"
    log "Dry Run: $DRY_RUN"
    log "Force Disable: $FORCE_DISABLE"
    log ""
    
    # Confirm cleanup (unless dry run)
    confirm_cleanup
    
    # Run all cleanup operations
    cleanup_unused_apis
    review_expensive_apis
    
    # Show summary
    show_summary
    
    log "✅ API cleanup completed!"
}

# Main execution
main() {
    # Parse command line arguments
    parse_args "$@"
    
    # Check if gcloud is available
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Not authenticated with gcloud. Please run 'gcloud auth login' first."
        exit 1
    fi
    
    # Check if project is set
    if [ -z "$(gcloud config get-value project 2>/dev/null)" ]; then
        log_error "No project is set. Please run 'gcloud config set project PROJECT_ID' first."
        exit 1
    fi
    
    # Run the cleanup
    main_cleanup
}

# Run main function
main "$@"
