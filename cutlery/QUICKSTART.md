# AI Issue Triage Workflows - Quick Start Guide

Welcome! This guide will help you set up automated AI-powered issue analysis for your GitHub repository.

## 📁 Files in This Directory

This `cutlery/` directory contains everything you need to get started:

```
cutlery/
├── QUICKSTART.md                              # This guide
├── workflows/                                 # GitHub Actions workflows
│   ├── gemini-issue-analysis.yml             # Auto: Single issue analysis
│   ├── gemini-labeled-issue-analysis.yml     # Label: Single issue analysis  
│   ├── ai-bulk-issue-analysis.yml            # Auto: Bulk issue analysis
│   └── ai-bulk-labeled-issue-analysis.yml    # Label: Bulk issue analysis
├── triage.config.json                        # Example configuration file
└── samples/                                  # Sample files for testing
    ├── sample_issue.txt                      # Example issue for testing
    ├── sample_issues.json                    # Multiple test issues
    ├── sample-prompt.txt                     # Example custom prompt
    └── env_example.txt                       # Environment variables template
```


## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Setup Steps](#setup-steps)
- [Configuration](#configuration)
- [Usage](#usage)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)

---

## Overview

This system provides **four automated workflows** in two categories:

### Automatic Workflows (All Issues)

1. **Single Issue Analysis** (`gemini-issue-analysis.yml`)
   - Triggers when a new issue is opened
   - Analyzes **every new issue** automatically
   - Provides AI-powered insights, root cause analysis, and solutions
   - Includes prompt injection security checks

2. **Bulk Issue Analysis** (`ai-bulk-issue-analysis.yml`)
   - Triggers when a PR is merged to main
   - Processes **all open issues** (oldest → newest)
   - Smart duplicate detection: compares each issue against previously analyzed ones
   - Re-analyzes all open issues with updated codebase context
   - Posts new analysis comments with fresh insights

### Label-Based Workflows (Selective Analysis) 🎯 NEW!

3. **Labeled Issue Analysis** (`gemini-labeled-issue-analysis.yml`)
   - Triggers when an issue is **labeled** and opened with "Gemini Analyze" label
   - Analyzes **only issues with the "Gemini Analyze" label**
   - Same comprehensive analysis as automatic workflow
   - Perfect for manual triage and cost control

4. **Bulk Labeled Analysis** (`ai-bulk-labeled-issue-analysis.yml`)
   - Triggers when a PR is merged to main
   - Processes **only open issues with "Gemini Analyze" label**
   - Smart duplicate detection within labeled issues
   - Ideal for focusing on complex or high-priority issues

### When to Use Label-Based Workflows

- 🎯 **Cost Control**: Reduce API usage by analyzing only selected issues
- 🔍 **Manual Triage**: Team decides which issues need AI analysis
- ⚡ **Complex Issues**: Focus AI resources on difficult problems
- 📊 **Gradual Rollout**: Test AI analysis on select issues first
- 💰 **Budget Constraints**: Limit API calls to fit your budget

### Key Features

- **Beautiful UI**: Professional GitHub-flavored Markdown with emojis and collapsible sections
- **Automated Analysis**: AI analyzes issues using your codebase context  
- **Security Protection**: Built-in prompt injection detection  
- **Configurable**: Customize repository, prompts, and output paths  
- **Duplicate Detection**: Identifies duplicate issues automatically  
- **Smart Labeling**: Auto-assigns labels based on analysis
- **Flexible Filtering**: Choose automatic (all issues) or label-based (selective) workflows  

---

## Prerequisites

### 1. GitHub Repository

- A GitHub repository with Issues enabled
- GitHub Actions enabled in repository settings

### 2. Gemini API Key

> **⚠️ Important Notes**:
> - **Red Hat employees**: Do NOT follow these steps. Please refer to the RH Internal Guidelines for generating your API keys.
> - **Already have a GCP/Gemini API key?** You can skip this section and use your existing key.

You'll need a Google Gemini API key:

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click **"Get API key"** or **"Create API key"**
3. Create a new API key or use an existing one
4. **Copy the API key** (you'll need it later)

> **Note**: The Gemini API has a free tier with generous limits. Check [Google's pricing page](https://ai.google.dev/pricing) for current limits.

### 3. AI-Issue-Triage Repository

This system uses the [AI-Issue-Triage](https://github.com/shvenkat-rh/AI-Issue-Triage) repository, which contains:

- `utils/` - Core library package
  - `analyzer.py` - AI analysis engine
  - `models.py` - Data models
  - `duplicate/` - Duplicate detection modules
  - `security/` - Security checks (prompt injection)
- `cli/` - Command-line tools
  - `analyze.py` - Main analysis CLI
  - `duplicate_check.py` - Duplicate detection CLI
  - `cosine_check.py` - Cosine similarity CLI

The workflows automatically clone this repository during execution - **no manual setup needed**.

---

## Setup Steps

### Step 1: Choose and Copy Workflow Files

You have **four workflow options**. Choose the ones that fit your needs:

#### Option A: Automatic Workflows (All Issues)
Copy these to analyze all issues automatically:

```bash
# From cutlery/workflows/ to .github/workflows/
gemini-issue-analysis.yml      → Analyzes every new issue
ai-bulk-issue-analysis.yml     → Re-analyzes all open issues on PR merge
```

**Best for**: Small to medium repositories, comprehensive issue tracking

#### Option B: Label-Based Workflows (Selective Analysis) 🎯
Copy these to analyze only labeled issues:

```bash
# From cutlery/workflows/ to .github/workflows/
gemini-labeled-issue-analysis.yml     → Analyzes only labeled issues
ai-bulk-labeled-issue-analysis.yml    → Re-analyzes only labeled issues on PR merge
```

**Best for**: Cost control, manual triage, high-volume repositories

#### Option C: Both (Recommended for Flexibility)
Copy all four workflows and use labels to control which issues get analyzed:

```bash
.github/workflows/
├── gemini-issue-analysis.yml              # Auto: Single issue
├── gemini-labeled-issue-analysis.yml      # Label: Single issue  
├── ai-bulk-issue-analysis.yml             # Auto: Bulk issues
└── ai-bulk-labeled-issue-analysis.yml     # Label: Bulk issues
```

**Best for**: Maximum flexibility, gradual rollout, testing

> **💡 Tip**: Start with label-based workflows to test the system, then switch to automatic workflows once you're confident.

### Step 2: Create Configuration File

Create `triage.config.json` in your repository root. You can use the provided example as a template:

**Example**: See `cutlery/triage.config.json` for a complete example template with all optional fields.

Create your own `triage.config.json`:

```json
{
  "repository": {
    "url": "https://github.com/YOUR-ORG/YOUR-REPO",
    "description": "Target repository for AI issue analysis"
  },
  "repomix": {
    "output_path": "repomix-output.txt",
    "description": "Path where repomix output will be stored"
  },
  "analysis": {
    "custom_prompt_path": "",
    "description": "Optional: Path to custom prompt template file for AI analysis (leave empty to use default ansible-creator prompt)"
  },
  "gemini": {
    "model": "gemini-2.0-flash-001",
    "description": "Optional: Gemini model to use (leave empty or remove to use default)"
  }
}
```

**Important**: 
- Replace `YOUR-ORG/YOUR-REPO` with your actual GitHub organization and repository name.
- The `gemini.model` field is optional. You can omit it to use the default model.

### Step 3: Add Gemini API Key to GitHub Secrets

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. **Name**: `GEMINI_API_KEY`
5. **Value**: Paste your Gemini API key
6. Click **"Add secret"**

### Step 4: (Optional) Create "Gemini Analyze" Label

**Only needed if using label-based workflows**

1. Go to your repository on GitHub
2. Navigate to **Issues** → **Labels**
3. Click **"New label"**
4. **Name**: `Gemini Analyze`
5. **Description**: `Trigger AI analysis for this issue`
6. **Color**: Choose any color (suggestion: `#0E8A16` for green)
7. Click **"Create label"**

> **Note**: You can use a different label name by editing the workflow files and changing `'Gemini Analyze'` to your preferred label name.

### Step 5: Commit and Push

```bash
git add .github/workflows/ triage.config.json
git commit -m "Add AI issue triage workflows"
git push origin main
```

### Step 6: Test the Setup

#### Testing Automatic Workflows

If you copied automatic workflows:

1. Go to **Issues** → **New Issue**
2. Title: `Test AI Analysis`
3. Description: `This is a test issue to verify the AI analysis workflow is working correctly.`
4. Click **Create issue**

#### Testing Label-Based Workflows

If you copied label-based workflows:

1. Go to **Issues** → **New Issue**
2. Title: `Test AI Analysis`
3. Description: `This is a test issue to verify the AI analysis workflow is working correctly.`
4. Click **Create issue**
5. **Add the "Gemini Analyze" label** to the issue

**Tip**: You can use content from `cutlery/samples/sample_issue.txt` for a more detailed test case.

#### What to Expect

Within a few minutes, you should see:
- ✅ Workflow running in the **Actions** tab
- ✅ Beautiful AI analysis comment posted on the issue with:
  - Professional formatting with emojis
  - Collapsible sections for detailed information
  - Syntax-highlighted code blocks
- ✅ Labels automatically added (`gemini-analyzed`, `type:*`, `severity:*`)

---

## Configuration

### triage.config.json

This is your main configuration file with three sections:

#### 1. Repository Configuration

```json
"repository": {
  "url": "https://github.com/YOUR-ORG/YOUR-REPO",
  "description": "Target repository for AI issue analysis"
}
```

- **url**: The GitHub repository to analyze
- This is used by `repomix` to fetch and analyze your codebase

#### 2. Repomix Configuration

```json
"repomix": {
  "output_path": "repomix-output.txt",
  "description": "Path where repomix output will be stored"
}
```

- **output_path**: Where to store the codebase analysis file
- Default: `repomix-output.txt` (you usually don't need to change this)

#### 3. Analysis Configuration

```json
"analysis": {
  "custom_prompt_path": "",
  "description": "Optional: Path to custom prompt template file"
}
```

- **custom_prompt_path**: Path to your custom prompt template (optional)
- Leave empty (`""`) to use the default prompt. The default prompt is specific to `ansible-creator`.
- See [Custom Prompts](#custom-prompts) section below

#### 4. Gemini Model Configuration

```json
"gemini": {
  "model": "gemini-2.0-flash-001",
  "description": "Gemini model to use for analysis"
}
```

- **model**: Gemini model name to use (optional)
- Leave empty or remove this section to use the default: `gemini-2.0-flash-001`
- **Available models**:
  - `gemini-2.0-flash-001` (Default) - Latest, fastest, cost-effective
  - `gemini-1.5-pro` - More powerful for complex analysis
  - `gemini-1.5-flash` - Previous generation fast model
  - Other models from [Google AI Studio](https://ai.google.dev/models)
- **Note**: Different models have different pricing and rate limits

---

## Customization

### Custom Prompts

You can customize how the AI analyzes issues by providing your own prompt template.

#### Step 1: Create a Prompt File

Create `prompt.txt` in your repository root.

**Example**: See `cutlery/samples/sample-prompt.txt` for a complete example template.

Create your own `prompt.txt`:

```text
You are an expert software engineer analyzing a code issue for [YOUR PROJECT NAME]. 
Your task is to perform comprehensive issue analysis based on the provided codebase.

ISSUE DETAILS:
Title: {title}
Description: {issue_description}

CODEBASE CONTENT:
{codebase_content}

ANALYSIS REQUIREMENTS:
1. **Issue Classification**: Determine if this is a 'bug', 'enhancement', or 'feature_request'
2. **Severity Assessment**: Rate as 'low', 'medium', 'high', or 'critical'
3. **Root Cause Analysis**: Identify the primary cause and contributing factors
4. **Code Location Identification**: Find relevant files, functions, and classes
5. **Solution Proposal**: Suggest specific code changes with rationale

RESPONSE FORMAT (JSON):
{{
    "issue_type": "bug|enhancement|feature_request",
    "severity": "low|medium|high|critical",
    "root_cause_analysis": {{
        "primary_cause": "Main reason for the issue",
        "contributing_factors": ["factor1", "factor2"],
        "affected_components": ["component1", "component2"],
        "related_code_locations": [
            {{
                "file_path": "path/to/file.py",
                "line_number": 123,
                "function_name": "function_name",
                "class_name": "ClassName"
            }}
        ]
    }},
    "proposed_solutions": [
        {{
            "description": "Solution description",
            "code_changes": "Specific code changes needed",
            "location": {{
                "file_path": "path/to/file.py",
                "line_number": 123,
                "function_name": "function_name",
                "class_name": "ClassName"
            }},
            "rationale": "Why this solution works"
        }}
    ],
    "confidence_score": 0.85,
    "analysis_summary": "Brief summary of the analysis"
}}

ANALYSIS GUIDELINES:
- Focus on [YOUR PROJECT'S] specific patterns and architecture
- Consider [YOUR LANGUAGE]-specific patterns and best practices
- Look for patterns in existing code for consistency
- Provide actionable, specific solutions

Please analyze the issue and provide your response in the exact JSON format specified above.
```

#### Step 2: Available Placeholders

Your prompt **must** include these placeholders (they will be replaced automatically):

- `{title}` - The issue title
- `{issue_description}` - The issue description/body
- `{codebase_content}` - Your complete codebase from repomix

#### Step 3: Update Configuration

Update `triage.config.json`:

```json
"analysis": {
  "custom_prompt_path": "prompt.txt"
}
```

#### Step 4: Commit and Push

```bash
git add prompt.txt triage.config.json
git commit -m "Add custom analysis prompt"
git push origin main
```

### Using a Different Gemini Model

You can specify which Gemini model to use for analysis:

**In `triage.config.json`**:

```json
{
  "gemini": {
    "model": "gemini-1.5-pro"
  }
}
```

**Available models**:
- `gemini-2.0-flash-001` - Default, latest, fastest
- `gemini-1.5-pro` - More powerful, better for complex issues
- `gemini-1.5-flash` - Previous generation
- Check [Google AI Studio](https://ai.google.dev/models) for more options

**When to use different models**:
- **gemini-2.0-flash-001**: General use, cost-effective
- **gemini-1.5-pro**: Complex codebases, detailed analysis needed
- **gemini-1.5-flash**: If 2.0 has issues or for backward compatibility

### Analyzing a Different Repository

You can analyze issues from one repository using the codebase from another:

**Example**: Analyze issues in `my-org/issues-repo` using code from `my-org/main-codebase`

In `my-org/issues-repo`, set `triage.config.json`:

```json
{
  "repository": {
    "url": "https://github.com/my-org/main-codebase"
  }
}
```

This is useful for:
- Separating issue tracking from code
- Analyzing legacy code with modern tooling
- Cross-repository analysis

---

## Usage

### Workflow Comparison

| Feature | Automatic | Label-Based |
|---------|-----------|-------------|
| **Trigger** | All new issues | Only labeled issues |
| **Cost** | Higher (more API calls) | Lower (fewer API calls) |
| **Manual Work** | None | Add label to issues |
| **Best For** | Complete automation | Manual triage, cost control |
| **Issue Volume** | Low to medium | Any (especially high) |

### Single Issue Analysis

#### Automatic (`gemini-issue-analysis.yml`)
**Triggered**: When any new issue is created

#### Label-Based (`gemini-labeled-issue-analysis.yml`)  
**Triggered**: When an issue is labeled with "Gemini Analyze" OR opened with that label

**What Both Do**:
1. Fetches your codebase using repomix
2. Checks for prompt injection (security)
3. Checks for duplicate issues
4. Analyzes the issue with AI
5. Posts beautiful formatted analysis comment with:
   - Emojis for visual indicators (🐛 🔴 📊)
   - Collapsible sections for detailed info
   - Syntax-highlighted code blocks
   - Professional Markdown formatting
6. Adds relevant labels

**Labels Added**:
- `gemini-analyzed` - Issue has been analyzed
- `type:bug` / `type:enhancement` / `type:feature_request`
- `severity:low` / `severity:medium` / `severity:high` / `severity:critical`
- `duplicate` - If duplicate found
- `security-alert` - If prompt injection detected
- `prompt-injection-blocked` / `prompt-injection-warning`

### Bulk Issue Analysis

#### Automatic (`ai-bulk-issue-analysis.yml`)
**Triggered**: When a PR is merged to main  
**Processes**: All open issues

#### Label-Based (`ai-bulk-labeled-issue-analysis.yml`)
**Triggered**: When a PR is merged to main  
**Processes**: Only open issues with "Gemini Analyze" label

**What Both Do**:
1. Fetches relevant open issues (sorted oldest → newest)
2. For each issue (in order):
   - **Step 1: Prompt Injection Check**
     - Scans for malicious patterns
     - Posts security report comment
     - Adds `security-alert`, `prompt-injection-blocked` or `prompt-injection-warning` labels
     - Skips analysis for high/critical risk issues
   - **Step 2: Duplicate Detection** (if security check passes)
     - Compares against previously analyzed issues in this run
     - If duplicate: adds `duplicate` label, posts duplicate comment with confidence score, skips AI analysis
   - **Step 3: AI Analysis** (if not duplicate)
     - Runs full analysis against updated codebase
     - Posts beautifully formatted analysis with fresh insights
     - Adds labels: `gemini-analyzed`, `type:*`, `severity:*`

**Smart Duplicate Detection**:
- Issues are processed **oldest first**
- Each issue is compared against all previously analyzed issues in this run
- Older issues become "canonical" - newer duplicates reference them
- Duplicates are marked and skipped to save API calls
- Example: If Issue #50 and Issue #100 are duplicates, #100 will reference #50

**Comments Posted**:
Every issue receives at least one comment with beautiful formatting:
- **Prompt Injection Report** - Posted for all issues (safe or risky)
- **Duplicate Detection Comment** - Posted if duplicate found (with confidence score and reasoning)
- **AI Analysis** - Posted only for non-duplicate, safe issues with:
  - 🤖 Professional header with emojis
  - 📝 Executive summary
  - 🔍 Root cause analysis with collapsible details
  - 💡 Proposed solutions with code blocks
  - Full analysis with fresh codebase context

**Use Cases**:
- After major code refactoring
- When issue context changes
- Periodic re-analysis of open issues
- Cleaning up duplicate issues automatically

---

## Advanced Configuration

### AI-Issue-Triage Repository Settings

The workflows clone from:
- **Repository**: `shvenkat-rh/AI-Issue-Triage`
- **Branch**: `main`

To use a fork or different branch, modify the workflow:

```yaml
- name: Clone AI-Issue-Triage repository
  uses: actions/checkout@v4
  with:
    repository: YOUR-ORG/AI-Issue-Triage  # Change this
    ref: your-branch-name                 # Change this
    path: ai-triage
```

---

## Troubleshooting

### Issue: Workflow Stuck in "Queued" State

**Cause**: GitHub Actions runner availability or resource limits

**Solutions**:
1. Wait - workflows may queue during peak times
2. Check **Settings** → **Actions** → **General** for approval requirements
3. Verify you haven't hit GitHub Actions limits
4. For private repos, check your plan's concurrent job limits

### Issue: "GEMINI_API_KEY environment variable not set"

**Cause**: API key not configured properly

**Solutions**:
1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Verify `GEMINI_API_KEY` exists
3. Check the secret name is exactly `GEMINI_API_KEY` (case-sensitive)
4. If recently added, try re-running the workflow

### Issue: "Source file not found"

**Cause**: Configuration file path incorrect

**Solutions**:
1. Verify `triage.config.json` exists in repository root
2. Check the file is committed and pushed
3. Verify repository URL in config is correct
4. Check repomix can access the repository (must be public or accessible)

### Issue: Analysis Quality is Poor

**Cause**: Default prompt not optimized for your project

**Solutions**:
1. Create a custom prompt (see [Custom Prompts](#custom-prompts))
2. Include project-specific context and patterns
3. Specify your programming language and frameworks
4. Add examples of good analysis for your project

### Issue: Too Many False Positive Prompt Injections

**Cause**: Legitimate content triggering security checks

**Solutions**:
1. Review the detected patterns in workflow logs
2. Contact repository maintainers to adjust sensitivity
3. The security system errs on the side of caution
4. Low/Medium risks still get analyzed

### Viewing Workflow Logs

1. Go to **Actions** tab in your repository
2. Click on the workflow run
3. Expand each step to see detailed logs
4. Download artifacts for analysis results

### Workflow Artifacts

Both workflows upload artifacts containing:
- `analysis_result.json` - Structured analysis data
- `analysis_result.txt` - Human-readable analysis
- `prompt_injection_result.json` - Security check results
- `duplicate_result.json` - Duplicate detection results
- `triage.config.json` - Configuration used
- `repomix-output.txt` - Codebase analysis

Access artifacts:
1. Go to completed workflow run
2. Scroll to **Artifacts** section
3. Download zip files

---

## Cost Considerations

### GitHub Actions

- **Free Tier**: 2,000 minutes/month for public repositories
- **Private Repos**: Minutes depend on your plan
- These workflows typically use 5-15 minutes per run

### Gemini API

- **Free Tier**: Generous limits for development and testing
- **Costs**: Check [Google AI Pricing](https://ai.google.dev/pricing)
- **Typical Usage**: 
  - Single issue analysis: ~1-2 requests
  - Bulk analysis: 1-2 requests per open issue

### Repomix

- Free and open-source
- Runs during workflow execution
- No additional costs

---

## Security Notes

### Data Privacy

- Issue content is sent to Google's Gemini API
- Your codebase is packaged by repomix and included in prompts
- No data is stored permanently by the workflows
- All processing happens in isolated GitHub Actions runners

### Prompt Injection Protection

The system includes built-in protection against prompt injection attacks:

- **Risk Levels**: safe, low, medium, high, critical
- **High/Critical**: Issue analysis is blocked
- **Low/Medium**: Analysis proceeds with warnings
- **Safe**: Normal processing

### Recommendations

1. Review security alerts on issues
2. Keep the AI-Issue-Triage dependency updated
3. Monitor workflow logs for unusual activity
4. Rotate your Gemini API key periodically
5. Use GitHub's secret scanning features

---

## Getting Help

### Resources

- **AI-Issue-Triage Repo**: [shvenkat-rh/AI-Issue-Triage](https://github.com/shvenkat-rh/AI-Issue-Triage)
- **Repomix**: [yamadashy/repomix](https://github.com/yamadashy/repomix)
- **Google Gemini Docs**: [ai.google.dev](https://ai.google.dev/)
- **GitHub Actions Docs**: [docs.github.com/actions](https://docs.github.com/actions)

### Common Issues

If you encounter problems:

1. Check workflow logs in the Actions tab
2. Verify all configuration files are correct
3. Ensure secrets are properly configured
4. Review the troubleshooting section above
5. Check that the AI-Issue-Triage repository is accessible

---

## Example Configuration

Here's a complete example for a Python project:

**triage.config.json**:
```json
{
  "repository": {
    "url": "https://github.com/myorg/my-python-app"
  },
  "repomix": {
    "output_path": "repomix-output.txt"
  },
  "analysis": {
    "custom_prompt_path": "prompts/python-analysis.txt"
  }
}
```

**prompts/python-analysis.txt**:
```text
You are a Python expert analyzing issues for a Flask web application.

ISSUE DETAILS:
Title: {title}
Description: {issue_description}

CODEBASE CONTENT:
{codebase_content}

Focus on:
- Python best practices and PEP standards
- Flask-specific patterns and security
- Database migrations and ORM usage
- API endpoint design and REST principles
- Testing with pytest

[Rest of prompt...]
```

---

## You're All Set!

Your repository now has automated AI-powered issue analysis! 

**Next Steps**:
1. Create a test issue to verify everything works (use `cutlery/samples/sample_issue.txt` for inspiration)
2. Customize the prompt for your project (see `cutlery/samples/sample-prompt.txt`)
3. Monitor the first few analyses to ensure quality
4. Adjust configuration as needed (refer to `cutlery/triage.config.json` example)

---

## Quick Reference: Files in Cutlery Directory

All files referenced in this guide can be found in the `cutlery/` directory:

### Workflows (Copy to Your Repo)

**Automatic Workflows (All Issues)**:
- `cutlery/workflows/gemini-issue-analysis.yml` → Copy to `.github/workflows/`
- `cutlery/workflows/ai-bulk-issue-analysis.yml` → Copy to `.github/workflows/`

**Label-Based Workflows (Selective Analysis)** 🎯:
- `cutlery/workflows/gemini-labeled-issue-analysis.yml` → Copy to `.github/workflows/`
- `cutlery/workflows/ai-bulk-labeled-issue-analysis.yml` → Copy to `.github/workflows/`

### Configuration Examples
- `cutlery/triage.config.json` - Example configuration file

### Sample Files (For Testing & Reference)
- `cutlery/samples/sample_issue.txt` - Example issue content for testing
- `cutlery/samples/sample_issues.json` - Multiple test issues in JSON format
- `cutlery/samples/sample-prompt.txt` - Complete custom prompt template example
- `cutlery/samples/env_example.txt` - Environment variables template

### This Guide
- `cutlery/QUICKSTART.md` - Complete setup and usage guide (this file)

**Questions?** Check the troubleshooting section or review the workflow logs for detailed information.

Happy issue triaging!

