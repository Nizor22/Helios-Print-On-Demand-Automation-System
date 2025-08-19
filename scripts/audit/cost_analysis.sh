#!/bin/bash

# 💰 GOOGLE CLOUD COST ANALYSIS SCRIPT
# Comprehensive cost analysis for optimization and budgeting

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
    echo -e "${BLUE}[Cost Analysis]${NC} $1"
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

# Function to get current month and year
get_current_period() {
    date +%Y-%m
}

# Function to get previous month and year
get_previous_period() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        date -v-1m +%Y-%m
    else
        # Linux
        date -d "last month" +%Y-%m
    fi
}

# Function to analyze billing information
analyze_billing() {
    log "💰 Analyzing billing information..."
    
    # Check if billing API is accessible
    if ! gcloud billing accounts list --help &> /dev/null; then
        log_error "Billing API not accessible - skipping billing analysis"
        return 1
    fi
    
    # Get billing account information
    local billing_account=$(gcloud billing projects describe "$PROJECT_ID" --format="value(billingAccountName)" 2>/dev/null || echo "Not set")
    
    if [ "$billing_account" == "Not set" ]; then
        log_warning "⚠️  No billing account associated with project"
        return 1
    fi
    
    log "Billing Account: $billing_account"
    
    # Get billing account details
    local billing_info=$(gcloud billing accounts describe "$billing_account" --format="table(name,displayName,open,accountId)" 2>/dev/null || echo "")
    
    if [ -n "$billing_info" ]; then
        # Parse billing information (skip header)
        while IFS= read -r billing_line; do
            if [ -z "$billing_line" ] || echo "$billing_line" | grep -q "NAME"; then
                continue
            fi
            
            # Parse billing information
            local name=$(echo "$billing_line" | awk '{print $1}')
            local display_name=$(echo "$billing_line" | awk '{print $2}')
            local open=$(echo "$billing_line" | awk '{print $3}')
            local account_id=$(echo "$billing_line" | awk '{print $4}')
            
            log "Billing Account: $display_name ($account_id) - Open: $open"
            
            # Add billing info to results
            jq --arg name "$name" \
               --arg display_name "$display_name" \
               --arg open "$open" \
               --arg account_id "$account_id" \
               '.billing.account = {"name": $name, "display_name": $display_name, "open": ($open | test("True")), "account_id": $account_id}' \
               "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
            
        done <<< "$billing_info"
    fi
    
    # Check for budget alerts
    local budgets=$(gcloud billing budgets list --billing-account="$billing_account" --format="json" 2>/dev/null || echo "")
    
    if [ -n "$budgets" ] && [ "$budgets" != "[]" ]; then
        local total_budgets=0
        
        # Parse JSON response for better reliability
        local budget_count=$(echo "$budgets" | jq '. | length' 2>/dev/null || echo "0")
        
        if [ "$budget_count" -gt 0 ]; then
            echo "$budgets" | jq -r '.[] | "\(.name)|\(.displayName)|\(.budgetAmount.specifiedAmount.currencyCode // "USD")|\(.budgetAmount.specifiedAmount.units // "0")|\(.thresholdRules[0].thresholdPercent // "0")"' | while IFS='|' read -r name display_name currency amount threshold; do
                if [ -n "$name" ]; then
                    total_budgets=$((total_budgets + 1))
                    
                    # Handle null values
                    currency=${currency:-"USD"}
                    amount=${amount:-"0"}
                    threshold=${threshold:-"0"}
                    
                    log "Budget: $display_name - $amount $currency (threshold: ${threshold}%)"
                    
                    # Add budget info to results
                    jq --arg name "$name" \
                       --arg display_name "$display_name" \
                       --arg currency "$currency" \
                       --arg amount "$amount" \
                       --arg threshold "$threshold" \
                       '.billing.budgets += [{"name": $name, "display_name": $display_name, "currency": $currency, "amount": ($amount | tonumber), "threshold": ($threshold | tonumber)}]' \
                       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
                fi
            done
            
            # Update summary
            jq --arg total "$total_budgets" \
               '.summary.total_budgets = ($total | tonumber)' \
               "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
        fi
    else
        log_warning "⚠️  No budgets configured - consider setting up budget alerts"
    fi
    
    log_success "Billing analysis completed"
}

