#!/bin/bash
# ============================================================================
# Quick Environment Setup Script
# ============================================================================
# This script helps you create a .env file with the required configuration
# ============================================================================

set -e

echo "============================================================================"
echo "🚀 ADK Multi-Agent Framework - Environment Setup"
echo "============================================================================"
echo ""

# Check if .env already exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Setup cancelled. Keeping existing .env file."
        exit 0
    fi
fi

# Copy template
echo "📋 Creating .env from template..."
cp .env.example .env

echo ""
echo "============================================================================"
echo "📝 Required Configuration"
echo "============================================================================"
echo ""

# Get Google API Key
echo "1️⃣  GOOGLE_API_KEY"
echo "   Get your API key from: https://aistudio.google.com/app/apikey"
echo ""
read -p "   Enter your Google API Key: " GOOGLE_API_KEY

if [ -z "$GOOGLE_API_KEY" ]; then
    echo "❌ Error: Google API Key is required!"
    exit 1
fi

# Get Google Cloud Project
echo ""
echo "2️⃣  GOOGLE_CLOUD_PROJECT"
echo "   Find your project ID at: https://console.cloud.google.com/"
echo ""
read -p "   Enter your Google Cloud Project ID: " GOOGLE_CLOUD_PROJECT

if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "❌ Error: Google Cloud Project ID is required!"
    exit 1
fi

# Update .env file
echo ""
echo "💾 Updating .env file..."

# macOS compatible sed
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/GOOGLE_API_KEY=.*/GOOGLE_API_KEY=$GOOGLE_API_KEY/" .env
    sed -i '' "s/GOOGLE_CLOUD_PROJECT=.*/GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT/" .env
else
    # Linux
    sed -i "s/GOOGLE_API_KEY=.*/GOOGLE_API_KEY=$GOOGLE_API_KEY/" .env
    sed -i "s/GOOGLE_CLOUD_PROJECT=.*/GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT/" .env
fi

echo ""
echo "============================================================================"
echo "✅ Environment Setup Complete!"
echo "============================================================================"
echo ""
echo "Your .env file has been created with:"
echo "  ✅ GOOGLE_API_KEY: ${GOOGLE_API_KEY:0:20}..."
echo "  ✅ GOOGLE_CLOUD_PROJECT: $GOOGLE_CLOUD_PROJECT"
echo ""
echo "Optional: Edit .env to customize other settings (Redis, logging, etc.)"
echo ""
echo "Next steps:"
echo "  1. Run tests: python test_adk_runner.py"
echo "  2. Start services: docker compose --profile dev up -d"
echo "  3. Open ADK Web: http://localhost:3002"
echo ""
echo "============================================================================"

