#!/bin/bash

# AI Agent Deployment Script for Helios Autonomous Store
# This script deploys the AI-enhanced version of Helios to Google Cloud Run

set -e

echo "🤖 Deploying Helios AI Agent System to Google Cloud Run"
echo "=================================================="

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"helios-pod-system"}
REGION=${GOOGLE_CLOUD_REGION:-"us-central1"}
SERVICE_NAME="helios-ai-agent"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
MEMORY="2Gi"
CPU="2"
MIN_INSTANCES="1"
MAX_INSTANCES="10"
TIMEOUT="300s"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "🔍 Checking prerequisites..."

if ! command_exists gcloud; then
    echo -e "${RED}❌ gcloud CLI not found. Please install Google Cloud SDK.${NC}"
    exit 1
fi

if ! command_exists docker; then
    echo -e "${RED}❌ Docker not found. Please install Docker.${NC}"
    exit 1
fi

# Load environment variables
if [ -f "ai_agent.env" ]; then
    echo "📋 Loading AI agent environment variables..."
    export $(cat ai_agent.env | grep -v '^#' | xargs)
else
    echo -e "${YELLOW}⚠️  ai_agent.env file not found. Using defaults...${NC}"
fi

# Authenticate with Google Cloud
echo "🔐 Authenticating with Google Cloud..."
gcloud auth configure-docker --quiet

# Set project
echo "📁 Setting project to ${PROJECT_ID}..."
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "🔧 Enabling required Google Cloud APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    aiplatform.googleapis.com \
    artifactregistry.googleapis.com \
    --quiet

# Build Docker image
echo "🏗️  Building Docker image with AI enhancements..."
docker build \
    --build-arg ENABLE_AI_AGENT=true \
    --build-arg PYTHON_VERSION=3.13.6 \
    -t ${IMAGE_NAME}:latest \
    -t ${IMAGE_NAME}:$(date +%Y%m%d-%H%M%S) \
    -f deployment/docker/Dockerfile.ai \
    .

# Push to Google Container Registry
echo "📤 Pushing image to Google Container Registry..."
docker push ${IMAGE_NAME}:latest

# Create/Update secrets
echo "🔒 Managing secrets in Google Secret Manager..."

# Function to create or update secret
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2
    
    if gcloud secrets describe ${secret_name} --project=${PROJECT_ID} >/dev/null 2>&1; then
        echo "   Updating secret: ${secret_name}"
        echo -n "${secret_value}" | gcloud secrets versions add ${secret_name} --data-file=-
    else
        echo "   Creating secret: ${secret_name}"
        echo -n "${secret_value}" | gcloud secrets create ${secret_name} --data-file=-
    fi
}

# Create secrets for AI agent
if [ ! -z "${GEMINI_API_KEY}" ]; then
    create_or_update_secret "gemini-api-key" "${GEMINI_API_KEY}"
fi

if [ ! -z "${GOOGLE_MCP_AUTH_TOKEN}" ]; then
    create_or_update_secret "mcp-auth-token" "${GOOGLE_MCP_AUTH_TOKEN}"
fi

if [ ! -z "${SERPAPI_API_KEY}" ]; then
    create_or_update_secret "serpapi-key" "${SERPAPI_API_KEY}"
fi

# Deploy to Cloud Run
echo "🚀 Deploying AI-enhanced Helios to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --region ${REGION} \
    --platform managed \
    --memory ${MEMORY} \
    --cpu ${CPU} \
    --min-instances ${MIN_INSTANCES} \
    --max-instances ${MAX_INSTANCES} \
    --timeout ${TIMEOUT} \
    --port 8080 \
    --allow-unauthenticated \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
    --set-env-vars="GOOGLE_CLOUD_REGION=${REGION}" \
    --set-env-vars="USE_AI_AGENT=true" \
    --set-env-vars="USE_AI_ORCHESTRATION=true" \
    --set-env-vars="USE_AI_INSIGHTS=true" \
    --set-env-vars="GOOGLE_MCP_URL=${GOOGLE_MCP_URL}" \
    --set-env-vars="ENABLE_GOOGLE_TRENDS_TOOL=true" \
    --set-env-vars="ENABLE_SOCIAL_MEDIA_SCANNER=true" \
    --set-env-vars="ENABLE_NEWS_ANALYZER=true" \
    --set-env-vars="ENABLE_COMPETITOR_INTELLIGENCE=true" \
    --set-env-vars="MIN_OPPORTUNITY_SCORE=${MIN_OPPORTUNITY_SCORE:-7.0}" \
    --set-env-vars="MIN_AUDIENCE_CONFIDENCE=${MIN_AUDIENCE_CONFIDENCE:-0.7}" \
    --set-env-vars="AI_CONFIDENCE_THRESHOLD=${AI_CONFIDENCE_THRESHOLD:-0.7}" \
    --set-secrets="GEMINI_API_KEY=gemini-api-key:latest" \
    --set-secrets="GOOGLE_MCP_AUTH_TOKEN=mcp-auth-token:latest" \
    --set-secrets="SERPAPI_API_KEY=serpapi-key:latest" \
    --service-account="${SERVICE_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --quiet

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')

