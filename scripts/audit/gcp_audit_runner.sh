#!/bin/bash

# 🚀 HELIOS GOOGLE CLOUD PROJECT AUDIT RUNNER
# Comprehensive audit script for cost optimization, security, and performance

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
AUDIT_DIR="$SCRIPT_DIR"
LOG_DIR="$PROJECT_ROOT/logs/audit"
REPORT_DIR="$PROJECT_ROOT/reports/audit"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Ensure directories exist
mkdir -p "$LOG_DIR" "$REPORT_DIR"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_DIR/audit_$TIMESTAMP.log"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_DIR/audit_$TIMESTAMP.log"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_DIR/audit_$TIMESTAMP.log"
}

log_error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_DIR/audit_$TIMESTAMP.log"
}

# Check prerequisites
check_prerequisites() {
    log "🔍 Checking prerequisites..."
    
    # Check if gcloud is installed
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
    
    log_success "Prerequisites check passed"
}

# Get project information
get_project_info() {
    log "📋 Gathering project information..."
    
    PROJECT_ID=$(gcloud config get-value project)
    PROJECT_NAME=$(gcloud projects describe "$PROJECT_ID" --format="value(name)")
    BILLING_ACCOUNT=$(gcloud billing projects describe "$PROJECT_ID" --format="value(billingAccountName)" 2>/dev/null || echo "Not set")
    
    log "Project ID: $PROJECT_ID"
    log "Project Name: $PROJECT_NAME"
    log "Billing Account: $BILLING_ACCOUNT"
    
    # Save project info for other scripts
    cat > "$AUDIT_DIR/project_info.env" << EOF
PROJECT_ID="$PROJECT_ID"
PROJECT_NAME="$PROJECT_NAME"
BILLING_ACCOUNT="$BILLING_ACCOUNT"
TIMESTAMP="$TIMESTAMP"
EOF
    
    log_success "Project information gathered"
}

# Run API audit
run_api_audit() {
    log "🔌 Running API audit..."
    
    if [ -f "$AUDIT_DIR/api_audit.sh" ]; then
        bash "$AUDIT_DIR/api_audit.sh" 2>&1 | tee -a "$LOG_DIR/audit_$TIMESTAMP.log"
        log_success "API audit completed"
    else
        log_warning "API audit script not found"
    fi
}

# Run storage audit
run_storage_audit() {
    log "🗄️ Running storage audit..."
    
    if [ -f "$AUDIT_DIR/storage_audit.sh" ]; then
        bash "$AUDIT_DIR/storage_audit.sh" 2>&1 | tee -a "$LOG_DIR/audit_$TIMESTAMP.log"
        log_success "Storage audit completed"
    else
        log_warning "Storage audit script not found"
    fi
}

# Run compute audit
run_compute_audit() {
    log "💻 Running compute audit..."
    
    if [ -f "$AUDIT_DIR/compute_audit.sh" ]; then
        bash "$AUDIT_DIR/compute_audit.sh" 2>&1 | tee -a "$LOG_DIR/audit_$TIMESTAMP.log"
        log_success "Compute audit completed"
    else
        log_warning "Compute audit script not found"
    fi
}

# Run container audit
run_container_audit() {
    log "🐳 Running container audit..."
    
    if [ -f "$AUDIT_DIR/container_audit.sh" ]; then
        bash "$AUDIT_DIR/container_audit.sh" 2>&1 | tee -a "$LOG_DIR/audit_$TIMESTAMP.log"
        log_success "Container audit completed"
    else
        log_warning "Container audit script not found"
    fi
}

# Run security audit
run_security_audit() {
    log "🔒 Running security audit..."
    
    if [ -f "$AUDIT_DIR/security_audit.sh" ]; then
        bash "$AUDIT_DIR/security_audit.sh" 2>&1 | tee -a "$LOG_DIR/audit_$TIMESTAMP.log"
        log_success "Security audit completed"
    else
        log_warning "Security audit script not found"
    fi
}

# Run cost analysis
run_cost_analysis() {
    log "💰 Running cost analysis..."
    
    if [ -f "$AUDIT_DIR/cost_analysis.sh" ]; then
        bash "$AUDIT_DIR/cost_analysis.sh" 2>&1 | tee -a "$LOG_DIR/audit_$TIMESTAMP.log"
        log_success "Cost analysis completed"
    else
        log_warning "Cost analysis script not found"
    fi
}

# Generate comprehensive report
generate_report() {
    log "📊 Generating comprehensive audit report..."
    
    REPORT_FILE="$REPORT_DIR/audit_report_$TIMESTAMP.md"
    
    cat > "$REPORT_FILE" << EOF
# 🚀 HELIOS GOOGLE CLOUD PROJECT AUDIT REPORT

**Generated**: $(date)
**Project**: $PROJECT_NAME ($PROJECT_ID)
**Audit ID**: $TIMESTAMP

## 📋 Executive Summary

This report contains the results of a comprehensive Google Cloud Project audit for the Helios autonomous store system.

## 🔍 Audit Components

EOF
    
    # Add individual audit results
    for audit_type in api storage compute container security cost; do
        if [ -f "$AUDIT_DIR/${audit_type}_audit_results.json" ]; then
            # Capitalize first letter for display
            local audit_title
            case $audit_type in
                api) audit_title="API" ;;
                storage) audit_title="Storage" ;;
                compute) audit_title="Compute" ;;
                container) audit_title="Container" ;;
                security) audit_title="Security" ;;
                cost) audit_title="Cost" ;;
                *) audit_title="$audit_type" ;;
            esac
            
            echo "### $audit_title Audit Results" >> "$REPORT_FILE"
            echo "\`\`\`json" >> "$REPORT_FILE"
            cat "$AUDIT_DIR/${audit_type}_audit_results.json" >> "$REPORT_FILE"
            echo "\`\`\`" >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
        fi
    done
    
    # Add recommendations
    cat >> "$REPORT_FILE" << EOF

## 🎯 Recommendations

### Immediate Actions
- Review and address any critical security findings
- Clean up unused resources identified in the audit
- Optimize over-provisioned resources

### Short-term Optimizations (1-2 weeks)
- Implement resource tagging strategy
- Set up automated cleanup policies
- Configure cost monitoring and alerts

### Long-term Improvements (1-2 months)
- Establish regular audit schedule
- Implement infrastructure as code
- Set up automated compliance checks

## 📊 Cost Impact

*Cost analysis results will be populated here*

## 🔒 Security Findings

*Security audit results will be populated here*

## 📈 Performance Metrics

*Performance analysis results will be populated here*

---

**Report generated by Helios GCP Audit Runner v1.0**
EOF
    
    log_success "Comprehensive report generated: $REPORT_FILE"
}

# Main execution
main() {
    log "🚀 Starting Helios Google Cloud Project Audit"
    log "================================================"
    
    # Check prerequisites
    check_prerequisites
    
    # Get project information
    get_project_info
    
    # Run all audits
    run_api_audit
    run_storage_audit
    run_compute_audit
    run_container_audit
    run_security_audit
    run_cost_analysis
    
    # Generate report
    generate_report
    
    log "🎉 Audit completed successfully!"
    log "📁 Logs: $LOG_DIR/audit_$TIMESTAMP.log"
    log "📊 Report: $REPORT_DIR/audit_report_$TIMESTAMP.md"
    log "================================================"
}

# Run main function
main "$@"
