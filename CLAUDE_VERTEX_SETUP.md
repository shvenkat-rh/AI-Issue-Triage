# Claude Code with Vertex AI Setup Guide

This guide explains how to set up the Claude CLI to work with Google Cloud Platform's Vertex AI.

## Prerequisites

1. **Google Cloud Project**: You need a GCP project with Vertex AI enabled
2. **Authentication**: Proper GCP credentials configured
3. **Model Access**: Access to Claude models in Vertex AI Model Garden

## Environment Setup

### 1. Set Required Environment Variables

Add these to your shell configuration file (`~/.zshrc`, `~/.bashrc`, etc.):

```bash
# Required for Vertex AI
export ANTHROPIC_VERTEX_PROJECT_ID=your-gcp-project-id
export CLAUDE_CODE_USE_VERTEX=1
export CLOUD_ML_REGION=us-east5  # Default region for Claude Code

# Optional: For direct Anthropic API (alternative to Vertex AI)
# export ANTHROPIC_API_KEY=your-anthropic-api-key
```

### 2. Authenticate with Google Cloud

#### For Local Development

```bash
# Install Google Cloud SDK if not already installed
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth application-default login

# Set your project (replace with your actual project ID)
gcloud config set project your-gcp-project-id
```

#### For CI/CD Environments (Service Account)

For automated environments like CI/CD pipelines, use service account authentication:

```bash
# 1. Create a service account
gcloud iam service-accounts create claude-ci-bot \
    --description="Service account for Claude CI bot" \
    --display-name="Claude CI Bot"

# 2. Grant necessary permissions
gcloud projects add-iam-policy-binding your-gcp-project-id \
    --member="serviceAccount:claude-ci-bot@your-gcp-project-id.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# 3. Create and download service account key
gcloud iam service-accounts keys create claude-ci-key.json \
    --iam-account=claude-ci-bot@your-gcp-project-id.iam.gserviceaccount.com

# 4. Set environment variable for authentication
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/claude-ci-key.json"
```

#### CI/CD Platform Examples

**GitHub Actions:**
```yaml
# Store the service account key as a GitHub secret: GCP_SA_KEY
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v1
  with:
    credentials_json: ${{ secrets.GCP_SA_KEY }}

- name: Set up environment
  run: |
    echo "ANTHROPIC_VERTEX_PROJECT_ID=${{ secrets.GCP_PROJECT_ID }}" >> $GITHUB_ENV
    echo "CLAUDE_CODE_USE_VERTEX=1" >> $GITHUB_ENV
    echo "CLOUD_ML_REGION=us-east5" >> $GITHUB_ENV
```

**GitLab CI:**
```yaml
variables:
  GOOGLE_APPLICATION_CREDENTIALS: /tmp/gcp-key.json
  ANTHROPIC_VERTEX_PROJECT_ID: $GCP_PROJECT_ID
  CLAUDE_CODE_USE_VERTEX: "1"
  CLOUD_ML_REGION: us-east5

before_script:
  - echo $GCP_SA_KEY | base64 -d > $GOOGLE_APPLICATION_CREDENTIALS
```

**Jenkins:**
```groovy
withCredentials([file(credentialsId: 'gcp-service-account', variable: 'GCP_KEY_FILE')]) {
    sh '''
        export GOOGLE_APPLICATION_CREDENTIALS=$GCP_KEY_FILE
        export ANTHROPIC_VERTEX_PROJECT_ID=${GCP_PROJECT_ID}
        export CLAUDE_CODE_USE_VERTEX=1
        export CLOUD_ML_REGION=us-east5
        python claude_cli.py --title "CI Analysis" --description "Automated analysis"
    '''
}
```

### 3. Enable Required APIs

```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Enable other required APIs
gcloud services enable cloudresourcemanager.googleapis.com
gcloud services enable compute.googleapis.com
```

### 4. Verify Model Access

