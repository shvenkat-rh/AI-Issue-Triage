#!/usr/bin/env python3
"""Command-line interface for Gemini Batch Issue Analyzer.

COMMAND LINE OPTIONS:

INPUT OPTIONS:
  --issues-file, -f PATH       JSON file containing list of issues to analyze (required)
                               Format: [{"title": "...", "description": "..."}, ...]

CONFIGURATION OPTIONS:
  --source-path, -s PATH       Path to source of truth file containing codebase
                               information (default: repomix-output.txt)
  --custom-prompt PATH         Path to custom prompt template file that overrides
                               the default analysis prompt
  --api-key TEXT               Gemini API key for authentication
                               (default: from GEMINI_API_KEY env var)
  --retries INTEGER            Maximum number of retry attempts for low quality
                               responses (default: 2)
  --poll-interval INTEGER      Seconds between polling for batch results (default: 10)

OUTPUT OPTIONS:
  --output, -o PATH            Save analysis results to file instead of stdout
  --format [text|json]         Output format: 'text' for human-readable format,
                               'json' for structured data (default: json)

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

INPUT FILE FORMAT:
  The issues file should be a JSON array of objects with 'title' and 'description' keys:
  [
    {
      "title": "Login page crashes",
      "description": "When I click submit, the app crashes"
    },
    {
      "title": "Database timeout",
      "description": "Connection times out after 30 seconds"
    }
  ]

OUTPUT FORMATS:
  - text: Human-readable analysis reports for each issue
  - json: Structured JSON array of analysis results suitable for programmatic processing

ENVIRONMENT VARIABLES:
  GEMINI_API_KEY              API key for Gemini service (alternative to --api-key)
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Import cleaning functions from analyze.py
from cli.analyze import clean_issue_data, clean_text, format_analysis_text, mask_emails, mask_ip_addresses, mask_secrets
from utils.batch_analyzer import GeminiBatchIssueAnalyzer
from utils.models import IssueType, Severity


def load_issues_from_file(file_path: Path) -> List[dict]:
    """Load issues from a JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("ERROR: Issues file must contain a JSON array", file=sys.stderr)
            sys.exit(1)

        issues = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                print(f"ERROR: Issue {i+1} must be a JSON object", file=sys.stderr)
                sys.exit(1)

            if "title" not in item:
                print(f"ERROR: Issue {i+1} missing required field 'title'", file=sys.stderr)
                sys.exit(1)

            if "description" not in item:
                print(f"ERROR: Issue {i+1} missing required field 'description'", file=sys.stderr)
                sys.exit(1)

            issues.append({"title": str(item["title"]), "description": str(item["description"])})

        return issues

    except FileNotFoundError:
        print(f"ERROR: File '{file_path}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in file '{file_path}': {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Error loading issues file: {e}", file=sys.stderr)
        sys.exit(1)


