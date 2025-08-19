#!/bin/bash

# 🧹 GOOGLE CLOUD STORAGE CLEANUP SCRIPT
# Automated cleanup of unused and orphaned storage resources

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
    echo -e "${BLUE}[Storage Cleanup]${NC} $1"
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
DRY_RUN=${DRY_RUN:-false}
CLEANUP_ORPHANED_DISKS=${CLEANUP_ORPHANED_DISKS:-true}
CLEANUP_OLD_SNAPSHOTS=${CLEANUP_OLD_SNAPSHOTS:-true}
CLEANUP_UNTAGGED_IMAGES=${CLEANUP_UNTAGGED_IMAGES:-true}
CLEANUP_OLD_BACKUPS=${CLEANUP_OLD_BACKUPS:-true}
SNAPSHOT_RETENTION_DAYS=${SNAPSHOT_RETENTION_DAYS:-30}
BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-90}

# Function to confirm cleanup
confirm_cleanup() {
    if [ "$DRY_RUN" = "true" ]; then
        log "🔍 DRY RUN MODE - No resources will be deleted"
        return 0
    fi
    
    echo -e "${YELLOW}⚠️  WARNING: This script will DELETE resources from your Google Cloud project!${NC}"
    echo -e "${YELLOW}Project: $PROJECT_NAME ($PROJECT_ID)${NC}"
    echo ""
    echo "The following cleanup operations will be performed:"
    echo "- Remove orphaned Compute Engine disks"
    echo "- Delete old snapshots (older than $SNAPSHOT_RETENTION_DAYS days)"
    echo "- Clean up untagged container images"
    echo "- Remove old backups (older than $BACKUP_RETENTION_DAYS days)"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " confirmation
    
    if [ "$confirmation" != "yes" ]; then
        log "Cleanup cancelled by user"
        exit 0
    fi
    
    log "Cleanup confirmed - proceeding with resource deletion"
}

# Function to cleanup orphaned disks
cleanup_orphaned_disks() {
    if [ "$CLEANUP_ORPHANED_DISKS" != "true" ]; then
        log "Skipping orphaned disk cleanup (disabled)"
        return 0
    fi
    
    log "🔍 Finding orphaned Compute Engine disks..."
    
    # Find disks with no attached instances
    local orphaned_disks=$(gcloud compute disks list --filter="users=null" --format="table(name,sizeGb,zone)" 2>/dev/null || echo "")
    
    if [ -z "$orphaned_disks" ]; then
        log "No orphaned disks found"
        return 0
    fi
    
    local total_disks=0
    local total_size_gb=0
    local deleted_disks=0
    
    # Process each orphaned disk (skip header)
    while IFS= read -r disk_line; do
        if [ -z "$disk_line" ] || echo "$disk_line" | grep -q "NAME"; then
            continue
        fi
        
        total_disks=$((total_disks + 1))
        
        # Parse disk information
        local name=$(echo "$disk_line" | awk '{print $1}')
        local size_gb=$(echo "$disk_line" | awk '{print $2}')
        local zone=$(echo "$disk_line" | awk '{print $3}')
        
        log "Found orphaned disk: $name (${size_gb}GB) in $zone"
        total_size_gb=$((total_size_gb + size_gb))
        
        if [ "$DRY_RUN" = "true" ]; then
            log "  [DRY RUN] Would delete disk: $name"
        else
            log "  Deleting disk: $name"
            if gcloud compute disks delete "$name" --zone="$zone" --quiet 2>/dev/null; then
                deleted_disks=$((deleted_disks + 1))
                log_success "  Successfully deleted disk: $name"
            else
                log_error "  Failed to delete disk: $name"
            fi
        fi
        
    done <<< "$orphaned_disks"
    
    if [ "$total_disks" -gt 0 ]; then
        if [ "$DRY_RUN" = "true" ]; then
            log "DRY RUN: Would delete $total_disks orphaned disks (${total_size_gb}GB total)"
        else
            log_success "Deleted $deleted_disks out of $total_disks orphaned disks (${total_size_gb}GB total)"
        fi
    fi
}

