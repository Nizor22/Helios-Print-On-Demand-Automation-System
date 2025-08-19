#!/bin/bash

# 🔒 GOOGLE CLOUD SECURITY AUDIT SCRIPT
# Comprehensive security analysis for compliance and risk assessment

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
    echo -e "${BLUE}[Security Audit]${NC} $1"
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

# Function to audit IAM policies
audit_iam() {
    log "🔐 Auditing IAM policies and permissions..."
    
    # Get project IAM policy
    local iam_policy=$(gcloud projects get-iam-policy "$PROJECT_ID" --format="table(bindings.role,bindings.members)" 2>/dev/null || echo "")
    
    if [ -z "$iam_policy" ]; then
        log_error "Failed to retrieve IAM policy"
        return 1
    fi
    
    local total_bindings=0
    local owner_bindings=0
    local admin_bindings=0
    local service_account_bindings=0
    local public_bindings=0
    
    # Process IAM bindings (skip header)
    while IFS= read -r binding_line; do
        if [ -z "$binding_line" ] || echo "$binding_line" | grep -q "ROLE"; then
            continue
        fi
        
        total_bindings=$((total_bindings + 1))
        
        # Parse binding information
        local role=$(echo "$binding_line" | awk '{print $1}')
        local members=$(echo "$binding_line" | awk '{for(i=2;i<=NF;i++) printf "%s ", $i; print ""}')
        
        log "Analyzing IAM binding: $role"
        
        # Check for high-privilege roles
        if echo "$role" | grep -q "owner"; then
            owner_bindings=$((owner_bindings + 1))
            log_warning "⚠️  Owner role found: $role"
        fi
        
        if echo "$role" | grep -q "admin"; then
            admin_bindings=$((admin_bindings + 1))
            log_warning "⚠️  Admin role found: $role"
        fi
        
        # Check for service accounts
        if echo "$members" | grep -q "serviceAccount"; then
            service_account_bindings=$((service_account_bindings + 1))
        fi
        
        # Check for public access
        if echo "$members" | grep -q "allUsers\|allAuthenticatedUsers"; then
            public_bindings=$((public_bindings + 1))
            log_error "❌ Public access found: $role -> $members"
        fi
        
        # Add binding info to results
        jq --arg role "$role" \
           --arg members "$members" \
           --arg high_privilege "$(echo "$role" | grep -q "owner\|admin" && echo "true" || echo "false")" \
           --arg public_access "$(echo "$members" | grep -q "allUsers\|allAuthenticatedUsers" && echo "true" || echo "false")" \
           '.iam.bindings += [{"role": $role, "members": $members, "high_privilege": ($high_privilege | test("true")), "public_access": ($public_access | test("true"))}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
        
    done <<< "$iam_policy"
    
    # Update summary
    jq --arg total "$total_bindings" \
       --arg owners "$owner_bindings" \
       --arg admins "$admin_bindings" \
       --arg service_accounts "$service_account_bindings" \
       --arg public "$public_bindings" \
       '.summary.total_iam_bindings = ($total | tonumber) |
        .summary.owner_role_bindings = ($owners | tonumber) |
        .summary.admin_role_bindings = ($admins | tonumber) |
        .summary.service_account_bindings = ($service_accounts | tonumber) |
        .summary.public_access_bindings = ($public | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    log_success "IAM audit completed: $total_bindings bindings analyzed"
}

# Function to audit service accounts
audit_service_accounts() {
    log "👤 Auditing service accounts..."
    
    # List all service accounts
    local service_accounts=$(gcloud iam service-accounts list --format="table(email,displayName,disabled)" 2>/dev/null || echo "")
    
    if [ -z "$service_accounts" ]; then
        log "No service accounts found"
        return 0
    fi
    
    local total_accounts=0
    local disabled_accounts=0
    local accounts_without_display_name=0
    
    # Process each service account (skip header)
    while IFS= read -r sa_line; do
        if [ -z "$sa_line" ] || echo "$sa_line" | grep -q "EMAIL"; then
            continue
        fi
        
        total_accounts=$((total_accounts + 1))
        
        # Parse service account information
        local email=$(echo "$sa_line" | awk '{print $1}')
        local display_name=$(echo "$sa_line" | awk '{print $2}')
        local disabled=$(echo "$sa_line" | awk '{print $3}')
        
        log "Analyzing service account: $email"
        
        # Check if disabled
        if [ "$disabled" == "True" ]; then
            disabled_accounts=$((disabled_accounts + 1))
            log_warning "⚠️  Disabled service account: $email"
        fi
        
        # Check if has display name
        if [ "$display_name" == "None" ] || [ -z "$display_name" ]; then
            accounts_without_display_name=$((accounts_without_display_name + 1))
            log_warning "⚠️  Service account without display name: $email"
        fi
        
        # Add service account info to results
        jq --arg email "$email" \
           --arg display_name "$display_name" \
           --arg disabled "$disabled" \
           '.service_accounts.accounts += [{"email": $email, "display_name": $display_name, "disabled": ($disabled | test("True"))}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
        
    done <<< "$service_accounts"
    
    # Update summary
    jq --arg total "$total_accounts" \
       --arg disabled "$disabled_accounts" \
       --arg no_display_name "$accounts_without_display_name" \
       '.summary.total_service_accounts = ($total | tonumber) |
        .summary.disabled_service_accounts = ($disabled | tonumber) |
        .summary.service_accounts_without_display_name = ($no_display_name | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    log_success "Service accounts audit completed: $total_accounts accounts analyzed"
}

# Function to audit network security
audit_network_security() {
    log "🌐 Auditing network security..."
    
    # List VPC networks
    local networks=$(gcloud compute networks list --format="table(name,x_gcloud_subnet_mode,autoCreateSubnetworks)" 2>/dev/null || echo "")
    
    if [ -z "$networks" ]; then
        log "No VPC networks found"
        return 0
    fi
    
    local total_networks=0
    local auto_created_networks=0
    
    # Process each network (skip header)
    while IFS= read -r network_line; do
        if [ -z "$network_line" ] || echo "$network_line" | grep -q "NAME"; then
            continue
        fi
        
        total_networks=$((total_networks + 1))
        
        # Parse network information
        local name=$(echo "$network_line" | awk '{print $1}')
        local subnet_mode=$(echo "$network_line" | awk '{print $2}')
        local auto_create=$(echo "$network_line" | awk '{print $3}')
        
        log "Analyzing VPC network: $name"
        
        # Check if auto-created
        if [ "$auto_create" == "True" ]; then
            auto_created_networks=$((auto_created_networks + 1))
            log_warning "⚠️  Auto-created network: $name"
        fi
        
        # Add network info to results
        jq --arg name "$name" \
           --arg subnet_mode "$subnet_mode" \
           --arg auto_create "$auto_create" \
           '.network_security.networks += [{"name": $name, "subnet_mode": $subnet_mode, "auto_created": ($auto_create | test("True"))}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
        
    done <<< "$networks"
    
    # List firewall rules
    local firewall_rules=$(gcloud compute firewall-rules list --format="table(name,network,sourceRanges.list(),allowed[].ports[],direction)" 2>/dev/null || echo "")
    
    if [ -n "$firewall_rules" ]; then
        local total_firewall_rules=0
        local public_firewall_rules=0
        
        # Process each firewall rule (skip header)
        while IFS= read -r firewall_line; do
            if [ -z "$firewall_line" ] || echo "$firewall_line" | grep -q "NAME"; then
                continue
            fi
            
            total_firewall_rules=$((total_firewall_rules + 1))
            
            # Parse firewall rule information
            local name=$(echo "$firewall_line" | awk '{print $1}')
            local network=$(echo "$firewall_line" | awk '{print $2}')
            local source_ranges=$(echo "$firewall_line" | awk '{print $3}')
            local ports=$(echo "$firewall_line" | awk '{print $4}')
            local direction=$(echo "$firewall_line" | awk '{print $5}')
            
            log "Analyzing firewall rule: $name"
            
            # Check for public access
            if echo "$source_ranges" | grep -q "0.0.0.0/0"; then
                public_firewall_rules=$((public_firewall_rules + 1))
                log_warning "⚠️  Public firewall rule: $name (0.0.0.0/0)"
            fi
            
            # Add firewall rule info to results
            jq --arg name "$name" \
               --arg network "$network" \
               --arg source_ranges "$source_ranges" \
               --arg ports "$ports" \
               --arg direction "$direction" \
               --arg public_access "$(echo "$source_ranges" | grep -q "0.0.0.0/0" && echo "true" || echo "false")" \
               '.network_security.firewall_rules += [{"name": $name, "network": $network, "source_ranges": $source_ranges, "ports": $ports, "direction": $direction, "public_access": ($public_access | test("true"))}]' \
               "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
            
        done <<< "$firewall_rules"
        
        # Update summary
        jq --arg total "$total_firewall_rules" \
           --arg public "$public_firewall_rules" \
           '.summary.total_firewall_rules = ($total | tonumber) |
            .summary.public_firewall_rules = ($public | tonumber)' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    # Update network summary
    jq --arg networks "$total_networks" \
       --arg auto_created "$auto_created_networks" \
       '.summary.total_vpc_networks = ($networks | tonumber) |
        .summary.auto_created_networks = ($auto_created | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    log_success "Network security audit completed: $total_networks networks analyzed"
}

# Function to audit Secret Manager
audit_secret_manager() {
    log "🔑 Auditing Secret Manager..."
    
    # Check if Secret Manager API is enabled
    if ! gcloud secrets list --help &> /dev/null; then
        log "Secret Manager API not enabled - skipping audit"
        return 0
    fi
    
    # List all secrets
    local secrets=$(gcloud secrets list --format="table(name,createTime,labels)" 2>/dev/null || echo "")
    
    if [ -z "$secrets" ]; then
        log "No secrets found in Secret Manager"
        return 0
    fi
    
    local total_secrets=0
    local secrets_without_labels=0
    
    # Process each secret (skip header)
    while IFS= read -r secret_line; do
        if [ -z "$secret_line" ] || echo "$secret_line" | grep -q "NAME"; then
            continue
        fi
        
        total_secrets=$((total_secrets + 1))
        
        # Parse secret information
        local name=$(echo "$secret_line" | awk '{print $1}')
        local create_time=$(echo "$secret_line" | awk '{print $2}')
        local labels=$(echo "$secret_line" | awk '{for(i=3;i<=NF;i++) printf "%s ", $i; print ""}')
        
        log "Analyzing secret: $name"
        
        # Check if has labels
        if [ -z "$labels" ] || [ "$labels" == "None" ]; then
            secrets_without_labels=$((secrets_without_labels + 1))
            log_warning "⚠️  Secret without labels: $name"
        fi
        
        # Add secret info to results
        jq --arg name "$name" \
           --arg create_time "$create_time" \
           --arg labels "$labels" \
           --arg has_labels "$(echo "$labels" | grep -q "None\|^$" && echo "false" || echo "true")" \
           '.secret_manager.secrets += [{"name": $name, "create_time": $create_time, "labels": $labels, "has_labels": ($has_labels | test("true"))}]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
        
    done <<< "$secrets"
    
    # Update summary
    jq --arg total "$total_secrets" \
       --arg no_labels "$secrets_without_labels" \
       '.summary.total_secrets = ($total | tonumber) |
        .summary.secrets_without_labels = ($no_labels | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    log_success "Secret Manager audit completed: $total_secrets secrets analyzed"
}

# Function to audit Cloud KMS
audit_cloud_kms() {
    log "🔐 Auditing Cloud KMS..."
    
    # Check if Cloud KMS API is enabled
    if ! gcloud kms --help &> /dev/null; then
        log "Cloud KMS API not enabled - skipping audit"
        return 0
    fi
    
    # Check if Cloud KMS API is actually enabled for the project
    if ! gcloud services list --enabled --filter="config.name=cloudkms.googleapis.com" --format="value(config.name)" | grep -q "cloudkms.googleapis.com"; then
        log "Cloud KMS API not enabled for this project - skipping audit"
        return 0
    fi
    
    # Try to list keyrings with timeout and multiple locations
    local total_keyrings=0
    local total_keys=0
    local locations=("us-central1" "us-east1" "us-west1" "europe-west1" "asia-east1")
    
    for location in "${locations[@]}"; do
        log "Checking Cloud KMS in location: $location"
        
        # Use timeout to prevent hanging
        local keyrings=$(timeout 15s gcloud kms keyrings list --location="$location" --format="table(name,createTime)" 2>/dev/null || echo "")
        
        if [ -n "$keyrings" ] && [ "$keyrings" != "Command timed out or failed" ]; then
            # Process each keyring (skip header)
            while IFS= read -r keyring_line; do
                if [ -z "$keyring_line" ] || echo "$keyring_line" | grep -q "NAME"; then
                    continue
                fi
            
                total_keyrings=$((total_keyrings + 1))
            
                # Parse keyring information
                local name=$(echo "$keyring_line" | awk '{print $1}')
                local create_time=$(echo "$keyring_line" | awk '{print $2}')
            
                log "Analyzing keyring: $name in $location"
            
                # List keys in this keyring with timeout
                local keys=$(timeout 15s gcloud kms keys list --keyring="$name" --location="$location" --format="table(name,primary.name,primary.state,primary.createTime)" 2>/dev/null || echo "")
            
                if [ -n "$keys" ] && [ "$keys" != "Command timed out or failed" ]; then
                    # Process each key (skip header)
                    while IFS= read -r key_line; do
                        if [ -z "$key_line" ] || echo "$key_line" | grep -q "NAME"; then
                            continue
                        fi
                    
                        total_keys=$((total_keys + 1))
                    
                        # Parse key information
                        local key_name=$(echo "$key_line" | awk '{print $1}')
                        local primary_name=$(echo "$key_line" | awk '{print $2}')
                        local state=$(echo "$key_line" | awk '{print $3}')
                        local key_create_time=$(echo "$key_line" | awk '{print $4}')
                    
                        log "  Analyzing key: $key_name ($state)"
                    
                        # Add key info to results
                        jq --arg keyring "$name" \
                           --arg key_name "$key_name" \
                           --arg primary_name "$primary_name" \
                           --arg state "$state" \
                           --arg create_time "$key_create_time" \
                           --arg location "$location" \
                           '.cloud_kms.keys += [{"keyring": $keyring, "key_name": $key_name, "primary_name": $primary_name, "state": $state, "create_time": $create_time, "location": $location}]' \
                           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
                    
                    done <<< "$keys"
                fi
            
                # Add keyring info to results
                jq --arg name "$name" \
                   --arg create_time "$create_time" \
                   --arg location "$location" \
                   '.cloud_kms.keyrings += [{"name": $name, "create_time": $create_time, "location": $location}]' \
                   "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
            
            done <<< "$keyrings"
        else
            log "No keyrings found in $location (or command timed out)"
        fi
    done
    
    # Update summary
    jq --arg keyrings "$total_keyrings" \
       --arg keys "$total_keys" \
       '.summary.total_cloud_kms_keyrings = ($keyrings | tonumber) |
        .summary.total_cloud_kms_keys = ($keys | tonumber)' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    if [ "$total_keyrings" -eq 0 ]; then
        log "No Cloud KMS resources found in any location"
    else
        log_success "Cloud KMS audit completed: $total_keyrings keyrings, $total_keys keys"
    fi
}

# Function to generate security recommendations
generate_security_recommendations() {
    log "🎯 Generating security recommendations..."
    
    # Read current results
    local owner_bindings=$(jq '.summary.owner_role_bindings' "$RESULTS_FILE")
    local admin_bindings=$(jq '.summary.admin_role_bindings' "$RESULTS_FILE")
    local public_access=$(jq '.summary.public_access_bindings' "$RESULTS_FILE")
    local public_firewall=$(jq '.summary.public_firewall_rules' "$RESULTS_FILE")
    local secrets_without_labels=$(jq '.summary.secrets_without_labels' "$RESULTS_FILE")
    
    # Initialize recommendations array
    jq '.recommendations = []' "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    # Add recommendations based on findings
    if [ "$owner_bindings" -gt 0 ]; then
        jq '.recommendations += ["Review and limit '${owner_bindings}' owner role assignments - consider using more restrictive roles"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$admin_bindings" -gt 0 ]; then
        jq '.recommendations += ["Review and limit '${admin_bindings}' admin role assignments - implement principle of least privilege"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$public_access" -gt 0 ]; then
        jq '.recommendations += ["Remove '${public_access}' public access IAM bindings - security risk"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$public_firewall" -gt 0 ]; then
        jq '.recommendations += ["Review '${public_firewall}' public firewall rules - restrict access to specific IP ranges"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    if [ "$secrets_without_labels" -gt 0 ]; then
        jq '.recommendations += ["Add labels to '${secrets_without_labels}' secrets for better organization and security"]' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
    
    # Add general recommendations
    jq '.recommendations += ["Enable Cloud Security Command Center for advanced threat detection"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    jq '.recommendations += ["Implement regular security audits and access reviews"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    jq '.recommendations += ["Enable VPC Service Controls to restrict API access"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    
    jq '.recommendations += ["Set up security monitoring and alerting"]' \
       "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
}

# Main security audit function
audit_security() {
    log "Starting comprehensive security audit for project: $PROJECT_ID"
    
    # Create results file
    RESULTS_FILE="$SCRIPT_DIR/security_audit_results.json"
    
    # Initialize results structure
    cat > "$RESULTS_FILE" << EOF
{
  "audit_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project_id": "$PROJECT_ID",
  "project_name": "$PROJECT_NAME",
  "audit_type": "security_audit",
  "summary": {
    "total_iam_bindings": 0,
    "owner_role_bindings": 0,
    "admin_role_bindings": 0,
    "service_account_bindings": 0,
    "public_access_bindings": 0,
    "total_service_accounts": 0,
    "disabled_service_accounts": 0,
    "service_accounts_without_display_name": 0,
    "total_vpc_networks": 0,
    "auto_created_networks": 0,
    "total_firewall_rules": 0,
    "public_firewall_rules": 0,
    "total_secrets": 0,
    "secrets_without_labels": 0,
    "total_cloud_kms_keyrings": 0,
    "total_cloud_kms_keys": 0
  },
  "iam": {
    "bindings": []
  },
  "service_accounts": {
    "accounts": []
  },
  "network_security": {
    "networks": [],
    "firewall_rules": []
  },
  "secret_manager": {
    "secrets": []
  },
  "cloud_kms": {
    "keyrings": [],
    "keys": []
  },
  "recommendations": []
}
EOF
    
    # Run all security audits
    audit_iam
    audit_service_accounts
    audit_network_security
    audit_secret_manager
    audit_cloud_kms
    
    # Generate recommendations
    generate_security_recommendations
    
    log_success "Security audit completed. Results saved to: $RESULTS_FILE"
}

# Function to show audit summary
show_summary() {
    log "📊 Security Audit Summary"
    log "=========================="
    
    if [ -f "$RESULTS_FILE" ]; then
        local iam_bindings=$(jq '.summary.total_iam_bindings' "$RESULTS_FILE")
        local service_accounts=$(jq '.summary.total_service_accounts' "$RESULTS_FILE")
        local networks=$(jq '.summary.total_vpc_networks' "$RESULTS_FILE")
        local secrets=$(jq '.summary.total_secrets' "$RESULTS_FILE")
        
        log "IAM: $iam_bindings bindings"
        log "Service Accounts: $service_accounts accounts"
        log "VPC Networks: $networks networks"
        log "Secrets: $secrets secrets"
        
        local public_access=$(jq '.summary.public_access_bindings' "$RESULTS_FILE")
        local public_firewall=$(jq '.summary.public_firewall_rules' "$RESULTS_FILE")
        local owner_roles=$(jq '.summary.owner_role_bindings' "$RESULTS_FILE")
        
        if [ "$public_access" -gt 0 ]; then
            log_error "❌ Found $public_access public access IAM bindings - CRITICAL SECURITY RISK"
        fi
        
        if [ "$public_firewall" -gt 0 ]; then
            log_warning "⚠️  Found $public_firewall public firewall rules - security concern"
        fi
        
        if [ "$owner_roles" -gt 0 ]; then
            log_warning "⚠️  Found $owner_roles owner role assignments - review needed"
        fi
    else
        log_error "Results file not found"
    fi
}

# Main execution
main() {
    log "🚀 Starting Google Cloud Security Audit"
    log "======================================="
    
    # Check if jq is available for JSON processing
    if ! command -v jq &> /dev/null; then
        log_error "jq is required for JSON processing. Please install it first."
        exit 1
    fi
    
    # Run the audit
    audit_security
    
    # Show summary
    show_summary
    
    log "✅ Security audit completed successfully!"
}

# Run main function
main "$@"
