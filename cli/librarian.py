#!/usr/bin/env python3
"""CLI for Librarian - Identifies relevant files for issue analysis."""

import argparse
import json
import logging
import sys
from pathlib import Path

from utils.librarian import LibrarianAnalyzer

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    """Main CLI entry point for Librarian."""
    parser = argparse.ArgumentParser(
        description="Librarian - Identify relevant files for issue analysis (Pass 1 of Two-Pass Architecture)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Identify relevant files for an issue
  python -m cli.librarian --title "Bug" --description "Login fails" --skeleton repomix-output.txt

  # Output as JSON
  python -m cli.librarian --title "Bug" --description "Details" --output files.json

  # Specify custom skeleton file
  python -m cli.librarian --title "Bug" --description "Details" --skeleton custom-skeleton.txt
        """,
    )

    # Input options
    parser.add_argument("--title", "-t", required=True, help="Issue title")
    parser.add_argument("--description", "-d", required=True, help="Issue description")
    parser.add_argument(
        "--skeleton",
        "-s",
        type=str,
        default="repomix-output.txt",
        help="Path to skeleton/compressed codebase file (default: repomix-output.txt)",
    )

    # Configuration options
    parser.add_argument("--api-key", type=str, help="Gemini API key (or set GEMINI_API_KEY env var)")
    parser.add_argument(
        "--model", type=str, default="gemini-2.0-flash-001", help="Gemini model name (default: gemini-2.0-flash-001)"
    )

    # Output options
    parser.add_argument("--output", "-o", type=str, help="Output file for results (JSON)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"Initializing Librarian with skeleton: {args.skeleton}")

    # Initialize Librarian
    try:
        librarian = LibrarianAnalyzer(api_key=args.api_key, skeleton_path=args.skeleton, model_name=args.model)
    except Exception as e:
        logger.error(f"Error initializing Librarian: {e}")
        sys.exit(1)

    # Identify relevant files
    try:
        logger.info(f"Analyzing issue: {args.title}")
        file_paths = librarian.identify_relevant_files(title=args.title, issue_description=args.description)

        if not file_paths:
            logger.warning("No relevant files identified")
            sys.exit(1)

        logger.info(f"✅ Identified {len(file_paths)} relevant file(s)")

        # Prepare output
        result = {"issue_title": args.title, "issue_description": args.description, "relevant_files": file_paths}

        # Output results
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            logger.info(f"Results saved to {args.output}")
        else:
            print(json.dumps(result, indent=2))

    except Exception as e:
        logger.error(f"Error identifying relevant files: {e}")
        import traceback

        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
