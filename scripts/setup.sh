#!/bin/bash

# 🚀 HELIOS GOOGLE CLOUD AUDIT SYSTEM SETUP
# Easy setup and configuration script

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Logging function
log() {
    echo -e "${BLUE}[Setup]${NC} $1"
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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install dependencies
install_dependencies() {
    log "🔧 Installing dependencies..."
    
    local missing_tools=()
    
    # Check gcloud CLI
    if ! command_exists gcloud; then
        missing_tools+=("gcloud")
    fi
    
    # Check jq
    if ! command_exists jq; then
        missing_tools+=("jq")
    fi
    
    # Check bc (optional)
    if ! command_exists bc; then
        log_warning "bc not found - some calculations may be limited"
    fi
    
    # Install missing tools
    if [ ${#missing_tools[@]} -gt 0 ]; then
        log "Installing missing tools: ${missing_tools[*]}"
        
        # Detect OS
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            if command_exists brew; then
                for tool in "${missing_tools[@]}"; do
                    if [ "$tool" = "gcloud" ]; then
                        log "Installing gcloud CLI..."
                        curl https://sdk.cloud.google.com | bash
                        exec -l $SHELL
                    else
                        log "Installing $tool..."
                        brew install "$tool"
                    fi
                done
            else
                log_error "Homebrew not found. Please install Homebrew first:"
                log_error "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                exit 1
            fi
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux
            if command_exists apt-get; then
                # Ubuntu/Debian
                log "Updating package list..."
                sudo apt-get update
                
                for tool in "${missing_tools[@]}"; do
                    if [ "$tool" = "gcloud" ]; then
                        log "Installing gcloud CLI..."
                        curl https://sdk.cloud.google.com | bash
                        exec -l $SHELL
                    else
                        log "Installing $tool..."
                        sudo apt-get install -y "$tool"
                    fi
                done
            elif command_exists yum; then
                # CentOS/RHEL
                for tool in "${missing_tools[@]}"; do
                    if [ "$tool" = "gcloud" ]; then
                        log "Installing gcloud CLI..."
                        curl https://sdk.cloud.google.com | bash
                        exec -l $SHELL
                    else
                        log "Installing $tool..."
                        sudo yum install -y "$tool"
                    fi
                done
            else
                log_error "Unsupported Linux distribution. Please install manually:"
                log_error "  gcloud: https://cloud.google.com/sdk/docs/install"
                log_error "  jq: https://stedolan.github.io/jq/download/"
                exit 1
            fi
        else
            log_error "Unsupported operating system: $OSTYPE"
            exit 1
        fi
    else
        log_success "All required tools are already installed"
    fi
}

# Function to setup Google Cloud authentication
setup_gcloud() {
    log "🔐 Setting up Google Cloud authentication..."
    
    # Check if already authenticated
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_success "Already authenticated with Google Cloud"
        return 0
    fi
    
    # Check if project is set
    local current_project=$(gcloud config get-value project 2>/dev/null || echo "")
    
    if [ -z "$current_project" ]; then
        log "No project is set. Please set your project ID:"
        read -p "Enter your Google Cloud Project ID: " project_id
        
        if [ -n "$project_id" ]; then
            gcloud config set project "$project_id"
            log_success "Project set to: $project_id"
        else
            log_error "Project ID is required"
            exit 1
        fi
    fi
    
    # Authenticate
    log "Please authenticate with Google Cloud..."
    gcloud auth login
    
    # Verify authentication
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_success "Successfully authenticated with Google Cloud"
    else
        log_error "Authentication failed"
        exit 1
    fi
}

# Function to make scripts executable
make_scripts_executable() {
    log "🔧 Making scripts executable..."
    
    # Make audit scripts executable
    chmod +x "$SCRIPT_DIR"/audit/*.sh 2>/dev/null || true
    chmod +x "$SCRIPT_DIR"/cleanup/*.sh 2>/dev/null || true
    
    log_success "Scripts made executable"
}

# Function to create necessary directories
create_directories() {
    log "📁 Creating necessary directories..."
    
    # Create logs directory
    mkdir -p "$PROJECT_ROOT/logs/audit"
    mkdir -p "$PROJECT_ROOT/reports/audit"
    
    log_success "Directories created"
}

# Function to verify setup
verify_setup() {
    log "🔍 Verifying setup..."
    
    local all_good=true
    
    # Check gcloud
    if ! command_exists gcloud; then
        log_error "gcloud CLI not found"
        all_good=false
    else
        log_success "gcloud CLI found"
    fi
    
    # Check jq
    if ! command_exists jq; then
        log_error "jq not found"
        all_good=false
    else
        log_success "jq found"
    fi
    
    # Check authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Not authenticated with Google Cloud"
        all_good=false
    else
        log_success "Google Cloud authentication verified"
    fi
    
    # Check project
    local project=$(gcloud config get-value project 2>/dev/null || echo "")
    if [ -z "$project" ]; then
        log_error "No project is set"
        all_good=false
    else
        log_success "Project set to: $project"
    fi
    
    # Check script permissions
    if [ ! -x "$SCRIPT_DIR/audit/gcp_audit_runner.sh" ]; then
        log_error "Main audit runner not executable"
        all_good=false
    else
        log_success "Main audit runner is executable"
    fi
    
    if [ "$all_good" = true ]; then
        log_success "Setup verification completed successfully!"
        return 0
    else
        log_error "Setup verification failed. Please fix the issues above."
        return 1
    fi
}

# Function to run test audit
run_test_audit() {
    log "🧪 Running test audit..."
    
    if [ -x "$SCRIPT_DIR/audit/gcp_audit_runner.sh" ]; then
        log "Running comprehensive audit (this may take several minutes)..."
        bash "$SCRIPT_DIR/audit/gcp_audit_runner.sh"
        
        if [ $? -eq 0 ]; then
            log_success "Test audit completed successfully!"
        else
            log_error "Test audit failed"
            return 1
        fi
    else
        log_error "Main audit runner not found or not executable"
        return 1
    fi
}

# Function to show next steps
show_next_steps() {
    log "🎯 Setup completed! Here are your next steps:"
    echo ""
    echo "1. 📊 Run regular audits:"
    echo "   bash scripts/audit/gcp_audit_runner.sh"
    echo ""
    echo "2. 🧹 Clean up resources (preview first):"
    echo "   bash scripts/cleanup/storage_cleanup.sh --dry-run"
    echo "   bash scripts/cleanup/api_cleanup.sh --dry-run"
    echo ""
    echo "3. 📈 Monitor costs and performance regularly"
    echo ""
    echo "4. 🔒 Review security findings and address issues"
    echo ""
    echo "📚 For more information, see: scripts/README.md"
    echo ""
    echo "🚀 Happy auditing!"
}

# Function to show help
show_help() {
    echo "🚀 Helios Google Cloud Audit System Setup"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --install-deps          Install required dependencies"
    echo "  --setup-auth            Setup Google Cloud authentication"
    echo "  --verify                Verify the setup"
    echo "  --test                  Run a test audit"
    echo "  --full                  Complete setup (default)"
    echo "  --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      # Complete setup"
    echo "  $0 --install-deps       # Install dependencies only"
    echo "  $0 --verify             # Verify setup only"
    echo "  $0 --test               # Run test audit"
    echo ""
}

# Parse command line arguments
parse_args() {
    local install_deps=false
    local setup_auth=false
    local verify=false
    local test=false
    local full_setup=true
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --install-deps)
                install_deps=true
                full_setup=false
                shift
                ;;
            --setup-auth)
                setup_auth=true
                full_setup=false
                shift
                ;;
            --verify)
                verify=true
                full_setup=false
                shift
                ;;
            --test)
                test=true
                full_setup=false
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
    
    # Execute requested operations
    if [ "$full_setup" = true ]; then
        log "🚀 Starting complete setup..."
        install_dependencies
        setup_gcloud
        make_scripts_executable
        create_directories
        verify_setup
        show_next_steps
    else
        if [ "$install_deps" = true ]; then
            install_dependencies
        fi
        
        if [ "$setup_auth" = true ]; then
            setup_gcloud
        fi
        
        if [ "$verify" = true ]; then
            verify_setup
        fi
        
        if [ "$test" = true ]; then
            run_test_audit
        fi
    fi
}

# Main execution
main() {
    log "🚀 Welcome to Helios Google Cloud Audit System Setup!"
    log "====================================================="
    
    # Check if running from correct directory
    if [ ! -f "$SCRIPT_DIR/audit/gcp_audit_runner.sh" ]; then
        log_error "Setup script must be run from the scripts directory"
        log_error "Current directory: $SCRIPT_DIR"
        exit 1
    fi
    
    # Parse arguments and execute
    parse_args "$@"
    
    log "🎉 Setup completed successfully!"
}

# Run main function
main "$@"
