#!/usr/bin/env python3
"""Command-line interface for Gemini Issue Analyzer.

COMMAND LINE OPTIONS:

INPUT OPTIONS:
  --title, -t TEXT              Issue title (required with --description)
  --description, -d TEXT        Issue description (required with --title)
  --file, -f PATH              Read issue from file (title on first line,
                               description on remaining lines)

CONFIGURATION OPTIONS:
  --source-path, -s PATH       Path to source of truth file containing codebase
                               information (default: repomix-output.txt)
  --custom-prompt PATH         Path to custom prompt template file that overrides
                               the default analysis prompt
  --api-key TEXT               Gemini API key for authentication
                               (default: from GEMINI_API_KEY env var)
  --retries INTEGER            Maximum number of retry attempts for low quality
                               responses (default: 2)

OUTPUT OPTIONS:
  --output, -o PATH            Save analysis results to file instead of stdout
  --format [text|json]         Output format: 'text' for human-readable format,
                               'json' for structured data (default: text)

BEHAVIOR OPTIONS:
  --quiet, -q                  Suppress progress messages, only show results
  --no-clean                   Disable data cleaning (preserve raw input including
                               secrets, emails, IPs)
  --version                    Show version information and exit

DATA CLEANING:
  By default, the tool automatically cleans input data to:
  - Strip extra whitespace and normalize formatting
  - Mask sensitive information like API keys, tokens, passwords
  - Mask email addresses (e.g., user@domain.com → u***r@domain.com)
  - Mask IP addresses (both IPv4 and IPv6)
  Use --no-clean to disable this behavior and preserve raw input.

USAGE MODES:
  1. Interactive Mode: Run without arguments to enter interactive input mode
  2. Direct Mode: Use --title and --description to provide issue details
  3. File Mode: Use --file to read issue details from a text file

INPUT REQUIREMENTS:
  - Interactive mode: No arguments needed, will prompt for input
  - Direct mode: Both --title and --description are required
  - File mode: Only --file is needed, cannot be combined with --title/--description

OUTPUT FORMATS:
  - text: Human-readable analysis report with sections for classification,
          summary, root cause analysis, and proposed solutions
  - json: Structured JSON data suitable for programmatic processing

ENVIRONMENT VARIABLES:
  GEMINI_API_KEY              API key for Gemini service (alternative to --api-key)
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from utils.analyzer import GeminiIssueAnalyzer
from utils.models import IssueType, Severity


def clean_text(text: str) -> str:
    """Clean and normalize text by removing extra whitespace and normalizing format.

    Args:
        text: The text to clean

    Returns:
        Cleaned text with normalized whitespace
    """
    if not text:
        return text

    # Remove leading/trailing whitespace
    text = text.strip()

    # Replace multiple spaces with single space
    text = re.sub(r"\s+", " ", text)

    # Replace multiple newlines with double newline (preserve paragraph breaks)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

    # Clean up mixed whitespace (tabs, spaces, etc.)
    text = re.sub(r"[ \t]+", " ", text)

    return text


def mask_secrets(text: str) -> str:
    """Mask common secrets like API keys, tokens, passwords, etc.

    Args:
        text: The text to process

    Returns:
        Text with secrets masked
    """
    if not text:
        return text

    # Common secret patterns (ordered from most specific to least specific)
    patterns = [
        # JWT tokens (most specific - must come before general token patterns)
        (r"\beyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b", r"[MASKED_JWT_TOKEN]"),
        # OpenAI API keys (specific format)
        (r"\bsk-[a-zA-Z0-9]{48}\b", r"[MASKED_OPENAI_KEY]"),
        # GitHub tokens (specific format)
        (r"\bgh[ps]_[a-zA-Z0-9_]{36,}\b", r"[MASKED_GITHUB_TOKEN]"),
        # AWS keys (specific format)
        (r"\bAKIA[0-9A-Z]{16}\b", r"[MASKED_AWS_ACCESS_KEY]"),
        (r'(aws_secret_access_key[_-]?[=:\s]*["\']?)([a-zA-Z0-9/+=]{40})["\']?', r"\1[MASKED_AWS_SECRET]"),
        # Database connection strings
        (r"(mongodb://[^:]+:)([^@]+)(@)", r"\1[MASKED_DB_PASSWORD]\3"),
        (r"(mysql://[^:]+:)([^@]+)(@)", r"\1[MASKED_DB_PASSWORD]\3"),
        (r"(postgres://[^:]+:)([^@]+)(@)", r"\1[MASKED_DB_PASSWORD]\3"),
        # API Keys (various formats)
        (r'(api[_-]?key[_-]?[=:\s]*["\']?)([a-zA-Z0-9_-]{20,})["\']?', r"\1[MASKED_API_KEY]"),
        (r'(key[_-]?[=:\s]*["\']?)([a-zA-Z0-9_-]{32,})["\']?', r"\1[MASKED_KEY]"),
        # Tokens (broader patterns - after specific ones)
        (r'(access[_-]?token[_-]?[=:\s]*["\']?)([a-zA-Z0-9_.\-/+=]{20,})["\']?', r"\1[MASKED_ACCESS_TOKEN]"),
        (r'(bearer[_-]?[=:\s]*["\']?)([a-zA-Z0-9_.\-/+=]{20,})["\']?', r"\1[MASKED_BEARER_TOKEN]"),
        (r'(token[_-]?[=:\s]*["\']?)([a-zA-Z0-9_.\-/+=]{20,})["\']?', r"\1[MASKED_TOKEN]"),
        # Passwords
        (r'(password[_-]?[=:\s]*["\']?)([^\s"\']{8,})["\']?', r"\1[MASKED_PASSWORD]"),
        (r'(pass[_-]?[=:\s]*["\']?)([^\s"\']{8,})["\']?', r"\1[MASKED_PASSWORD]"),
        (r'(pwd[_-]?[=:\s]*["\']?)([^\s"\']{8,})["\']?', r"\1[MASKED_PASSWORD]"),
        # Generic secrets (long alphanumeric strings that look like secrets)
        (r'(secret[_-]?[=:\s]*["\']?)([a-zA-Z0-9_-]{24,})["\']?', r"\1[MASKED_SECRET]"),
    ]

    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text


def mask_emails(text: str) -> str:
    """Mask email addresses in text.

    Args:
        text: The text to process

    Returns:
        Text with email addresses masked
    """
    if not text:
        return text

    # Email pattern - matches most common email formats
    email_pattern = r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"

    def mask_email(match):
        email = match.group(0)
        parts = email.split("@")
        if len(parts) == 2:
            username, domain = parts
            # Keep first and last character of username if long enough
            if len(username) > 2:
                masked_username = username[0] + "*" * (len(username) - 2) + username[-1]
            else:
                masked_username = "*" * len(username)

            # Keep domain as is or mask it too based on preference
            # For now, keeping domain visible for context
            return f"{masked_username}@{domain}"
        return "[MASKED_EMAIL]"

    return re.sub(email_pattern, mask_email, text)


def mask_ip_addresses(text: str) -> str:
    """Mask IP addresses in text.

    Args:
        text: The text to process

    Returns:
        Text with IP addresses masked
    """
    if not text:
        return text

    # IPv4 pattern
    ipv4_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"

    # IPv6 pattern (simplified)
    ipv6_pattern = r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"

    # Replace IPv4 addresses
    text = re.sub(ipv4_pattern, "[MASKED_IPv4]", text)

    # Replace IPv6 addresses
    text = re.sub(ipv6_pattern, "[MASKED_IPv6]", text)

    return text


def clean_issue_data(title: str, description: str) -> tuple[str, str]:
    """Clean and sanitize issue title and description.

    Args:
        title: The issue title
        description: The issue description

    Returns:
        Tuple of (cleaned_title, cleaned_description)
    """
    # Clean and normalize text
    cleaned_title = clean_text(title) if title else ""
    cleaned_description = clean_text(description) if description else ""

    # Mask sensitive information
    cleaned_title = mask_secrets(cleaned_title)
    cleaned_title = mask_emails(cleaned_title)
    cleaned_title = mask_ip_addresses(cleaned_title)

    cleaned_description = mask_secrets(cleaned_description)
    cleaned_description = mask_emails(cleaned_description)
    cleaned_description = mask_ip_addresses(cleaned_description)

    return cleaned_title, cleaned_description


def format_analysis_text(analysis) -> str:
    """Format analysis results for text output with beautiful GitHub-flavored Markdown."""

    output = []

    # Get severity emoji and color
    severity_map = {"critical": ("🔴", "Critical"), "high": ("🟠", "High"), "medium": ("🟡", "Medium"), "low": ("🟢", "Low")}
    severity_emoji, severity_label = severity_map.get(analysis.severity.value.lower(), ("⚪", analysis.severity.value.title()))

    # Get issue type emoji
    type_map = {"bug": "🐛", "enhancement": "✨", "feature_request": "🚀"}
    type_emoji = type_map.get(analysis.issue_type.value.lower(), "📋")

    # Header with title and badges
    output.append("# 🤖 AI Analysis Report")
    output.append("")
    output.append(f"**Issue:** {analysis.title}")
    output.append("")

    # Status badges
    confidence_percent = int(analysis.confidence_score * 100)
    confidence_color = "green" if confidence_percent >= 80 else "yellow" if confidence_percent >= 60 else "orange"

    output.append(f"{type_emoji} **Type:** `{analysis.issue_type.value.upper()}`  ")
    output.append(f"{severity_emoji} **Severity:** `{severity_label.upper()}`  ")
    output.append(f"📊 **Confidence:** `{confidence_percent}%`  ")
    output.append(f"⏰ **Generated:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}`")
    output.append("")
    output.append("---")
    output.append("")

    # Summary Section
    output.append("## 📝 Executive Summary")
    output.append("")
    output.append(analysis.analysis_summary)
    output.append("")
    output.append("---")
    output.append("")

    # Root Cause Analysis Section
    output.append("## 🔍 Root Cause Analysis")
    output.append("")
    output.append("### Primary Cause")
    output.append("")
    output.append(f"> {analysis.root_cause_analysis.primary_cause}")
    output.append("")

    if analysis.root_cause_analysis.contributing_factors:
        output.append("<details>")
        output.append("<summary><b>Contributing Factors</b></summary>")
        output.append("")
        for factor in analysis.root_cause_analysis.contributing_factors:
            output.append(f"- {factor}")
        output.append("")
        output.append("</details>")
        output.append("")

    if analysis.root_cause_analysis.affected_components:
        output.append("<details>")
        output.append("<summary><b>Affected Components</b></summary>")
        output.append("")
        for component in analysis.root_cause_analysis.affected_components:
            output.append(f"- `{component}`")
        output.append("")
        output.append("</details>")
        output.append("")

    if analysis.root_cause_analysis.related_code_locations:
        output.append("<details>")
        output.append("<summary><b>Related Code Locations</b></summary>")
        output.append("")
        output.append("| File | Line | Class | Function |")
        output.append("|------|------|-------|----------|")
        for location in analysis.root_cause_analysis.related_code_locations:
            file_path = f"`{location.file_path}`"
            line_num = str(location.line_number) if location.line_number else "-"
            class_name = f"`{location.class_name}`" if location.class_name else "-"
            func_name = f"`{location.function_name}`" if location.function_name else "-"
            output.append(f"| {file_path} | {line_num} | {class_name} | {func_name} |")
        output.append("")
        output.append("</details>")
        output.append("")

    output.append("---")
    output.append("")

    # Proposed Solutions Section
    output.append("## 💡 Proposed Solutions")
    output.append("")

    for i, solution in enumerate(analysis.proposed_solutions, 1):
        solution_num = f"Solution {i}" if len(analysis.proposed_solutions) > 1 else "Solution"
        output.append(f"### {solution_num}")
        output.append("")
        output.append(f"**{solution.description}**")
        output.append("")

        # Location information
        output.append("<details>")
        output.append("<summary><b>📍 Implementation Details</b></summary>")
        output.append("")
        output.append("**Location:**")
        output.append(f"- **File:** `{solution.location.file_path}`")
        if solution.location.line_number:
            output.append(f"- **Line:** `{solution.location.line_number}`")
        if solution.location.class_name:
            output.append(f"- **Class:** `{solution.location.class_name}`")
        if solution.location.function_name:
            output.append(f"- **Function:** `{solution.location.function_name}`")
        output.append("")

        # Rationale
        output.append("**Rationale:**")
        output.append("")
        output.append(solution.rationale)
        output.append("")

        # Code changes
        output.append("**Code Changes:**")
        output.append("")
        output.append("```python")
        output.append(solution.code_changes)
        output.append("```")
        output.append("")
        output.append("</details>")
        output.append("")

    output.append("---")
    output.append("")

    # Footer
    output.append("<sub>")
    output.append("🤖 *This analysis was generated by Gemini AI. Please review carefully and validate before implementing.*")
    output.append("</sub>")

    return "\n".join(output)


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Gemini Issue Analyzer - AI-powered issue analysis for codebases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  ai-triage
  # or: python -m cli.analyze

  # Direct analysis
  ai-triage --title "Login bug" --description "Users can't login"

  # From file
  ai-triage --file issue.txt

  # With custom source of truth
  ai-triage --title "Bug" --description "Description" --source-path /path/to/codebase.txt

  # With custom prompt template
  ai-triage --title "Bug" --description "Description" --custom-prompt /path/to/prompt.txt
  
  # Configure retry attempts
  ai-triage --title "Bug" --description "Description" --retries 3

  # Output to file
  ai-triage --title "Bug" --description "Description" --output analysis.txt

  # JSON output
  ai-triage --title "Bug" --description "Description" --format json

  # Disable data cleaning (preserve raw input)
  ai-triage --title "API key issue" --description "My key abc123..." --no-clean
        """,
    )

    # Input options
    parser.add_argument("--title", "-t", help="Issue title")

    parser.add_argument("--description", "-d", help="Issue description")

    parser.add_argument(
        "--file", "-f", type=Path, help="Read issue from file (format: title on first line, description on remaining lines)"
    )

    # Output options
    parser.add_argument("--output", "-o", type=Path, help="Output file (default: stdout)")

    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format (default: text)")

    # Other options
    parser.add_argument("--source-path", "-s", type=Path, help="Path to source of truth file (default: repomix-output.txt)")

    parser.add_argument("--custom-prompt", type=Path, help="Path to custom prompt template file (overrides default prompt)")

    parser.add_argument("--api-key", help="Gemini API key (default: from GEMINI_API_KEY env var)")

    parser.add_argument("--model", help="Gemini model name (default: gemini-2.0-flash-001)")

    parser.add_argument(
        "--retries", type=int, default=2, help="Maximum number of retry attempts for low quality responses (default: 2)"
    )

    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress messages")

    parser.add_argument(
        "--no-clean", action="store_true", help="Disable data cleaning (preserve raw input including secrets, emails, IPs)"
    )

    parser.add_argument("--version", action="version", version="Gemini Issue Analyzer 1.0.0")

    args = parser.parse_args()

    # Get issue details
    title = None
    description = None

    if args.file:
        if not args.file.exists():
            print(f"Error: File '{args.file}' not found", file=sys.stderr)
            sys.exit(1)

        try:
            content = args.file.read_text().strip()
            lines = content.split("\n", 1)
            title = lines[0].strip()
            description = lines[1].strip() if len(lines) > 1 else ""

            # Clean the data from file
            if not args.no_clean:
                title, description = clean_issue_data(title, description)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.title and args.description:
        title = args.title
        description = args.description

        # Clean the data from command line arguments
        if not args.no_clean:
            title, description = clean_issue_data(title, description)

    elif args.title or args.description:
        print("Error: Both --title and --description are required when not using --file", file=sys.stderr)
        sys.exit(1)

    else:
        # Interactive mode
        if not args.quiet:
            print("Gemini Issue Analyzer - Interactive Mode")
            print("=" * 50)

        try:
            title = input("Issue Title: ").strip()
            if not title:
                print("Error: Title cannot be empty", file=sys.stderr)
                sys.exit(1)

            print("Issue Description (press Ctrl+D when done):")
            description_lines = []
            try:
                while True:
                    line = input()
                    description_lines.append(line)
            except EOFError:
                pass

            description = "\n".join(description_lines).strip()
            if not description:
                print("Error: Description cannot be empty", file=sys.stderr)
                sys.exit(1)

            # Clean the data from interactive input
            if not args.no_clean:
                title, description = clean_issue_data(title, description)

        except KeyboardInterrupt:
            print("\nAborted by user", file=sys.stderr)
            sys.exit(1)

    # Validate inputs
    if not title or not description:
        print("Error: Both title and description are required", file=sys.stderr)
        sys.exit(1)

    # Initialize analyzer
    try:
        if not args.quiet:
            print("Initializing Gemini analyzer...")

        analyzer = GeminiIssueAnalyzer(
            api_key=args.api_key,
            source_path=str(args.source_path) if args.source_path else None,
            custom_prompt_path=str(args.custom_prompt) if args.custom_prompt else None,
            model_name=args.model,
        )

        if not args.quiet:
            print("Analyzing issue...")

        analysis = analyzer.analyze_issue(title, description, max_retries=args.retries)

        if not args.quiet:
            print("Analysis complete!")
            print()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Format output
    if args.format == "json":
        output_text = json.dumps(analysis.model_dump(), indent=2, default=str)
    else:
        output_text = format_analysis_text(analysis)

    # Write output
    if args.output:
        try:
            args.output.write_text(output_text)
            if not args.quiet:
                print(f"Analysis saved to {args.output}")
        except Exception as e:
            print(f"Error writing to file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output_text)


if __name__ == "__main__":
    main()
