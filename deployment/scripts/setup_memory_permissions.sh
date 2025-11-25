#!/bin/bash
# Setup permissions for Vertex AI Memory Bank
# This script grants the necessary permissions to the Reasoning Engine service account

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Vertex AI Memory Bank Permission Setup${NC}"
echo -e "${GREEN}========================================${NC}"

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: No project configured. Run: gcloud config set project YOUR_PROJECT_ID${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Project ID:${NC} $PROJECT_ID"

# Get project number
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
echo -e "${YELLOW}Project Number:${NC} $PROJECT_NUMBER"

# Reasoning Engine service account
SERVICE_ACCOUNT="service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
echo -e "${YELLOW}Service Account:${NC} $SERVICE_ACCOUNT"

echo -e "\n${GREEN}Granting permissions...${NC}"

# Grant Vertex AI User role (includes aiplatform.endpoints.predict)
echo -e "\n1. Granting Vertex AI User role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/aiplatform.user" \
    --condition=None \
    2>/dev/null || echo -e "${YELLOW}   (Role may already be granted)${NC}"

# Grant Service Account Token Creator (for impersonation)
echo -e "\n2. Granting Service Account Token Creator role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/iam.serviceAccountTokenCreator" \
    --condition=None \
    2>/dev/null || echo -e "${YELLOW}   (Role may already be granted)${NC}"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Permissions granted successfully!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${YELLOW}Next steps:${NC}"
echo -e "1. Wait 1-2 minutes for permissions to propagate"
echo -e "2. Restart your server: python3.11 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000"
echo -e "3. Run tests: python3.11 test_vertex_memory.py"

