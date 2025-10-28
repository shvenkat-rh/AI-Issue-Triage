#!/usr/bin/env python3
"""Command-line interface for the Gemini Batch Duplicate Issue Analyzer."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from utils.duplicate.batch_gemini_duplicate import GeminiBatchDuplicateAnalyzer
from utils.models import IssueReference

# Import utility functions from duplicate_check.py
from cli.duplicate_check import load_issues_from_file, create_sample_issues_file, validate_issues_file


def load_new_issues_from_file(file_path: Path) -> List[dict]:
    """Load new issues to check for duplicates from a JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("ERROR: New issues file must contain a JSON array", file=sys.stderr)
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

            issues.append({
                "title": str(item["title"]),
                "description": str(item["description"])
            })

        return issues

    except FileNotFoundError:
        print(f"ERROR: File '{file_path}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in file '{file_path}': {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Error loading new issues file: {e}", file=sys.stderr)
        sys.exit(1)


def create_sample_new_issues_file(file_path: Path):
    """Create a sample new issues file for demonstration."""
    sample_issues = [
        {
            "title": "Submit button not working on login form",
            "description": "Users report that clicking the submit button on the login form doesn't work. The page doesn't respond and no error is shown."
        },
        {
            "title": "Database timeout errors during peak hours",
            "description": "During high traffic periods, the database connection times out frequently. This causes authentication failures."
        },
        {
            "title": "New feature request: Dark mode",
            "description": "Users are requesting a dark mode for the application to reduce eye strain during night time usage."
        }
    ]

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sample_issues, f, indent=2)

    print(f"Sample new issues file created: {file_path}")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Gemini Batch Duplicate Issue Analyzer - Detect duplicate issues using AI in batch mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create sample files
  ai-triage-batch-duplicate --create-sample-existing existing_issues.json
  ai-triage-batch-duplicate --create-sample-new new_issues.json

  # Batch check multiple new issues for duplicates
  ai-triage-batch-duplicate --new-issues new_issues.json --existing-issues existing_issues.json
  # or: python -m cli.batch_duplicate_check --new-issues ... --existing-issues ...

  # Validate an existing issues file
  ai-triage-batch-duplicate --validate-issues existing_issues.json

  # Output to file
  ai-triage-batch-duplicate --new-issues new.json --existing-issues existing.json --output results.json

  # Text output format
  ai-triage-batch-duplicate --new-issues new.json --existing-issues existing.json --format text

  # Custom polling interval
  ai-triage-batch-duplicate --new-issues new.json --existing-issues existing.json --poll-interval 15

