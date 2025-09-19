#!/bin/bash
# Setup script for Claude CI authentication with Google Cloud

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
SERVICE_ACCOUNT_NAME="claude-ci-bot"
KEY_FILE="claude-ci-key.json"

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: No project ID provided and no default project set.${NC}"
    echo "Usage: $0 [PROJECT_ID]"
    echo "Or set default project: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo -e "${GREEN}Setting up Claude CI authentication for project: ${PROJECT_ID}${NC}"

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo -e "${RED}Error: Not authenticated with gcloud. Please run:${NC}"
    echo "gcloud auth login"
    exit 1
fi

# Create service account
echo -e "${YELLOW}Creating service account: ${SERVICE_ACCOUNT_NAME}${NC}"
if gcloud iam service-accounts describe "${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" &>/dev/null; then
    echo "Service account already exists"
else
    gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
        --description="Service account for Claude CI bot" \
        --display-name="Claude CI Bot" \
        --project="$PROJECT_ID"
fi

# Grant necessary permissions
echo -e "${YELLOW}Granting permissions${NC}"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user" \
    --quiet

# Optional: Add additional roles if needed
# gcloud projects add-iam-policy-binding "$PROJECT_ID" \
#     --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
#     --role="roles/ml.developer" \
#     --quiet

# Create service account key
echo -e "${YELLOW}Creating service account key: ${KEY_FILE}${NC}"
if [ -f "$KEY_FILE" ]; then
    echo -e "${YELLOW}Warning: ${KEY_FILE} already exists. Backing up to ${KEY_FILE}.bak${NC}"
    mv "$KEY_FILE" "${KEY_FILE}.bak"
fi

gcloud iam service-accounts keys create "$KEY_FILE" \
    --iam-account="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --project="$PROJECT_ID"

# Set permissions on key file
chmod 600 "$KEY_FILE"

echo -e "${GREEN}✅ Setup complete!${NC}"
echo
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Test the authentication:"
echo "   export GOOGLE_APPLICATION_CREDENTIALS=\"$(pwd)/${KEY_FILE}\""
echo "   export ANTHROPIC_VERTEX_PROJECT_ID=\"${PROJECT_ID}\""
echo "   export CLAUDE_CODE_USE_VERTEX=1"
echo "   python claude_cli.py --version"
echo
echo "2. For CI/CD, you'll need to:"
echo "   - Store the contents of ${KEY_FILE} as a secret (e.g., GCP_SA_KEY)"
echo "   - Store the project ID as a secret (e.g., GCP_PROJECT_ID): ${PROJECT_ID}"
echo "   - Base64 encode the key file for some platforms:"
echo "     base64 -i ${KEY_FILE}"
echo
echo -e "${YELLOW}Security note:${NC}"
echo "- Keep ${KEY_FILE} secure and never commit it to version control"
echo "- Consider adding ${KEY_FILE} to your .gitignore"
echo "- Rotate the key periodically for better security"

# Add to .gitignore if it exists
if [ -f ".gitignore" ]; then
    if ! grep -q "claude-ci-key.json" .gitignore; then
        echo "claude-ci-key.json" >> .gitignore
        echo -e "${GREEN}Added ${KEY_FILE} to .gitignore${NC}"
    fi
fi