# Function to analyze resource costs
analyze_resource_costs() {
    log "📊 Analyzing resource costs..."
    
    # Get current month costs by service (if billing export is enabled)
    local current_month=$(get_current_period)
    local previous_month=$(get_previous_period)
    
    log "Analyzing costs for: $current_month (current) vs $previous_month (previous)"
    
    # Check if BigQuery billing export is available
    if command -v bq &> /dev/null; then
        log "BigQuery available - attempting to analyze detailed costs..."
        
        # Try to query billing data (this will only work if billing export is enabled)
        local billing_query="
            SELECT 
                service.description as service_name,
                SUM(cost) as total_cost,
                AVG(cost) as avg_cost,
                COUNT(*) as usage_count
            FROM \`${PROJECT_ID}.billing.gcp_billing_export_v1_*\`
            WHERE _TABLE_SUFFIX BETWEEN '${previous_month}01' AND '${current_month}31'
            GROUP BY service_name
            ORDER BY total_cost DESC
            LIMIT 20
        "
        
        # Try to execute query (may fail if billing export not enabled)
        local billing_results=$(bq query --use_legacy_sql=false --format=json "$billing_query" 2>/dev/null || echo "")
        
        if [ -n "$billing_results" ]; then
            # Validate JSON response
            if echo "$billing_results" | jq empty 2>/dev/null; then
                log "Billing export data found - analyzing detailed costs..."
                
                # Process billing results
                local total_cost=0
                local service_count=0
                
                echo "$billing_results" | jq -r '.[] | "\(.service_name)|\(.total_cost)|\(.avg_cost)|\(.usage_count)"' 2>/dev/null | while IFS='|' read -r service cost avg usage; do
                    if [ -n "$service" ]; then
                        service_count=$((service_count + 1))
                        total_cost=$(echo "$total_cost + $cost" | bc -l 2>/dev/null || echo "$total_cost")
                        
                        log "Service: $service - Cost: \$$cost - Usage: $usage"
                        
                        # Add service cost info to results
                        jq --arg service "$service" \
                           --arg cost "$cost" \
                           --arg avg "$avg" \
                           --arg usage "$usage" \
                           '.resource_costs.services += [{"name": $service, "total_cost": ($cost | tonumber), "avg_cost": ($avg | tonumber), "usage_count": ($usage | tonumber)}]' \
                           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
                    fi
                done
                
                # Update summary
                jq --arg cost "$total_cost" \
                   --arg services "$service_count" \
                   '.summary.total_monthly_cost = ($cost | tonumber) |
                    .summary.services_with_costs = ($services | tonumber)' \
                   "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
                
                log_success "Detailed cost analysis completed: \$$total_cost total cost across $service_count services"
            else
                log_warning "Invalid JSON response from BigQuery - using basic cost estimation"
                estimate_basic_costs
            fi
        else
            log_warning "Billing export not enabled - using basic cost estimation"
            estimate_basic_costs
        fi
    else
        log_warning "BigQuery not available - using basic cost estimation"
        estimate_basic_costs
    fi
}

# Function to estimate basic costs when detailed billing is not available
estimate_basic_costs() {
    log "📈 Estimating basic costs from resource usage..."
    
    local total_estimated_cost=0
    
    # Estimate Cloud Run costs
    local cloud_run_services=$(gcloud run services list --format="value(metadata.name)" 2>/dev/null | wc -l)
    if [ "$cloud_run_services" -gt 0 ]; then
        # Rough estimate: $0.00002400 per 100ms per vCPU
        local cloud_run_cost=$(echo "$cloud_run_services * 0.50" | bc -l 2>/dev/null || echo "0")
        total_estimated_cost=$(echo "$total_estimated_cost + $cloud_run_cost" | bc -l 2>/dev/null || echo "$total_estimated_cost")
        
        log "Cloud Run: $cloud_run_services services - estimated \$$cloud_run_cost/month"
        
        jq --arg service "Cloud Run" \
           --arg cost "$cloud_run_cost" \
           --arg count "$cloud_run_services" \
           '.resource_costs.estimated_services += [{"name": $service, "estimated_cost": ($cost | tonumber), "resource_count": ($count | tonumber)}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    # Estimate Compute Engine costs
    local compute_instances=$(gcloud compute instances list --format="value(name)" 2>/dev/null | wc -l)
    if [ "$compute_instances" -gt 0 ]; then
        # Rough estimate: $0.0475 per hour per vCPU (e2-standard-2)
        local compute_cost=$(echo "$compute_instances * 34.20" | bc -l 2>/dev/null || echo "0")
        total_estimated_cost=$(echo "$total_estimated_cost + $compute_cost" | bc -l 2>/dev/null || echo "$total_estimated_cost")
        
        log "Compute Engine: $compute_instances instances - estimated \$$compute_cost/month"
        
        jq --arg service "Compute Engine" \
           --arg cost "$compute_cost" \
           --arg count "$compute_instances" \
           '.resource_costs.estimated_services += [{"name": $service, "estimated_cost": ($cost | tonumber), "resource_count": ($count | tonumber)}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    # Estimate Cloud Storage costs
    local storage_buckets=$(gsutil ls -b 2>/dev/null | wc -l)
    if [ "$storage_buckets" -gt 0 ]; then
        # Rough estimate: $0.020 per GB per month
        local storage_cost=$(echo "$storage_buckets * 5.00" | bc -l 2>/dev/null || echo "0")
        total_estimated_cost=$(echo "$total_estimated_cost + $storage_cost" | bc -l 2>/dev/null || echo "$total_estimated_cost")
        
        log "Cloud Storage: $storage_buckets buckets - estimated \$$storage_cost/month"
        
        jq --arg service "Cloud Storage" \
           --arg cost "$storage_cost" \
           --arg count "$storage_buckets" \
           '.resource_costs.estimated_services += [{"name": $service, "estimated_cost": ($cost | tonumber), "resource_count": ($count | tonumber)}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    # Estimate Firestore costs
    local firestore_databases=$(gcloud firestore databases list --format="value(name)" 2>/dev/null | wc -l)
    if [ "$firestore_databases" -gt 0 ]; then
        # Rough estimate: $0.18 per GB per month
        local firestore_cost=$(echo "$firestore_databases * 10.00" | bc -l 2>/dev/null || echo "0")
        total_estimated_cost=$(echo "$total_estimated_cost + $firestore_cost" | bc -l 2>/dev/null || echo "$total_estimated_cost")
        
        log "Firestore: $firestore_databases databases - estimated \$$firestore_cost/month"
        
        jq --arg service "Firestore" \
           --arg cost "$firestore_cost" \
           --arg count "$firestore_databases" \
           '.resource_costs.estimated_services += [{"name": $service, "estimated_cost": ($cost | tonumber), "resource_count": ($count | tonumber)}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    # Update summary
    jq --arg cost "$total_estimated_cost" \
       '.summary.total_estimated_monthly_cost = ($cost | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    log_success "Basic cost estimation completed: \$$total_estimated_cost estimated monthly cost"
}

# Function to analyze cost optimization opportunities
analyze_cost_optimization() {
    log "🎯 Analyzing cost optimization opportunities..."
    
    local optimization_opportunities=0
    local potential_savings=0
    
    # Check for stopped instances (potential savings)
    local stopped_instances=$(gcloud compute instances list --filter="status!=RUNNING" --format="value(name)" 2>/dev/null | wc -l)
    if [ "$stopped_instances" -gt 0 ]; then
        optimization_opportunities=$((optimization_opportunities + 1))
        local instance_savings=$(echo "$stopped_instances * 20.00" | bc -l 2>/dev/null || echo "0")
        potential_savings=$(echo "$potential_savings + $instance_savings" | bc -l 2>/dev/null || echo "$potential_savings")
        
        log_warning "⚠️  Found $stopped_instances stopped instances - potential savings: \$$instance_savings/month"
        
        jq --arg type "Stopped Instances" \
           --arg count "$stopped_instances" \
           --arg savings "$instance_savings" \
           '.cost_optimization.opportunities += [{"type": $type, "resource_count": ($count | tonumber), "potential_savings": ($savings | tonumber)}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    # Check for orphaned disks
    local orphaned_disks=$(gcloud compute disks list --filter="users=null" --format="value(name)" 2>/dev/null | wc -l)
    if [ "$orphaned_disks" -gt 0 ]; then
        optimization_opportunities=$((optimization_opportunities + 1))
        local disk_savings=$(echo "$orphaned_disks * 5.00" | bc -l 2>/dev/null || echo "0")
        potential_savings=$(echo "$potential_savings + $disk_savings" | bc -l 2>/dev/null || echo "$potential_savings")
        
        log_warning "⚠️  Found $orphaned_disks orphaned disks - potential savings: \$$disk_savings/month"
        
        jq --arg type "Orphaned Disks" \
           --arg count "$orphaned_disks" \
           --arg savings "$disk_savings" \
           '.cost_optimization.opportunities += [{"type": $type, "resource_count": ($count | tonumber), "potential_savings": ($savings | tonumber)}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    # Check for untagged resources
    local untagged_instances=$(gcloud compute instances list --filter="-labels:*" --format="value(name)" 2>/dev/null | wc -l)
    if [ "$untagged_instances" -gt 0 ]; then
        optimization_opportunities=$((optimization_opportunities + 1))
        
        log_warning "⚠️  Found $untagged_instances untagged instances - management issue"
        
        jq --arg type "Untagged Instances" \
           --arg count "$untagged_instances" \
           --arg savings "0" \
           '.cost_optimization.opportunities += [{"type": $type, "resource_count": ($count | tonumber), "potential_savings": ($savings | tonumber)}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    # Check for public buckets
    local public_buckets=0
    if command -v gsutil &> /dev/null; then
        local buckets=$(gsutil ls -b 2>/dev/null)
        for bucket in $buckets; do
            if gsutil iam get "$bucket" 2>/dev/null | grep -q "allUsers\|allAuthenticatedUsers"; then
                public_buckets=$((public_buckets + 1))
            fi
        done
        
        if [ "$public_buckets" -gt 0 ]; then
            optimization_opportunities=$((optimization_opportunities + 1))
            
            log_warning "⚠️  Found $public_buckets public buckets - security and cost risk"
            
            jq --arg type "Public Buckets" \
               --arg count "$public_buckets" \
               --arg savings "0" \
               '.cost_optimization.opportunities += [{"type": $type, "resource_count": ($count | tonumber), "potential_savings": ($savings | tonumber)}]' \
               "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
        fi
    fi
    
    # Update summary
    jq --arg opportunities "$optimization_opportunities" \
       --arg savings "$potential_savings" \
       '.summary.cost_optimization_opportunities = ($opportunities | tonumber) |
        .summary.potential_monthly_savings = ($savings | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    log_success "Cost optimization analysis completed: $optimization_opportunities opportunities, \$$potential_savings potential savings"
}

# Function to generate cost recommendations
generate_cost_recommendations() {
    log "🎯 Generating cost recommendations..."
    
    # Read current results
    local total_cost=$(jq '.summary.total_monthly_cost // .summary.total_estimated_monthly_cost' "$RESULTS_FILE")
    local optimization_opportunities=$(jq '.summary.cost_optimization_opportunities' "$RESULTS_FILE")
    local potential_savings=$(jq '.summary.potential_monthly_savings' "$RESULTS_FILE")
    local total_budgets=$(jq '.summary.total_budgets' "$RESULTS_FILE")
    
    # Initialize recommendations array
    jq '.recommendations = []' "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    # Add recommendations based on findings
    if [ "$total_cost" -gt 100 ]; then
        jq '.recommendations += ["Monthly costs exceed $100 - implement cost monitoring and alerts"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$optimization_opportunities" -gt 0 ]; then
        jq '.recommendations += ["Found '${optimization_opportunities}' cost optimization opportunities - potential savings: $'${potential_savings}'/month"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$total_budgets" -eq 0 ]; then
        jq '.recommendations += ["No budgets configured - set up budget alerts to prevent cost overruns"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    # Add general recommendations
    jq '.recommendations += ["Enable billing export to BigQuery for detailed cost analysis"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    jq '.recommendations += ["Implement resource tagging for better cost allocation"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    jq '.recommendations += ["Set up automated resource cleanup policies"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    jq '.recommendations += ["Review and optimize machine types and storage classes"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    jq '.recommendations += ["Consider using committed use discounts for predictable workloads"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
}

# Main cost analysis function
analyze_costs() {
    log "Starting comprehensive cost analysis for project: $PROJECT_ID"
    
    # Create results file
    RESULTS_FILE="$SCRIPT_DIR/cost_analysis_results.json"
    
    # Initialize results structure
    cat > "$RESULTS_FILE" << EOF
{
  "audit_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project_id": "$PROJECT_ID",
  "project_name": "$PROJECT_NAME",
  "audit_type": "cost_analysis",
  "summary": {
    "total_budgets": 0,
    "total_monthly_cost": 0,
    "total_estimated_monthly_cost": 0,
    "services_with_costs": 0,
    "cost_optimization_opportunities": 0,
    "potential_monthly_savings": 0
  },
  "billing": {
    "account": {},
    "budgets": []
  },
  "resource_costs": {
    "services": [],
    "estimated_services": []
  },
  "cost_optimization": {
    "opportunities": []
  },
  "recommendations": []
}
EOF
    
    # Run all cost analyses
    analyze_billing
    analyze_resource_costs
    analyze_cost_optimization
    
    # Generate recommendations
    generate_cost_recommendations
    
    log_success "Cost analysis completed. Results saved to: $RESULTS_FILE"
}

# Function to show cost summary
show_summary() {
    log "📊 Cost Analysis Summary"
    log "========================="
    
    if [ -f "$RESULTS_FILE" ]; then
        local total_cost=$(jq '.summary.total_monthly_cost // .summary.total_estimated_monthly_cost' "$RESULTS_FILE")
        local optimization_opportunities=$(jq '.summary.cost_optimization_opportunities' "$RESULTS_FILE")
        local potential_savings=$(jq '.summary.potential_monthly_savings' "$RESULTS_FILE")
        local total_budgets=$(jq '.summary.total_budgets' "$RESULTS_FILE")
        
        log "Monthly Cost: \$$total_cost"
        log "Optimization Opportunities: $optimization_opportunities"
        log "Potential Monthly Savings: \$$potential_savings"
        log "Configured Budgets: $total_budgets"
        
        if [ "$total_cost" -gt 100 ]; then
            log_warning "⚠️  High monthly costs - review resource usage"
        fi
        
        if [ "$optimization_opportunities" -gt 0 ]; then
            log_warning "⚠️  Found $optimization_opportunities cost optimization opportunities"
        fi
        
        if [ "$total_budgets" -eq 0 ]; then
            log_warning "⚠️  No budgets configured - set up cost alerts"
        fi
    else
        log_error "Results file not found"
    fi
}

# Main execution
main() {
    log "🚀 Starting Google Cloud Cost Analysis"
    log "======================================"
    
    # Check if jq is available for JSON processing
    if ! command -v jq &> /dev/null; then
        log_error "jq is required for JSON processing. Please install it first."
        exit 1
    fi
    
    # Check if bc is available for calculations
    if ! command -v bc &> /dev/null; then
        log_warning "bc not available - some calculations may be limited"
    fi
    
    # Run the analysis
    analyze_costs
    
    # Show summary
    show_summary
    
    log "✅ Cost analysis completed successfully!"
}

# Run main function
main "$@"
