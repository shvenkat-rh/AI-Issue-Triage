#!/usr/bin/env python3
"""Command-line interface for the Cosine Similarity Batch Duplicate Issue Analyzer."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from utils.duplicate.batch_cosine_duplicate import CosineBatchDuplicateAnalyzer
from utils.models import IssueReference

# Import utility functions from cosine_check.py and batch_duplicate_check.py
from cli.cosine_check import load_issues_from_file, create_sample_issues_file, validate_issues_file
from cli.batch_duplicate_check import load_new_issues_from_file, create_sample_new_issues_file


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Cosine Similarity Batch Duplicate Issue Analyzer - Detect duplicate issues using TF-IDF and cosine similarity in batch mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create sample files
  ai-triage-batch-cosine --create-sample-existing existing_issues.json
  ai-triage-batch-cosine --create-sample-new new_issues.json

  # Batch check multiple new issues for duplicates
  ai-triage-batch-cosine --new-issues new_issues.json --existing-issues existing_issues.json
  # or: python -m cli.batch_cosine_check --new-issues ... --existing-issues ...

  # Validate an existing issues file
  ai-triage-batch-cosine --validate-issues existing_issues.json

  # Custom similarity threshold
  ai-triage-batch-cosine --new-issues new.json --existing-issues existing.json --threshold 0.8

  # Show top similar issues for each new issue
  ai-triage-batch-cosine --new-issues new.json --existing-issues existing.json --show-similar 3

  # Output to file
  ai-triage-batch-cosine --new-issues new.json --existing-issues existing.json --output results.json

  # Text output format
  ai-triage-batch-cosine --new-issues new.json --existing-issues existing.json --format text

Supported JSON formats:
  NEW ISSUES FILE: Array of objects with 'title' and 'description'
  [{"title": "Bug", "description": "Description"}, ...]
  
  EXISTING ISSUES FILE: Same format as cosine_check.py
  Required fields: title, and either (issue_id OR id OR number)
  Optional fields: description/body, status/state, created_date/created_at, url/html_url
  
  Example GitHub format:
  [{"number": 1, "title": "Bug", "body": "Description", "state": "open"}]
  
  Example standard format:
  [{"issue_id": "1", "title": "Bug", "description": "Description", "status": "open"}]

Algorithm Details:
  This tool uses TF-IDF (Term Frequency-Inverse Document Frequency) vectorization
  combined with cosine similarity to detect duplicate issues in batch mode. It:
  - Processes multiple new issues simultaneously for efficiency
  - Preprocesses text by removing special characters and normalizing case
  - Weights issue titles more heavily than descriptions
  - Uses unigrams and bigrams for better context understanding
  - Calculates cosine similarity between vector representations
  - Provides detailed similarity reasons and confidence scores
  
  Batch processing is significantly faster than individual checks when analyzing
  multiple issues because it vectorizes all issues at once.
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

    parser.add_argument(
        "--threshold", type=float, default=0.7, help="Similarity threshold for duplicate detection (default: 0.7)"
    )

    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.6,
        help="Confidence threshold for high-confidence results (default: 0.6)",
    )

    parser.add_argument(
        "--show-similar", type=int, metavar="N", help="Show top N most similar issues for each new issue"
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

    # Validate threshold values
    if not 0.0 <= args.threshold <= 1.0:
        parser.error("--threshold must be between 0.0 and 1.0")

    if not 0.0 <= args.confidence_threshold <= 1.0:
        parser.error("--confidence-threshold must be between 0.0 and 1.0")

    # Run batch duplicate detection
    run_batch_duplicate_detection(args)


def run_batch_duplicate_detection(args):
    """Run batch duplicate detection with provided arguments."""
    try:
        # Initialize analyzer
        if not args.quiet:
            print("Initializing cosine similarity batch duplicate analyzer...")
        analyzer = CosineBatchDuplicateAnalyzer(
            similarity_threshold=args.threshold,
            confidence_threshold=args.confidence_threshold
        )

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
            print(f"Analyzing for duplicates using cosine similarity (batch mode)...")
        results = analyzer.batch_detect_duplicates(new_issues, existing_issues)

        # Get similar issues if requested
        similar_issues_batch = []
        if args.show_similar:
            if not args.quiet:
                print(f"Finding top {args.show_similar} similar issues for each...")
            similar_issues_batch = analyzer.find_most_similar_issues_batch(
                new_issues, existing_issues, top_k=args.show_similar
            )

        # Output results
        if args.format == "json":
            output_json_batch(results, new_issues, similar_issues_batch, args.output, args.quiet)
        else:
            output_text_batch(results, new_issues, similar_issues_batch, args.output, args.quiet)

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


def output_text_batch(results, new_issues, similar_issues_batch, output_file, quiet):
    """Output batch results in text format."""
    output_lines = []
    
    output_lines.append("COSINE SIMILARITY BATCH DUPLICATE DETECTION RESULTS")
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
        output_lines.append(f"Similarity Score: {result.similarity_score:.3f}")
        output_lines.append(f"Confidence Score: {result.confidence_score:.3f}")

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

        # Show similar issues if provided
        if similar_issues_batch and i - 1 < len(similar_issues_batch):
            similar_issues = similar_issues_batch[i - 1]
            if similar_issues:
                output_lines.append(f"\nTOP SIMILAR ISSUES:")
                output_lines.append("-" * 40)
                for j, (issue, similarity) in enumerate(similar_issues, 1):
                    output_lines.append(f"{j}. {issue.issue_id}: {issue.title}")
                    output_lines.append(f"   Similarity: {similarity:.3f}")
                    output_lines.append(f"   Status: {issue.status}")
                    if issue.url:
                        output_lines.append(f"   URL: {issue.url}")
                    output_lines.append("")

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


def output_json_batch(results, new_issues, similar_issues_batch, output_file, quiet):
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

    for i, (result, new_issue) in enumerate(zip(results, new_issues)):
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
            "similar_issues": [],
        }

        if result.duplicate_of:
            result_data["duplicate_of"] = {
                "issue_id": result.duplicate_of.issue_id,
                "title": result.duplicate_of.title,
                "status": result.duplicate_of.status,
                "url": result.duplicate_of.url,
            }

        # Add similar issues if provided
        if similar_issues_batch and i < len(similar_issues_batch):
            similar_issues = similar_issues_batch[i]
            result_data["similar_issues"] = [
                {
                    "issue_id": issue.issue_id,
                    "title": issue.title,
                    "status": issue.status,
                    "url": issue.url,
                    "similarity_score": similarity,
                }
                for issue, similarity in similar_issues
            ]

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

