#!/bin/bash

# reGen Server - Cloud Run Deployment Script
# This script automates the deployment of the reGen server to Google Cloud Run

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required tools
print_info "Checking required tools..."
if ! command_exists gcloud; then
    print_error "gcloud CLI is not installed. Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! command_exists docker; then
    print_error "Docker is not installed. Please install it from: https://docs.docker.com/get-docker/"
    exit 1
fi

print_success "All required tools are installed"

# Get project configuration
print_info "Getting project configuration..."

# Check if PROJECT_ID is set
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$PROJECT_ID" ]; then
        print_error "No GCP project ID set. Set it with: gcloud config set project YOUR_PROJECT_ID"
        exit 1
    fi
fi

# Set default values
SERVICE_NAME=${SERVICE_NAME:-"regen-server"}
REGION=${REGION:-"us-central1"}
MEMORY=${MEMORY:-"1Gi"}
CPU=${CPU:-"1"}
MIN_INSTANCES=${MIN_INSTANCES:-"1"}
MAX_INSTANCES=${MAX_INSTANCES:-"200"}
TIMEOUT=${TIMEOUT:-"3600"}  # Increased for WebSocket voice conversations (max 1 hour)
CONCURRENCY=${CONCURRENCY:-"40"}  # Increased for multiple WebSocket connections

print_info "Project ID: $PROJECT_ID"
print_info "Service Name: $SERVICE_NAME"
print_info "Region: $REGION"

# Ask for deployment method
echo ""
print_info "Select deployment method:"
echo "  1) Quick deploy (using source)"
echo "  2) Build and deploy with Docker (recommended)"
echo "  3) Deploy using Cloud Build"
read -p "Enter choice [1-3]: " deploy_choice

case $deploy_choice in
    1)
        print_info "Deploying using source..."
        gcloud run deploy "$SERVICE_NAME" \
            --source . \
            --region "$REGION" \
            --platform managed \
            --allow-unauthenticated \
            --set-env-vars APP_ENV=prod \
            --min-instances="$MIN_INSTANCES" \
            --max-instances="$MAX_INSTANCES" \
            --memory="$MEMORY" \
            --cpu="$CPU" \
            --timeout="$TIMEOUT" \
            --concurrency="$CONCURRENCY" \
            --port=8000 \
            --no-cpu-throttling
        ;;
    2)
        print_info "Building Docker image..."
        IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/regen-repo/regen-app"
        
        # Create Artifact Registry repository if it doesn't exist
        print_info "Ensuring Artifact Registry repository exists..."
        gcloud artifacts repositories describe regen-repo --location="$REGION" >/dev/null 2>&1 || \
        gcloud artifacts repositories create regen-repo --repository-format=docker --location="$REGION" --description="reGen application repository"
        
        # Configure Docker for Artifact Registry
        print_info "Configuring Docker for Artifact Registry..."
        gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet
        
        # Build the image for linux/amd64 platform (required for Cloud Run, especially on Mac M1/M2)
        print_info "Building for linux/amd64 platform (Cloud Run compatible)..."
        docker build --platform linux/amd64 -t "$IMAGE_NAME" .
        
        print_info "Pushing image to Artifact Registry..."
        docker push "$IMAGE_NAME"
        
        print_info "Deploying to Cloud Run..."
        gcloud run deploy "$SERVICE_NAME" \
            --image "$IMAGE_NAME" \
            --platform managed \
            --region "$REGION" \
            --allow-unauthenticated \
            --min-instances="$MIN_INSTANCES" \
            --max-instances="$MAX_INSTANCES" \
            --memory="$MEMORY" \
            --cpu="$CPU" \
            --no-cpu-throttling \
            --timeout="$TIMEOUT" \
            --concurrency="$CONCURRENCY"
        ;;
    3)
        print_info "Deploying using Cloud Build..."
        gcloud builds submit \
            --config cloudbuild.yaml \
            --substitutions _REGION="$REGION",_MIN_INSTANCES="$MIN_INSTANCES",_MAX_INSTANCES="$MAX_INSTANCES",_MEMORY="$MEMORY",_CPU="$CPU",_TIMEOUT="${TIMEOUT}s",_CONCURRENCY="$CONCURRENCY"
        ;;
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

# Get the service URL
print_info "Getting service URL..."
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format 'value(status.url)')

echo ""
print_success "Deployment completed successfully!"
echo ""
print_info "Service URL: $SERVICE_URL"
print_info "To view logs: gcloud run logs read --service $SERVICE_NAME --region $REGION"
print_info "To set environment variables: gcloud run services update $SERVICE_NAME --region $REGION --set-env-vars KEY=VALUE"
echo ""
print_warning "Remember to set the required environment variables (DATABASE_URL, JWT_SECRET, etc.)"
print_warning "Use: gcloud run services update $SERVICE_NAME --region $REGION --update-secrets DATABASE_URL=database-url:latest"
