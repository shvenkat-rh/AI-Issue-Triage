#!/usr/bin/env python3
"""CLI for PR review functionality."""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from utils.pr_analyzer import PRAnalyzer

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_pr_data(pr_file: str) -> dict:
    """Load PR data from a JSON file.
    
    Args:
        pr_file: Path to PR JSON file
        
    Returns:
        Dictionary containing PR data
    """
    try:
        with open(pr_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"PR file not found: {pr_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in PR file: {e}")
        sys.exit(1)


def save_review(review_data: dict, output_file: Optional[str] = None) -> None:
    """Save review data to a file or print to stdout.
    
    Args:
        review_data: Review data to save
        output_file: Optional output file path
    """
    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(review_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Review saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving review: {e}")
            sys.exit(1)
    else:
        print(json.dumps(review_data, indent=2, ensure_ascii=False))


def main():
    """Main CLI entry point for PR review."""
    parser = argparse.ArgumentParser(
        description="Analyze pull requests using Gemini AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Review a PR from JSON file
  python -m cli.pr_review --pr-file pr_data.json

  # Review a PR with inline data
  python -m cli.pr_review --title "Add feature" --body "Description" --files changes.json

  # Review with custom configuration
  python -m cli.pr_review --pr-file pr.json --config custom_config.yml

  # Review and save to file
  python -m cli.pr_review --pr-file pr.json --output review.json

  # Review with repo URL for context-specific prompts
  python -m cli.pr_review --pr-file pr.json --repo-url "https://github.com/user/repo"

PR JSON file format:
{
  "title": "PR title",
  "body": "PR description",
  "repo_url": "https://github.com/user/repo",
  "file_changes": [
    {
      "filename": "path/to/file.py",
      "status": "modified",
      "additions": 10,
      "deletions": 5,
      "patch": "@@ -1,5 +1,10 @@\\n..."
    }
  ]
}
        """,
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--pr-file", type=str, help="Path to JSON file containing PR data")
    input_group.add_argument("--title", type=str, help="PR title (use with --body and --files)")

    # Additional inline input options
    parser.add_argument("--body", type=str, help="PR description/body (use with --title)")
    parser.add_argument("--files", type=str, help="Path to JSON file containing file changes (use with --title)")
    parser.add_argument("--repo-url", type=str, help="Repository URL for context-specific analysis")

    # Configuration options
    parser.add_argument("--config", type=str, help="Path to custom prompt configuration YAML file")
    parser.add_argument("--model", type=str, help="Gemini model name (default: gemini-2.0-flash-001)")
    parser.add_argument("--api-key", type=str, help="Gemini API key (or set GEMINI_API_KEY env var)")

    # Output options
    parser.add_argument("--output", "-o", type=str, help="Output file for review results (JSON)")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format (default: json)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load PR data
    if args.pr_file:
        logger.info(f"Loading PR data from {args.pr_file}")
        pr_data = load_pr_data(args.pr_file)
        title = pr_data.get("title", "Untitled PR")
        body = pr_data.get("body", "")
        file_changes = pr_data.get("file_changes", [])
        repo_url = args.repo_url or pr_data.get("repo_url", "")
    else:
        # Inline input
        if not args.body:
            logger.error("--body is required when using --title")
            sys.exit(1)
        if not args.files:
            logger.error("--files is required when using --title")
            sys.exit(1)

        title = args.title
        body = args.body
        file_changes = load_pr_data(args.files)
        repo_url = args.repo_url or ""

    # Validate file_changes format
    if not isinstance(file_changes, list):
        logger.error("file_changes must be a list of file change objects")
        sys.exit(1)

    logger.info(f"Analyzing PR: {title}")
    logger.info(f"File changes: {len(file_changes)} file(s)")

    # Initialize PR analyzer
    try:
        analyzer = PRAnalyzer(
            api_key=args.api_key,
            config_path=args.config,
            model_name=args.model
        )
    except Exception as e:
        logger.error(f"Error initializing PR analyzer: {e}")
        sys.exit(1)

    # Perform review
    try:
        review = analyzer.review_pr(
            title=title,
            body=body,
            file_changes=file_changes,
            repo_url=repo_url
        )
        logger.info("Review completed successfully")

        # Format output
        if args.format == "markdown":
            output_text = analyzer.format_review_summary(review)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_text)
                logger.info(f"Markdown review saved to {args.output}")
            else:
                print(output_text)
        else:
            # JSON format
            review_dict = review.model_dump()
            save_review(review_dict, args.output)

    except Exception as e:
        logger.error(f"Error during PR review: {e}")
        import traceback
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