Supported JSON formats:
  NEW ISSUES FILE: Array of objects with 'title' and 'description'
  [{"title": "Bug", "description": "Description"}, ...]
  
  EXISTING ISSUES FILE: Same format as duplicate_check.py
  Required fields: title, and either (issue_id OR id OR number)
  Optional fields: description/body, status/state, created_date/created_at, url/html_url
  
  Example GitHub format:
  [{"number": 1, "title": "Bug", "body": "Description", "state": "open"}]
  
  Example standard format:
  [{"issue_id": "1", "title": "Bug", "description": "Description", "status": "open"}]
        """,
    )

    parser.add_argument(
        "--new-issues", type=Path, help="Path to JSON file containing new issues to check for duplicates"
    )

    parser.add_argument(
        "--existing-issues", type=Path, help="Path to JSON file containing existing issues"
    )

    parser.add_argument(
        "--create-sample-existing", type=Path, metavar="FILE", help="Create a sample existing issues JSON file"
    )

    parser.add_argument(
        "--create-sample-new", type=Path, metavar="FILE", help="Create a sample new issues JSON file"
    )

    parser.add_argument(
        "--validate-issues", type=Path, metavar="FILE", help="Validate and show the format of an issues JSON file"
    )

    parser.add_argument("--api-key", help="Gemini API key (optional, can use GEMINI_API_KEY env var)")

    parser.add_argument(
        "--poll-interval", type=int, default=10, help="Seconds between polling for batch results (default: 10)"
    )

    parser.add_argument("--output", type=Path, help="Output file (default: stdout)")

    parser.add_argument("--format", choices=["text", "json"], default="json", help="Output format (default: json)")

    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress messages")

    args = parser.parse_args()

    # Create sample existing issues file if requested
    if args.create_sample_existing:
        create_sample_issues_file(str(args.create_sample_existing))
        return

    # Create sample new issues file if requested
    if args.create_sample_new:
        create_sample_new_issues_file(args.create_sample_new)
        return

    # Validate issues file if requested
    if args.validate_issues:
        validate_issues_file(str(args.validate_issues))
        return

    # Validate required arguments for batch duplicate detection
    if not args.new_issues or not args.existing_issues:
        parser.error("--new-issues and --existing-issues are required for batch duplicate detection")

    # Run batch duplicate detection
    run_batch_duplicate_detection(args)


def run_batch_duplicate_detection(args):
    """Run batch duplicate detection with provided arguments."""
    try:
        # Initialize analyzer
        if not args.quiet:
            print("Initializing Gemini batch duplicate analyzer...")
        analyzer = GeminiBatchDuplicateAnalyzer(api_key=args.api_key)

        # Load existing issues
        existing_issues = load_issues_from_file(str(args.existing_issues))
        if not args.quiet:
            print(f"Loaded {len(existing_issues)} existing issues")

        # Load new issues
        new_issues = load_new_issues_from_file(args.new_issues)
        if not args.quiet:
            print(f"Loaded {len(new_issues)} new issues to check")

        # Perform batch duplicate detection
        if not args.quiet:
            print(f"Checking for duplicates in batch mode...")
        results = analyzer.batch_detect_duplicates(
            new_issues, 
            existing_issues,
            poll_interval=args.poll_interval
        )

        # Output results
        if args.format == "json":
            output_json_batch(results, new_issues, args.output, args.quiet)
        else:
            output_text_batch(results, new_issues, args.output, args.quiet)

    except Exception as e:
        if args.format == "json":
            # For JSON output, return error as JSON
            error_output = {
                "error": str(e),
                "results": [],
                "timestamp": datetime.now().isoformat(),
            }
            output_text = json.dumps(error_output, indent=2)
            if args.output:
                args.output.write_text(output_text)
            else:
                print(output_text)
        else:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def output_text_batch(results, new_issues, output_file, quiet):
    """Output batch results in text format."""
    output_lines = []
    
    output_lines.append("GEMINI BATCH DUPLICATE DETECTION RESULTS")
    output_lines.append("=" * 80)
    output_lines.append(f"Analyzed {len(results)} issues")
    output_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output_lines.append("")

    # Summary statistics
    num_duplicates = sum(1 for r in results if r.is_duplicate)
    output_lines.append(f"Summary: {num_duplicates} duplicates found, {len(results) - num_duplicates} unique issues")
    output_lines.append("")

    # Individual results
    for i, (result, new_issue) in enumerate(zip(results, new_issues), 1):
        output_lines.append("=" * 80)
        output_lines.append(f"ISSUE {i} of {len(results)}")
        output_lines.append("=" * 80)
        output_lines.append(f"Title: {new_issue['title']}")
        output_lines.append(f"Is Duplicate: {'YES' if result.is_duplicate else 'NO'}")
        output_lines.append(f"Similarity Score: {result.similarity_score:.2f}")
        output_lines.append(f"Confidence Score: {result.confidence_score:.2f}")

        if result.is_duplicate and result.duplicate_of:
            output_lines.append(f"\nDUPLICATE OF:")
            output_lines.append(f"   ID: {result.duplicate_of.issue_id}")
            output_lines.append(f"   Title: {result.duplicate_of.title}")
            output_lines.append(f"   Status: {result.duplicate_of.status}")
            if result.duplicate_of.url:
                output_lines.append(f"   URL: {result.duplicate_of.url}")

        if result.similarity_reasons:
            output_lines.append(f"\nSIMILARITY REASONS:")
            for reason in result.similarity_reasons:
                output_lines.append(f"   • {reason}")

        output_lines.append(f"\nRECOMMENDATION:")
        output_lines.append(f"   {result.recommendation}")
        output_lines.append("")

    output_text = "\n".join(output_lines)

    # Write output
    if output_file:
        try:
            output_file.write_text(output_text)
            if not quiet:
                print(f"Results saved to {output_file}")
        except Exception as e:
            print(f"ERROR: Error writing to file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output_text)


def output_json_batch(results, new_issues, output_file, quiet):
    """Output batch results in JSON format."""
    output_data = {
        "summary": {
            "total_issues": len(results),
            "duplicates_found": sum(1 for r in results if r.is_duplicate),
            "unique_issues": sum(1 for r in results if not r.is_duplicate),
            "timestamp": datetime.now().isoformat(),
        },
        "results": []
    }

    for result, new_issue in zip(results, new_issues):
        result_data = {
            "new_issue": {
                "title": new_issue["title"],
                "description": new_issue["description"],
            },
            "is_duplicate": result.is_duplicate,
            "similarity_score": result.similarity_score,
            "confidence_score": result.confidence_score,
            "similarity_reasons": result.similarity_reasons,
            "recommendation": result.recommendation,
            "duplicate_of": None,
        }

        if result.duplicate_of:
            result_data["duplicate_of"] = {
                "issue_id": result.duplicate_of.issue_id,
                "title": result.duplicate_of.title,
                "status": result.duplicate_of.status,
                "url": result.duplicate_of.url,
            }

        output_data["results"].append(result_data)

    output_text = json.dumps(output_data, indent=2)

    # Write output
    if output_file:
        try:
            output_file.write_text(output_text)
            if not quiet:
                print(f"Results saved to {output_file}")
        except Exception as e:
            print(f"ERROR: Error writing to file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output_text)


if __name__ == "__main__":
    main()