# Function to cleanup old snapshots
cleanup_old_snapshots() {
    if [ "$CLEANUP_OLD_SNAPSHOTS" != "true" ]; then
        log "Skipping old snapshot cleanup (disabled)"
        return 0
    fi
    
    log "🔍 Finding old Compute Engine snapshots..."
    
    # Calculate cutoff date
            local cutoff_date
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            cutoff_date=$(date -v-"$SNAPSHOT_RETENTION_DAYS"d +%Y-%m-%d)
        else
            # Linux
            cutoff_date=$(date -d "$SNAPSHOT_RETENTION_DAYS days ago" -I)
        fi
    log "Removing snapshots older than: $cutoff_date"
    
    # Find old snapshots
    local old_snapshots=$(gcloud compute snapshots list --filter="creationTimestamp<$cutoff_date" --format="table(name,diskSizeGb,creationTimestamp)" 2>/dev/null || echo "")
    
    if [ -z "$old_snapshots" ]; then
        log "No old snapshots found"
        return 0
    fi
    
    local total_snapshots=0
    local total_size_gb=0
    local deleted_snapshots=0
    
    # Process each old snapshot (skip header)
    while IFS= read -r snapshot_line; do
        if [ -z "$snapshot_line" ] || echo "$snapshot_line" | grep -q "NAME"; then
            continue
        fi
        
        total_snapshots=$((total_snapshots + 1))
        
        # Parse snapshot information
        local name=$(echo "$snapshot_line" | awk '{print $1}')
        local size_gb=$(echo "$snapshot_line" | awk '{print $2}')
        local creation_time=$(echo "$snapshot_line" | awk '{print $3}')
        
        log "Found old snapshot: $name (${size_gb}GB) created: $creation_time"
        total_size_gb=$((total_size_gb + size_gb))
        
        if [ "$DRY_RUN" = "true" ]; then
            log "  [DRY RUN] Would delete snapshot: $name"
        else
            log "  Deleting snapshot: $name"
            if gcloud compute snapshots delete "$name" --quiet 2>/dev/null; then
                deleted_snapshots=$((deleted_snapshots + 1))
                log_success "  Successfully deleted snapshot: $name"
            else
                log_error "  Failed to delete snapshot: $name"
            fi
        fi
        
    done <<< "$old_snapshots"
    
    if [ "$total_snapshots" -gt 0 ]; then
        if [ "$DRY_RUN" = "true" ]; then
            log "DRY RUN: Would delete $total_snapshots old snapshots (${total_size_gb}GB total)"
        else
            log_success "Deleted $deleted_snapshots out of $total_snapshots old snapshots (${total_size_gb}GB total)"
        fi
    fi
}

# Function to cleanup untagged container images
cleanup_untagged_images() {
    if [ "$CLEANUP_UNTAGGED_IMAGES" != "true" ]; then
        log "Skipping untagged image cleanup (disabled)"
        return 0
    fi
    
    log "🔍 Finding untagged container images..."
    
    # Check if gcloud container images command is available
    if ! gcloud container images list --help &> /dev/null; then
        log_warning "gcloud container images command not available - skipping untagged image cleanup"
        return 1
    fi
    
    # List all repositories in GCR
    local repositories=$(gcloud container images list --repository=gcr.io/"$PROJECT_ID" --format="table(name)" 2>/dev/null || echo "")
    
    if [ -z "$repositories" ]; then
        log "No GCR repositories found"
        return 0
    fi
    
    local total_images=0
    local deleted_images=0
    
    # Process each repository (skip header)
    while IFS= read -r repo_line; do
        if [ -z "$repo_line" ] || echo "$repo_line" | grep -q "NAME"; then
            continue
        fi
        
        local repo_name="$repo_line"
        log "Checking repository: $repo_name"
        
        # Find untagged images in this repository
        local untagged_images=$(gcloud container images list-tags "$repo_name" --format="table(tags,timestamp.datetime,digest)" --limit=100 2>/dev/null | grep "^[[:space:]]*[0-9]" | head -10 || echo "")
        
        if [ -n "$untagged_images" ]; then
            # Process each untagged image
            while IFS= read -r image_line; do
                if [ -z "$image_line" ]; then
                    continue
                fi
                
                total_images=$((total_images + 1))
                
                # Extract digest
                local digest=$(echo "$image_line" | awk '{print $3}')
                
                if [ -n "$digest" ]; then
                    log "  Found untagged image: $digest"
                    
                    if [ "$DRY_RUN" = "true" ]; then
                        log "    [DRY RUN] Would delete image: $repo_name@$digest"
                    else
                        log "    Deleting image: $repo_name@$digest"
                        if gcloud container images delete "$repo_name@$digest" --quiet 2>/dev/null; then
                            deleted_images=$((deleted_images + 1))
                            log_success "    Successfully deleted image: $digest"
                        else
                            log_error "    Failed to delete image: $digest"
                        fi
                    fi
                fi
                
            done <<< "$untagged_images"
        fi
        
    done <<< "$repositories"
    
    if [ "$total_images" -gt 0 ]; then
        if [ "$DRY_RUN" = "true" ]; then
            log "DRY RUN: Would delete $total_images untagged images"
        else
            log_success "Deleted $deleted_images out of $total_images untagged images"
        fi
    fi
}

