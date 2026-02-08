#!/bin/bash

# Google Cloud Storage Bucket Setup Script for reGen
# This script creates and configures a GCS bucket for storing documentary assets

set -e  # Exit on error

# Configuration
PROJECT_ID="${GCP_PROJECT_ID}"
BUCKET_NAME="regen_assets"
REGION="us-central1"
STORAGE_CLASS="STANDARD"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}reGen GCS Bucket Setup${NC}"
echo -e "${GREEN}================================${NC}"

# Check if gcloud CLI is installed
if ! command -v gsutil &> /dev/null; then
    echo -e "${RED}Error: gsutil (Google Cloud SDK) is not installed.${NC}"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if PROJECT_ID is set
if [ -z "$PROJECT_ID" ]; then
    echo -e "${YELLOW}GCP_PROJECT_ID environment variable not set.${NC}"
    read -p "Enter your GCP Project ID: " PROJECT_ID
fi

echo -e "${GREEN}Creating GCS bucket: gs://${BUCKET_NAME}${NC}"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Storage Class: $STORAGE_CLASS"
echo ""

# Create the bucket
echo -e "${GREEN}Step 1: Creating bucket...${NC}"
if gsutil ls -b gs://${BUCKET_NAME} 2>/dev/null; then
    echo -e "${YELLOW}Bucket gs://${BUCKET_NAME} already exists.${NC}"
else
    gsutil mb \
        -p "$PROJECT_ID" \
        -l "$REGION" \
        -c "$STORAGE_CLASS" \
        gs://${BUCKET_NAME}
    echo -e "${GREEN}✓ Bucket created successfully${NC}"
fi

# Apply CORS configuration
echo -e "${GREEN}Step 2: Applying CORS configuration...${NC}"
CORS_FILE="$(dirname "$0")/../cors.json"

if [ ! -f "$CORS_FILE" ]; then
    echo -e "${YELLOW}CORS file not found at $CORS_FILE. Creating it...${NC}"
    cat > "$CORS_FILE" << 'EOF'
[
  {
    "origin": ["*"],
    "method": ["GET", "HEAD"],
    "responseHeader": ["Content-Type", "Range"],
    "maxAgeSeconds": 3600
  }
]
EOF
fi

gsutil cors set "$CORS_FILE" gs://${BUCKET_NAME}
echo -e "${GREEN}✓ CORS configuration applied${NC}"

# Set bucket permissions for public read (optional)
echo -e "${GREEN}Step 3: Setting bucket permissions...${NC}"
read -p "Do you want to make assets publicly accessible? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    gsutil iam ch allUsers:objectViewer gs://${BUCKET_NAME}
    echo -e "${GREEN}✓ Bucket set to public read${NC}"
else
    echo -e "${YELLOW}Skipping public access. Assets will require signed URLs.${NC}"
fi

# Create folder structure
echo -e "${GREEN}Step 4: Creating folder structure...${NC}"
echo "" | gsutil cp - gs://${BUCKET_NAME}/assets/.keep
echo -e "${GREEN}✓ Folder structure created${NC}"

# Verify setup
echo -e "${GREEN}Step 5: Verifying setup...${NC}"
gsutil ls -L -b gs://${BUCKET_NAME}

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Bucket URL: gs://${BUCKET_NAME}"
echo "Public URL: https://storage.googleapis.com/${BUCKET_NAME}/"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Add GCS_BUCKET_NAME=${BUCKET_NAME} to your .env file"
echo "2. Add GCP_PROJECT_ID=${PROJECT_ID} to your .env file"
echo "3. Ensure service account credentials are configured"
echo ""
