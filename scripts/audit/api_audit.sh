#!/bin/bash

# 🔌 GOOGLE CLOUD API AUDIT SCRIPT
# Comprehensive API analysis for cost optimization and security

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
    echo -e "${BLUE}[API Audit]${NC} $1"
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

# Essential APIs for Helios system
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

# Optional APIs that might be useful
OPTIONAL_APIS=(
    "bigquery.googleapis.com"
    "dataproc.googleapis.com"
    "dataflow.googleapis.com"
    "composer.googleapis.com"
    "datastore.googleapis.com"
    "cloudtasks.googleapis.com"
    "cloudscheduler.googleapis.com"
    "workflows.googleapis.com"
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

# Function to check API usage
check_api_usage() {
    local api_name=$1
    local usage=$(gcloud services list --enabled --filter="config.name=$api_name" --format="value(usage)" 2>/dev/null || echo "N/A")
    echo "$usage"
}

# Function to check API cost impact
check_api_cost_impact() {
    local api_name=$1
    
    # Check if API is in expensive list
    if [[ " ${EXPENSIVE_APIS[@]} " =~ " ${api_name} " ]]; then
        echo "HIGH"
    else
        echo "LOW"
    fi
}

# Main API audit function
audit_apis() {
    log "Starting comprehensive API audit for project: $PROJECT_ID"
    
    # Create results file
    RESULTS_FILE="$SCRIPT_DIR/api_audit_results.json"
    
    # Initialize results structure
    cat > "$RESULTS_FILE" << EOF
{
  "audit_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project_id": "$PROJECT_ID",
  "project_name": "$PROJECT_NAME",
  "audit_type": "api_audit",
  "summary": {
    "total_enabled_apis": 0,
    "essential_apis": 0,
    "optional_apis": 0,
    "unused_apis": 0,
    "expensive_apis": 0,
    "potential_savings": 0
  },
  "apis": {
    "essential": [],
    "optional": [],
    "unused": [],
    "expensive": [],
    "other": []
  },
  "recommendations": []
}
EOF
    
    # Get all enabled APIs
    log "🔍 Discovering enabled APIs..."
    ENABLED_APIS=$(gcloud services list --enabled --format="value(config.name)")
    TOTAL_APIS=$(echo "$ENABLED_APIS" | wc -l)
    
    log "Found $TOTAL_APIS enabled APIs"
    
    # Initialize counters
    ESSENTIAL_COUNT=0
    OPTIONAL_COUNT=0
    UNUSED_COUNT=0
    EXPENSIVE_COUNT=0
    OTHER_COUNT=0
    
    # Process each API
    while IFS= read -r api; do
        if [ -z "$api" ]; then
            continue
        fi
        
        log "Analyzing API: $api"
        
        # Check usage
        usage=$(check_api_usage "$api")
        cost_impact=$(check_api_cost_impact "$api")
        
        # Categorize API
        if [[ " ${ESSENTIAL_APIS[@]} " =~ " ${api} " ]]; then
            category="essential"
            ESSENTIAL_COUNT=$((ESSENTIAL_COUNT + 1))
            log_success "Essential API: $api"
        elif [[ " ${OPTIONAL_APIS[@]} " =~ " ${api} " ]]; then
            category="optional"
            OPTIONAL_COUNT=$((OPTIONAL_COUNT + 1))
            log_warning "Optional API: $api"
        elif [[ " ${EXPENSIVE_APIS[@]} " =~ " ${api} " ]]; then
            category="expensive"
            EXPENSIVE_COUNT=$((EXPENSIVE_COUNT + 1))
            log_error "Expensive API: $api"
        else
            category="other"
            OTHER_COUNT=$((OTHER_COUNT + 1))
            log "Other API: $api"
        fi
        
        # Check if potentially unused
        if [[ "$usage" == "0" || "$usage" == "null" || "$usage" == "N/A" ]]; then
            UNUSED_COUNT=$((UNUSED_COUNT + 1))
            log_warning "Potentially unused API: $api"
        fi
        
        # Add to results
        jq --arg api "$api" \
           --arg usage "$usage" \
           --arg cost "$cost_impact" \
           --arg category "$category" \
           '.apis.'$category' += [{"name": $api, "usage": $usage, "cost_impact": $cost}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
        
    done <<< "$ENABLED_APIS"
    
    # Update summary
    jq --arg total "$TOTAL_APIS" \
       --arg essential "$ESSENTIAL_COUNT" \
       --arg optional "$OPTIONAL_COUNT" \
       --arg unused "$UNUSED_COUNT" \
       --arg expensive "$EXPENSIVE_COUNT" \
       --arg other "$OTHER_COUNT" \
       '.summary.total_enabled_apis = ($total | tonumber) |
        .summary.essential_apis = ($essential | tonumber) |
        .summary.optional_apis = ($optional | tonumber) |
        .summary.unused_apis = ($unused | tonumber) |
        .summary.expensive_apis = ($expensive | tonumber) |
        .summary.other_apis = ($other | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    # Generate recommendations
    generate_recommendations
    
    log_success "API audit completed. Results saved to: $RESULTS_FILE"
}

# Generate recommendations based on audit results
generate_recommendations() {
    log "🎯 Generating recommendations..."
    
    # Read current results
    local unused_count=$(jq '.summary.unused_apis' "$RESULTS_FILE")
    local expensive_count=$(jq '.summary.expensive_apis' "$RESULTS_FILE")
    local total_apis=$(jq '.summary.total_enabled_apis' "$RESULTS_FILE")
    
    # Initialize recommendations array
    jq '.recommendations = []' "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    # Add recommendations based on findings
    if [ "$unused_count" -gt 0 ]; then
        jq '.recommendations += ["Review and consider disabling '${unused_count}' potentially unused APIs to reduce costs"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$expensive_count" -gt 0 ]; then
        jq '.recommendations += ["Monitor '${expensive_count}' expensive APIs for usage patterns and cost optimization"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$total_apis" -gt 50 ]; then
        jq '.recommendations += ["Consider consolidating APIs - '${total_apis}' enabled APIs may indicate over-provisioning"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    # Add general recommendations
    jq '.recommendations += ["Implement API usage monitoring and alerting"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    jq '.recommendations += ["Set up automated API cleanup for unused services"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    jq '.recommendations += ["Review API permissions and access controls quarterly"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
}

# Function to show audit summary
show_summary() {
    log "📊 API Audit Summary"
    log "===================="
    
    if [ -f "$RESULTS_FILE" ]; then
        local total=$(jq '.summary.total_enabled_apis' "$RESULTS_FILE")
        local essential=$(jq '.summary.essential_apis' "$RESULTS_FILE")
        local optional=$(jq '.summary.optional_apis' "$RESULTS_FILE")
        local unused=$(jq '.summary.unused_apis' "$RESULTS_FILE")
        local expensive=$(jq '.summary.expensive_apis' "$RESULTS_FILE")
        
        log "Total Enabled APIs: $total"
        log "Essential APIs: $essential"
        log "Optional APIs: $optional"
        log "Potentially Unused: $unused"
        log "Expensive APIs: $expensive"
        
        if [ "$unused" -gt 0 ]; then
            log_warning "⚠️  Found $unused potentially unused APIs - potential cost savings"
        fi
        
        if [ "$expensive" -gt 0 ]; then
            log_warning "⚠️  Found $expensive expensive APIs - monitor usage closely"
        fi
    else
        log_error "Results file not found"
    fi
}

# Main execution
main() {
    log "🚀 Starting Google Cloud API Audit"
    log "=================================="
    
    # Check if jq is available for JSON processing
    if ! command -v jq &> /dev/null; then
        log_error "jq is required for JSON processing. Please install it first."
        exit 1
    fi
    
    # Run the audit
    audit_apis
    
    # Show summary
    show_summary
    
    log "✅ API audit completed successfully!"
}

# Run main function
main "$@"
