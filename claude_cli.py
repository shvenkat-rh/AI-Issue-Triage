#!/usr/bin/env python3
"""Command-line interface for Claude Issue Analyzer.

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
  --api-key TEXT               Anthropic API key or GCP Project ID for Vertex AI
                               (default: from ANTHROPIC_API_KEY or 
                               ANTHROPIC_VERTEX_PROJECT_ID env var)
  --retries INTEGER            Maximum number of retry attempts for low quality
                               responses (default: 2)

OUTPUT OPTIONS:
  --output, -o PATH            Save analysis results to file instead of stdout
  --format [text|json]         Output format: 'text' for human-readable format,
                               'json' for structured data (default: text)

BEHAVIOR OPTIONS:
  --quiet, -q                  Suppress progress messages, only show results
  --version                    Show version information and exit

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
  ANTHROPIC_API_KEY           API key for Anthropic Claude service (alternative to --api-key)
  ANTHROPIC_VERTEX_PROJECT_ID GCP Project ID for Claude Code via Vertex AI
  CLAUDE_CODE_USE_VERTEX      Set to "1" to enable Vertex AI mode
  CLOUD_ML_REGION             GCP region for Vertex AI (default: us-east5)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from claude_analyzer import ClaudeIssueAnalyzer
from models import IssueType, Severity


def format_analysis_text(analysis) -> str:
    """Format analysis results for text output."""
    
    # Header
    output = []
    
    output.append(f"CLAUDE ISSUE ANALYSIS REPORT")
    
    output.append(f"Title: {analysis.title}")
    output.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append("")
    
    # Classification
    output.append("CLASSIFICATION")
    output.append("-" * 40)
    output.append(f"Type: {analysis.issue_type.value.upper()}")
    output.append(f"Severity: {analysis.severity.value.upper()}")
    output.append(f"Confidence: {analysis.confidence_score:.1%}")
    output.append("")
    
    # Summary
    output.append("ANALYSIS SUMMARY")
    output.append("-" * 40)
    output.append(analysis.analysis_summary)
    output.append("")
    
    # Root Cause Analysis
    output.append("ROOT CAUSE ANALYSIS")
    output.append("-" * 40)
    output.append(f"Primary Cause: {analysis.root_cause_analysis.primary_cause}")
    output.append("")
    
    if analysis.root_cause_analysis.contributing_factors:
        output.append("Contributing Factors:")
        for factor in analysis.root_cause_analysis.contributing_factors:
            output.append(f"  • {factor}")
        output.append("")
    
    if analysis.root_cause_analysis.affected_components:
        output.append("Affected Components:")
        for component in analysis.root_cause_analysis.affected_components:
            output.append(f"  • {component}")
        output.append("")
    
    if analysis.root_cause_analysis.related_code_locations:
        output.append("Related Code Locations:")
        for location in analysis.root_cause_analysis.related_code_locations:
            loc_parts = [f"File: {location.file_path}"]
            if location.line_number:
                loc_parts.append(f"Line: {location.line_number}")
            if location.class_name:
                loc_parts.append(f"Class: {location.class_name}")
            if location.function_name:
                loc_parts.append(f"Function: {location.function_name}")
            output.append(f"  • {' | '.join(loc_parts)}")
        output.append("")
    
    # Proposed Solutions
    output.append("PROPOSED SOLUTIONS")
    output.append("-" * 40)
    
    for i, solution in enumerate(analysis.proposed_solutions, 1):
        output.append(f"Solution {i}: {solution.description}")
        output.append("")
        
        output.append(f"Location:")
        loc_parts = [f"File: {solution.location.file_path}"]
        if solution.location.line_number:
            loc_parts.append(f"Line: {solution.location.line_number}")
        if solution.location.class_name:
            loc_parts.append(f"Class: {solution.location.class_name}")
        if solution.location.function_name:
            loc_parts.append(f"Function: {solution.location.function_name}")
        output.append(f"  {' | '.join(loc_parts)}")
        output.append("")
        
        output.append(f"Rationale:")
        output.append(f"  {solution.rationale}")
        output.append("")
        
        output.append(f"Code Changes:")
        # Indent code changes
        code_lines = solution.code_changes.split('\n')
        for line in code_lines:
            output.append(f"  {line}")
        output.append("")
        
        if i < len(analysis.proposed_solutions):
            output.append("-" * 40)
    
    
    return "\n".join(output)


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Claude Issue Analyzer - AI-powered issue analysis for codebases using Anthropic Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python claude_cli.py

  # Direct analysis
  python claude_cli.py --title "Login bug" --description "Users can't login"

  # From file
  python claude_cli.py --file issue.txt

  # With custom source of truth
  python claude_cli.py --title "Bug" --description "Description" --source-path /path/to/codebase.txt

  # With custom prompt template
  python claude_cli.py --title "Bug" --description "Description" --custom-prompt /path/to/prompt.txt
  
  # Configure retry attempts
  python claude_cli.py --title "Bug" --description "Description" --retries 3

  # Output to file
  python claude_cli.py --title "Bug" --description "Description" --output analysis.txt

  # JSON output
  python claude_cli.py --title "Bug" --description "Description" --format json
        """
    )
    
    # Input options
    parser.add_argument(
        "--title", "-t",
        help="Issue title"
    )
    
    parser.add_argument(
        "--description", "-d",
        help="Issue description"
    )
    
    parser.add_argument(
        "--file", "-f",
        type=Path,
        help="Read issue from file (format: title on first line, description on remaining lines)"
    )
    
    # Output options
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file (default: stdout)"
    )
    
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    
    # Other options
    parser.add_argument(
        "--source-path", "-s",
        type=Path,
        help="Path to source of truth file (default: repomix-output.txt)"
    )
    
    parser.add_argument(
        "--custom-prompt",
        type=Path,
        help="Path to custom prompt template file (overrides default prompt)"
    )
    
    parser.add_argument(
        "--api-key",
        help="Anthropic API key or GCP Project ID for Vertex AI (default: from ANTHROPIC_API_KEY or ANTHROPIC_VERTEX_PROJECT_ID env var)"
    )
    
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Maximum number of retry attempts for low quality responses (default: 2)"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress messages"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Claude Issue Analyzer 1.0.0"
    )
    
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
            lines = content.split('\n', 1)
            title = lines[0].strip()
            description = lines[1].strip() if len(lines) > 1 else ""
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.title and args.description:
        title = args.title
        description = args.description
    
    elif args.title or args.description:
        print("Error: Both --title and --description are required when not using --file", file=sys.stderr)
        sys.exit(1)
    
    else:
        # Interactive mode
        if not args.quiet:
            print("Claude Issue Analyzer - Interactive Mode")
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
            
            description = '\n'.join(description_lines).strip()
            if not description:
                print("Error: Description cannot be empty", file=sys.stderr)
                sys.exit(1)
                
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
            print("Initializing Claude analyzer...")
        
        analyzer = ClaudeIssueAnalyzer(
            api_key=args.api_key,
            source_path=str(args.source_path) if args.source_path else None,
            custom_prompt_path=str(args.custom_prompt) if args.custom_prompt else None
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


