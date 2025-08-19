#!/bin/bash

# =============================================================================
# PROJECT RESET SCRIPT FOR helios-pod-system
# =============================================================================
# This script systematically cleans all custom-created resources from the
# Google Cloud project to prepare for a fresh, clean deployment.
# =============================================================================

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project configuration
PROJECT_ID="helios-pod-system"
REGION="us-central1"

echo -e "${BLUE}🚀 PROJECT RESET SCRIPT FOR ${PROJECT_ID}${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Function to confirm action
confirm_action() {
    local message="$1"
    echo ""
    echo -e "${YELLOW}⚠️  CONFIRMATION REQUIRED${NC}"
    echo -e "${YELLOW}$message${NC}"
    echo ""
    read -p "Type 'YES' to confirm: " confirmation
    if [ "$confirmation" != "YES" ]; then
        echo -e "${RED}❌ Action cancelled by user${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Confirmed${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

if ! command_exists gcloud; then
    print_error "gcloud CLI is not installed. Please install it first."
    exit 1
fi

if ! command_exists gsutil; then
    print_error "gsutil is not installed. Please install it first."
    exit 1
fi

print_status "Prerequisites check passed"

# Set project context
echo ""
echo -e "${BLUE}🎯 Setting project context...${NC}"
gcloud config set project $PROJECT_ID
print_status "Project set to: $PROJECT_ID"

# Verify project access
echo ""
echo -e "${BLUE}🔐 Verifying project access...${NC}"
if ! gcloud projects describe $PROJECT_ID >/dev/null 2>&1; then
    print_error "Cannot access project $PROJECT_ID. Please check your authentication and permissions."
    exit 1
fi
print_status "Project access verified"

# =============================================================================
# STEP 1: DELETE COMPUTE RESOURCES (CLOUD RUN)
# =============================================================================
echo ""
echo -e "${BLUE}🗑️  STEP 1: DELETING COMPUTE RESOURCES${NC}"
echo "=================================================="

echo -e "${BLUE}🔍 Listing Cloud Run services in $REGION...${NC}"
RUN_SERVICES=$(gcloud run services list --region=$REGION --format="value(METADATA.name)" 2>/dev/null || echo "")

if [ -z "$RUN_SERVICES" ]; then
    print_status "No Cloud Run services found"
else
    echo "Found services:"
    echo "$RUN_SERVICES" | while read service; do
        if [ ! -z "$service" ]; then
            echo "  - $service"
        fi
    done
    
    confirm_action "Delete ALL Cloud Run services in $REGION?"
    
    echo "$RUN_SERVICES" | while read service; do
        if [ ! -z "$service" ]; then
            echo -e "${BLUE}🗑️  Deleting Cloud Run service: $service${NC}"
            gcloud run services delete "$service" --region=$REGION --quiet 2>/dev/null || print_warning "Failed to delete $service"
        fi
    done
    
    print_status "Cloud Run services deletion completed"
fi

# =============================================================================
# STEP 2: DELETE CONTAINER IMAGES
# =============================================================================
echo ""
echo -e "${BLUE}🗑️  STEP 2: DELETING CONTAINER IMAGES${NC}"
echo "=================================================="

echo -e "${BLUE}🔍 Listing container images in GCR...${NC}"
GCR_IMAGES=$(gcloud container images list --repository=gcr.io/$PROJECT_ID --format="value(NAME)" 2>/dev/null || echo "")

if [ -z "$GCR_IMAGES" ]; then
    print_status "No container images found in GCR"
else
    echo "Found images:"
    echo "$GCR_IMAGES" | while read image; do
        if [ ! -z "$image" ]; then
            echo "  - $image"
        fi
    done
    
    confirm_action "Delete ALL container images and tags in GCR?"
    
    echo "$GCR_IMAGES" | while read image; do
        if [ ! -z "$image" ]; then
            echo -e "${BLUE}🗑️  Deleting image: $image${NC}"
            
            # Delete all tags first
            TAGS=$(gcloud container images list-tags "$image" --format="value(TAGS)" 2>/dev/null || echo "")
            if [ ! -z "$TAGS" ]; then
                echo "  Deleting tags for $image..."
                gcloud container images list-tags "$image" --format="value(DIGEST)" | while read digest; do
                    if [ ! -z "$digest" ]; then
                        gcloud container images delete "$image@sha256:$digest" --quiet 2>/dev/null || print_warning "Failed to delete tag $digest"
                    fi
                done
            fi
            
            # Delete the image itself
            gcloud container images delete "$image" --quiet 2>/dev/null || print_warning "Failed to delete image $image"
        fi
    done
    
    print_status "Container images deletion completed"
fi

# =============================================================================
# STEP 3: DELETE STORAGE RESOURCES
# =============================================================================
echo ""
echo -e "${BLUE}🗑️  STEP 3: DELETING STORAGE RESOURCES${NC}"
echo "=================================================="

echo -e "${BLUE}🔍 Checking Cloud Storage buckets...${NC}"
STORAGE_BUCKETS=$(gsutil ls 2>/dev/null || echo "")

if [ -z "$STORAGE_BUCKETS" ]; then
    print_status "No storage buckets found"
else
    echo "Found buckets:"
    echo "$STORAGE_BUCKETS" | while read bucket; do
        if [ ! -z "$bucket" ]; then
            echo "  - $bucket"
        fi
    done
    
    # Check for the specific bucket we want to delete
    if echo "$STORAGE_BUCKETS" | grep -q "gs://helios-product-assets-658997361183"; then
        echo ""
        echo -e "${YELLOW}⚠️  CRITICAL STORAGE DELETION${NC}"
        confirm_action "EMPTY AND DELETE the bucket gs://helios-product-assets-658997361183? This will remove ALL product assets!"
        
        echo -e "${BLUE}🗑️  Emptying bucket: gs://helios-product-assets-658997361183${NC}"
        gsutil -m rm -r "gs://helios-product-assets-658997361183/**" 2>/dev/null || print_warning "Failed to empty bucket"
        
        echo -e "${BLUE}🗑️  Deleting bucket: gs://helios-product-assets-658997361183${NC}"
        gsutil rb "gs://helios-product-assets-658997361183" 2>/dev/null || print_warning "Failed to delete bucket"
        
        print_status "Product assets bucket deleted"
    else
        print_status "Product assets bucket not found (already deleted)"
    fi
    
    # Note: We're NOT deleting the _cloudbuild bucket as instructed
    print_info "Preserving gs://helios-pod-system_cloudbuild/ (Cloud Build bucket)"
fi

# =============================================================================
# STEP 4: DELETE OTHER SERVICES
# =============================================================================
echo ""
echo -e "${BLUE}🗑️  STEP 4: DELETING OTHER SERVICES${NC}"
echo "=================================================="

# Delete Cloud Scheduler job
echo -e "${BLUE}🔍 Checking Cloud Scheduler jobs...${NC}"
SCHEDULER_JOBS=$(gcloud scheduler jobs list --location=$REGION --format="value(NAME)" 2>/dev/null || echo "")

if [ -z "$SCHEDULER_JOBS" ]; then
    print_status "No Cloud Scheduler jobs found"
else
    echo "Found jobs:"
    echo "$SCHEDULER_JOBS" | while read job; do
        if [ ! -z "$job" ]; then
            echo "  - $job"
        fi
    done
    
    confirm_action "Delete ALL Cloud Scheduler jobs in $REGION?"
    
    echo "$SCHEDULER_JOBS" | while read job; do
        if [ ! -z "$job" ]; then
            echo -e "${BLUE}🗑️  Deleting scheduler job: $job${NC}"
            gcloud scheduler jobs delete "$job" --location=$REGION --quiet 2>/dev/null || print_warning "Failed to delete job $job"
        fi
    done
    
    print_status "Cloud Scheduler jobs deletion completed"
fi

# Delete Secret Manager secrets
echo ""
echo -e "${BLUE}🔍 Checking Secret Manager secrets...${NC}"
SECRETS=$(gcloud secrets list --format="value(NAME)" 2>/dev/null || echo "")

if [ -z "$SECRETS" ]; then
    print_status "No secrets found in Secret Manager"
else
    echo "Found secrets:"
    echo "$SECRETS" | while read secret; do
        if [ ! -z "$secret" ]; then
            echo "  - $secret"
        fi
    done
    
    confirm_action "Delete ALL secrets from Secret Manager? This will remove ALL API keys and credentials!"
    
    echo "$SECRETS" | while read secret; do
        if [ ! -z "$secret" ]; then
            echo -e "${BLUE}🗑️  Deleting secret: $secret${NC}"
            gcloud secrets delete "$secret" --quiet 2>/dev/null || print_warning "Failed to delete secret $secret"
        fi
    done
    
    print_status "Secret Manager secrets deletion completed"
fi

# =============================================================================
# STEP 5: FINAL VERIFICATION
# =============================================================================
echo ""
echo -e "${BLUE}🔍 STEP 5: FINAL VERIFICATION${NC}"
echo "=================================================="

echo -e "${BLUE}🔍 Verifying Cloud Run services...${NC}"
REMAINING_RUN=$(gcloud run services list --region=$REGION --format="value(METADATA.name)" 2>/dev/null || echo "")
if [ -z "$REMAINING_RUN" ]; then
    print_status "✅ No Cloud Run services remaining"
else
    print_warning "⚠️  Remaining Cloud Run services:"
    echo "$REMAINING_RUN" | while read service; do
        if [ ! -z "$service" ]; then
            echo "  - $service"
        fi
    done
fi

echo ""
echo -e "${BLUE}🔍 Verifying container images...${NC}"
REMAINING_IMAGES=$(gcloud container images list --repository=gcr.io/$PROJECT_ID --format="value(NAME)" 2>/dev/null || echo "")
if [ -z "$REMAINING_IMAGES" ]; then
    print_status "✅ No container images remaining"
else
    print_warning "⚠️  Remaining container images:"
    echo "$REMAINING_IMAGES" | while read image; do
        if [ ! -z "$image" ]; then
            echo "  - $image"
        fi
    done
fi

echo ""
echo -e "${BLUE}🔍 Verifying storage buckets...${NC}"
REMAINING_BUCKETS=$(gsutil ls 2>/dev/null || echo "")
if [ -z "$REMAINING_BUCKETS" ]; then
    print_status "✅ No storage buckets remaining"
else
    print_warning "⚠️  Remaining storage buckets:"
    echo "$REMAINING_BUCKETS" | while read bucket; do
        if [ ! -z "$bucket" ]; then
            echo "  - $bucket"
        fi
    done
fi

echo ""
echo -e "${BLUE}🔍 Verifying Cloud Scheduler jobs...${NC}"
REMAINING_JOBS=$(gcloud scheduler jobs list --location=$REGION --format="value(NAME)" 2>/dev/null || echo "")
if [ -z "$REMAINING_JOBS" ]; then
    print_status "✅ No Cloud Scheduler jobs remaining"
else
    print_warning "⚠️  Remaining Cloud Scheduler jobs:"
    echo "$REMAINING_JOBS" | while read job; do
        if [ ! -z "$job" ]; then
            echo "  - $job"
        fi
    done
fi

echo ""
echo -e "${BLUE}🔍 Verifying Secret Manager secrets...${NC}"
REMAINING_SECRETS=$(gcloud secrets list --format="value(NAME)" 2>/dev/null || echo "")
if [ -z "$REMAINING_SECRETS" ]; then
    print_status "✅ No secrets remaining"
else
    print_warning "⚠️  Remaining secrets:"
    echo "$REMAINING_SECRETS" | while read secret; do
        if [ ! -z "$secret" ]; then
            echo "  - $secret"
        fi
    done
fi

# =============================================================================
# COMPLETION SUMMARY
# =============================================================================
echo ""
echo -e "${GREEN}🎉 PROJECT RESET COMPLETED!${NC}"
echo "=================================================="
echo ""
echo -e "${BLUE}📋 Summary of actions performed:${NC}"
echo "  ✅ Cloud Run services deleted"
echo "  ✅ Container images and tags deleted"
echo "  ✅ Product assets bucket deleted"
echo "  ✅ Cloud Scheduler jobs deleted"
echo "  ✅ Secret Manager secrets deleted"
echo ""
echo -e "${BLUE}🔧 Next steps:${NC}"
echo "  1. Recreate necessary secrets (API keys, tokens)"
echo "  2. Redeploy your services with clean configurations"
echo "  3. Test the new autonomous workflow system"
echo ""
echo -e "${GREEN}✨ Your project is now clean and ready for fresh deployment!${NC}"