# Function to cleanup old backups
cleanup_old_backups() {
    if [ "$CLEANUP_OLD_BACKUPS" != "true" ]; then
        log "Skipping old backup cleanup (disabled)"
        return 0
    fi
    
    log "🔍 Finding old Cloud SQL backups..."
    
    # Check if Cloud SQL API is accessible
    if ! gcloud sql --help &> /dev/null; then
        log_warning "Cloud SQL API not accessible - skipping backup cleanup"
        return 1
    fi
    
    # Calculate cutoff date
            local cutoff_date
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            cutoff_date=$(date -v-"$BACKUP_RETENTION_DAYS"d +%Y-%m-%d)
        else
            # cutoff_date=$(date -d "$BACKUP_RETENTION_DAYS days ago" -I)
        fi
    log "Removing backups older than: $cutoff_date"
    
    # List Cloud SQL instances
    local instances=$(gcloud sql instances list --format="value(name)" 2>/dev/null || echo "")
    
    if [ -z "$instances" ]; then
        log "No Cloud SQL instances found"
        return 0
    fi
    
    local total_backups=0
    local deleted_backups=0
    
    # Process each instance
    while IFS= read -r instance; do
        if [ -z "$instance" ]; then
            continue
        fi
        
        log "Checking backups for instance: $instance"
        
        # List backups for this instance
        local backups=$(gcloud sql backups list --instance="$instance" --format="table(id,startTime,status)" 2>/dev/null || echo "")
        
        if [ -n "$backups" ]; then
            # Process each backup (skip header)
            while IFS= read -r backup_line; do
                if [ -z "$backup_line" ] || echo "$backup_line" | grep -q "ID"; then
                    continue
                fi
            
                # Parse backup information
                local backup_id=$(echo "$backup_line" | awk '{print $1}')
                local start_time=$(echo "$backup_line" | awk '{print $2}')
                local status=$(echo "$backup_line" | awk '{print $3}')
                
                # Check if backup is old
                if [ -n "$start_time" ] && [ "$start_time" != "None" ]; then
                    local backup_date=$(echo "$start_time" | cut -d'T' -f1)
                    if [ "$backup_date" \< "$cutoff_date" ]; then
                        total_backups=$((total_backups + 1))
                        log "  Found old backup: $backup_id (started: $start_time)"
                        
                        if [ "$DRY_RUN" = "true" ]; then
                            log "    [DRY RUN] Would delete backup: $backup_id"
                        else
                            log "    Deleting backup: $backup_id"
                            if gcloud sql backups delete "$backup_id" --instance="$instance" --quiet 2>/dev/null; then
                                deleted_backups=$((deleted_backups + 1))
                                log_success "    Successfully deleted backup: $backup_id"
                            else
                                log_error "    Failed to delete backup: $backup_id"
                            fi
                        fi
                    fi
                fi
                
            done <<< "$backups"
        fi
        
    done <<< "$instances"
    
    if [ "$total_backups" -gt 0 ]; then
        if [ "$DRY_RUN" = "true" ]; then
            log "DRY RUN: Would delete $total_backups old backups"
        else
            log_success "Deleted $deleted_backups out of $total_backups old backups"
        fi
    fi
}

# Function to show cleanup summary
show_summary() {
    log "📊 Storage Cleanup Summary"
    log "=========================="
    
    if [ "$DRY_RUN" = "true" ]; then
        log "🔍 DRY RUN COMPLETED - No resources were actually deleted"
        log "Review the output above to see what would be cleaned up"
        log "Run with DRY_RUN=false to perform actual cleanup"
    else
        log "🧹 CLEANUP COMPLETED - Resources have been deleted"
        log "Review the output above to see what was cleaned up"
    fi
    
    log ""
    log "To run this script again:"
    log "  DRY_RUN=true bash $0    # Preview what would be deleted"
    log "  DRY_RUN=false bash $0   # Actually delete resources"
}

# Main cleanup function
main_cleanup() {
    log "🚀 Starting Google Cloud Storage Cleanup"
    log "========================================"
    log "Project: $PROJECT_NAME ($PROJECT_ID)"
    log "Dry Run: $DRY_RUN"
    log ""
    
    # Confirm cleanup (unless dry run)
    confirm_cleanup
    
    # Run all cleanup operations
    cleanup_orphaned_disks
    cleanup_old_snapshots
    cleanup_untagged_images
    cleanup_old_backups
    
    # Show summary
    show_summary
    
    log "✅ Storage cleanup completed!"
}

# Show help
show_help() {
    echo "🧹 Google Cloud Storage Cleanup Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dry-run              Preview what would be deleted (default)"
    echo "  --execute              Actually delete resources"
    echo "  --help                 Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  DRY_RUN                    Set to 'false' to actually delete resources"
    echo "  CLEANUP_ORPHANED_DISKS     Enable/disable orphaned disk cleanup (default: true)"
    echo "  CLEANUP_OLD_SNAPSHOTS      Enable/disable old snapshot cleanup (default: true)"
    echo "  CLEANUP_UNTAGGED_IMAGES    Enable/disable untagged image cleanup (default: true)"
    echo "  CLEANUP_OLD_BACKUPS        Enable/disable old backup cleanup (default: true)"
    echo "  SNAPSHOT_RETENTION_DAYS    Days to keep snapshots (default: 30)"
    echo "  BACKUP_RETENTION_DAYS      Days to keep backups (default: 90)"
    echo ""
    echo "Examples:"
    echo "  $0 --dry-run              # Preview cleanup (safe)"
    echo "  $0 --execute              # Perform cleanup"
    echo "  DRY_RUN=false $0          # Perform cleanup (alternative)"
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