1. Go to [Vertex AI Model Garden](https://console.cloud.google.com/vertex-ai/model-garden)
2. Search for "Claude" models
3. Ensure you have access to:
   - Claude 3.5 Sonnet
   - Claude 3.5 Haiku (optional)

## Usage

Once configured, the Claude CLI will automatically detect and use Vertex AI:

```bash
# The CLI will automatically use Vertex AI when ANTHROPIC_VERTEX_PROJECT_ID is set
python claude_cli.py --title "Bug report" --description "Detailed description"

# Interactive mode
python claude_cli.py

# Help
python claude_cli.py --help
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   ```bash
   # Re-authenticate
   gcloud auth application-default login
   ```

2. **Region Issues**
   ```bash
   # Claude Code is currently available in us-east5
   export CLOUD_ML_REGION=us-east5
   ```

3. **Project ID Issues**
   ```bash
   # Verify your project ID
   gcloud config get-value project
   
   # Set correct project
   gcloud config set project your-correct-project-id
   ```

4. **Model Access Issues**
   - Check Vertex AI Model Garden for Claude model availability
   - Ensure your project has the necessary quotas
   - Contact your GCP admin for model access permissions

### Verification

Test your setup with:

```bash
# Check environment variables
echo $ANTHROPIC_VERTEX_PROJECT_ID
echo $CLAUDE_CODE_USE_VERTEX
echo $CLOUD_ML_REGION

# Test Claude CLI
python claude_cli.py --version
```

## Switching Between Vertex AI and Direct API

The analyzer supports both configurations:

### Use Vertex AI (Recommended for GCP users)
```bash
export ANTHROPIC_VERTEX_PROJECT_ID=your-project-id
export CLAUDE_CODE_USE_VERTEX=1
unset ANTHROPIC_API_KEY  # Remove direct API key
```

### Use Direct Anthropic API
```bash
export ANTHROPIC_API_KEY=your-api-key
unset ANTHROPIC_VERTEX_PROJECT_ID  # Remove Vertex AI config
unset CLAUDE_CODE_USE_VERTEX
```

## CI/CD Integration Examples

### Required Secrets/Variables

For any CI/CD platform, you'll need these secrets:

- `GCP_SA_KEY`: Base64 encoded service account JSON key
- `GCP_PROJECT_ID`: Your Google Cloud Project ID

### Complete GitHub Actions Example

See `.github/workflows/claude-ci-analysis.yml` for a complete example that:
- Analyzes GitHub issues and pull requests automatically
- Posts analysis results as comments
- Adds labels based on analysis
- Stores analysis results as artifacts

### Docker Container Example

```dockerfile
FROM python:3.11-slim

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . /app
WORKDIR /app

# Set up service account authentication
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-key.json
ENV ANTHROPIC_VERTEX_PROJECT_ID=${GCP_PROJECT_ID}
ENV CLAUDE_CODE_USE_VERTEX=1
ENV CLOUD_ML_REGION=us-east5

# Run analysis
CMD ["python", "claude_cli.py", "--file", "issue.txt", "--format", "json"]
```

### Kubernetes Job Example

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: claude-analysis
spec:
  template:
    spec:
      containers:
      - name: claude-analyzer
        image: your-registry/claude-analyzer:latest
        env:
        - name: GOOGLE_APPLICATION_CREDENTIALS
          value: /etc/gcp/key.json
        - name: ANTHROPIC_VERTEX_PROJECT_ID
          valueFrom:
            secretKeyRef:
              name: gcp-config
              key: project-id
        - name: CLAUDE_CODE_USE_VERTEX
          value: "1"
        - name: CLOUD_ML_REGION
          value: us-east5
        volumeMounts:
        - name: gcp-key
          mountPath: /etc/gcp
          readOnly: true
      volumes:
      - name: gcp-key
        secret:
          secretName: gcp-service-account-key
      restartPolicy: Never
```

## Support

- [Anthropic Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code/google-vertex-ai)
- [Google Cloud Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Google Cloud SDK Documentation](https://cloud.google.com/sdk/docs)
- [Service Account Authentication](https://cloud.google.com/docs/authentication/getting-started)