# Deploy additional AI services if needed
echo "🔧 Checking additional AI service deployments..."

# Deploy MCP server if not already deployed
if ! gcloud run services describe helios-mcp --region ${REGION} >/dev/null 2>&1; then
    echo "📡 Deploying MCP server..."
    cd mcp && ./deploy-mcp.sh && cd ..
fi

# Set up Cloud Scheduler for AI-enhanced workflows
echo "⏰ Setting up Cloud Scheduler for AI workflows..."
gcloud scheduler jobs create http helios-ai-discovery \
    --location ${REGION} \
    --schedule "0 */6 * * *" \
    --http-method POST \
    --uri "${SERVICE_URL}/api/v1/discover-trends" \
    --oidc-service-account-email "${SERVICE_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --attempt-deadline 30m \
    --quiet || echo "   Scheduler job already exists"

# Create monitoring dashboard
echo "📊 Setting up monitoring dashboard..."
cat > monitoring-dashboard.json << EOF
{
  "displayName": "Helios AI Agent Dashboard",
  "mosaicLayout": {
    "columns": 3,
    "tiles": [
      {
        "width": 1,
        "height": 1,
        "widget": {
          "title": "AI Trend Analysis Performance",
          "scorecard": {
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "metric.type=\"custom.googleapis.com/ai_trend_analysis\"",
                "aggregation": {
                  "alignmentPeriod": "60s",
                  "perSeriesAligner": "ALIGN_MEAN"
                }
              }
            }
          }
        }
      },
      {
        "width": 1,
        "height": 1,
        "widget": {
          "title": "Product Success Predictions",
          "scorecard": {
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "metric.type=\"custom.googleapis.com/product_predictions\"",
                "aggregation": {
                  "alignmentPeriod": "60s",
                  "perSeriesAligner": "ALIGN_RATE"
                }
              }
            }
          }
        }
      },
      {
        "width": 1,
        "height": 1,
        "widget": {
          "title": "AI Agent Errors",
          "scorecard": {
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/user/ai_agent_errors\"",
                "aggregation": {
                  "alignmentPeriod": "300s",
                  "perSeriesAligner": "ALIGN_SUM"
                }
              }
            }
          }
        }
      }
    ]
  }
}
EOF

# Create the dashboard
gcloud monitoring dashboards create --config-from-file=monitoring-dashboard.json || echo "   Dashboard already exists"
rm monitoring-dashboard.json

# Final summary
echo ""
echo "✅ AI Agent Deployment Complete!"
echo "================================"
echo ""
echo "📌 Service URL: ${SERVICE_URL}"
echo "📊 Monitoring: https://console.cloud.google.com/monitoring"
echo "📝 Logs: https://console.cloud.google.com/logs"
echo ""
echo "🤖 AI Features Enabled:"
echo "   - Intelligent trend discovery with MCP"
echo "   - Vertex AI pattern recognition"
echo "   - AI-powered product generation"
echo "   - Predictive success analysis"
echo ""
echo "⚙️  Configuration:"
echo "   - Min instances: ${MIN_INSTANCES}"
echo "   - Max instances: ${MAX_INSTANCES}"
echo "   - Memory: ${MEMORY}"
echo "   - CPU: ${CPU}"
echo ""
echo "🔍 Next steps:"
echo "   1. Verify AI agent is running: curl ${SERVICE_URL}/health"
echo "   2. Check AI status: curl ${SERVICE_URL}/api/v1/ai-status"
echo "   3. Monitor performance in Cloud Console"
echo "   4. Review logs for AI decisions"
echo ""
echo "📚 Documentation: See AI_AGENT_README.md for detailed information"