def create_sample_issues_file(file_path: Path):
    """Create a sample issues file for demonstration."""
    sample_issues = [
        {
            "title": "Login page crashes when clicking submit button",
            "description": "When I click the submit button on the login page, the application crashes with a JavaScript error. The console shows 'TypeError: Cannot read property of undefined'. This happens in Chrome and Firefox.",
        },
        {
            "title": "Database connection timeout in production",
            "description": "The application frequently shows database connection timeout errors in production environment. This affects user authentication and data retrieval. Error occurs approximately every 30 minutes.",
        },
        {
            "title": "User authentication module memory leak",
            "description": "Memory usage continuously increases in the authentication service. After 24 hours of operation, memory usage reaches 2GB and the service becomes unresponsive.",
        },
    ]

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sample_issues, f, indent=2)

    print(f"Sample issues file created: {file_path}")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Gemini Batch Issue Analyzer - AI-powered batch issue analysis for codebases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a sample issues file
  ai-triage-batch --create-sample issues.json

  # Batch analyze issues from file
  ai-triage-batch --issues-file issues.json
  # or: python -m cli.batch_analyze --issues-file issues.json

  # With custom source of truth
  ai-triage-batch --issues-file issues.json --source-path /path/to/codebase.txt

  # With custom prompt template
  ai-triage-batch --issues-file issues.json --custom-prompt /path/to/prompt.txt
  
  # Configure retry attempts and polling
  ai-triage-batch --issues-file issues.json --retries 3 --poll-interval 15

  # Output to file
  ai-triage-batch --issues-file issues.json --output results.json

  # Text output format
  ai-triage-batch --issues-file issues.json --format text

  # Disable data cleaning
  ai-triage-batch --issues-file issues.json --no-clean
        """,
    )

    # Input options
    parser.add_argument("--issues-file", "-f", type=Path, help="JSON file containing list of issues to analyze")

    parser.add_argument("--create-sample", type=Path, help="Create a sample issues JSON file at the specified path")

    # Output options
    parser.add_argument("--output", "-o", type=Path, help="Output file (default: stdout)")

    parser.add_argument("--format", choices=["text", "json"], default="json", help="Output format (default: json)")

    # Other options
    parser.add_argument("--source-path", "-s", type=Path, help="Path to source of truth file (default: repomix-output.txt)")

    parser.add_argument("--custom-prompt", type=Path, help="Path to custom prompt template file (overrides default prompt)")

    parser.add_argument("--api-key", help="Gemini API key (default: from GEMINI_API_KEY env var)")

    parser.add_argument(
        "--retries", type=int, default=2, help="Maximum number of retry attempts for low quality responses (default: 2)"
    )

    parser.add_argument(
        "--poll-interval", type=int, default=10, help="Seconds between polling for batch results (default: 10)"
    )

    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress messages")

    parser.add_argument(
        "--no-clean", action="store_true", help="Disable data cleaning (preserve raw input including secrets, emails, IPs)"
    )

    parser.add_argument("--version", action="version", version="Gemini Batch Issue Analyzer 1.0.0")

    args = parser.parse_args()

    # Create sample file if requested
    if args.create_sample:
        create_sample_issues_file(args.create_sample)
        return

    # Validate required arguments
    if not args.issues_file:
        parser.error("--issues-file is required for batch analysis")

    # Load issues from file
    issues = load_issues_from_file(args.issues_file)

    if not args.quiet:
        print(f"Loaded {len(issues)} issues from {args.issues_file}")

    # Clean the data if requested
    if not args.no_clean:
        if not args.quiet:
            print("Cleaning and sanitizing issue data...")
        for issue in issues:
            issue["title"], issue["description"] = clean_issue_data(issue["title"], issue["description"])

    # Initialize analyzer
    try:
        if not args.quiet:
            print("Initializing Gemini batch analyzer...")

        analyzer = GeminiBatchIssueAnalyzer(
            api_key=args.api_key,
            source_path=str(args.source_path) if args.source_path else None,
            custom_prompt_path=str(args.custom_prompt) if args.custom_prompt else None,
        )

        if not args.quiet:
            print(f"Analyzing {len(issues)} issues in batch mode...")

        analyses = analyzer.batch_analyze_issues(issues, max_retries=args.retries, poll_interval=args.poll_interval)

        if not args.quiet:
            print("Analysis complete!")
            print()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Format output
    if args.format == "json":
        output_text = json.dumps([analysis.model_dump() for analysis in analyses], indent=2, default=str)
    else:
        # Text format: show each analysis separated by dividers
        text_outputs = []
        for i, analysis in enumerate(analyses, 1):
            text_outputs.append(f"{'='*80}")
            text_outputs.append(f"ANALYSIS {i} of {len(analyses)}")
            text_outputs.append(f"{'='*80}")
            text_outputs.append(format_analysis_text(analysis))
            text_outputs.append("")
        output_text = "\n".join(text_outputs)

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
