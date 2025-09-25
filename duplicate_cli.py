#!/usr/bin/env python3
"""Command-line interface for the Gemini Duplicate Issue Analyzer."""

import argparse
import json
import sys
from datetime import datetime
from typing import List

from duplicate_analyzer import GeminiDuplicateAnalyzer
from models import IssueReference


def load_issues_from_file(file_path: str) -> List[IssueReference]:
    """Load existing issues from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        issues = []
        for item in data:
            issues.append(IssueReference(**item))
        
        return issues
    except FileNotFoundError:
        print(f"❌ Error: File '{file_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in file '{file_path}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading issues: {e}")
        sys.exit(1)


def create_sample_issues_file(file_path: str):
    """Create a sample issues file for demonstration."""
    sample_issues = [
        {
            "issue_id": "ISSUE-001",
            "title": "Login page crashes when clicking submit button",
            "description": "When I click the submit button on the login page, the application crashes with a JavaScript error. The console shows 'TypeError: Cannot read property of undefined'. This happens in Chrome and Firefox.",
            "status": "open",
            "created_date": "2024-01-15",
            "url": "https://github.com/example/repo/issues/1"
        },
        {
            "issue_id": "ISSUE-002",
            "title": "Database connection timeout in production",
            "description": "The application frequently shows database connection timeout errors in production environment. This affects user authentication and data retrieval. Error occurs approximately every 30 minutes.",
            "status": "open", 
            "created_date": "2024-01-20",
            "url": "https://github.com/example/repo/issues/2"
        },
        {
            "issue_id": "ISSUE-003",
            "title": "User authentication module memory leak",
            "description": "Memory usage continuously increases in the authentication service. After 24 hours of operation, memory usage reaches 2GB and the service becomes unresponsive.",
            "status": "open",
            "created_date": "2024-01-25",
            "url": "https://github.com/example/repo/issues/3"
        }
    ]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(sample_issues, f, indent=2)
    
    print(f"✅ Sample issues file created: {file_path}")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Gemini Duplicate Issue Analyzer - Detect duplicate issues using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check if a new issue is a duplicate
  python duplicate_cli.py --title "Login error" --description "Can't log in" --issues issues.json

  # Create a sample issues file
  python duplicate_cli.py --create-sample issues.json
  
  # Interactive mode
  python duplicate_cli.py --interactive --issues issues.json
        """
    )
    
    parser.add_argument(
        '--title', 
        help='Title of the new issue to check for duplicates'
    )
    
    parser.add_argument(
        '--description', 
        help='Description of the new issue to check for duplicates'
    )
    
    parser.add_argument(
        '--issues', 
        help='Path to JSON file containing existing issues'
    )
    
    parser.add_argument(
        '--create-sample', 
        metavar='FILE',
        help='Create a sample issues JSON file at the specified path'
    )
    
    parser.add_argument(
        '--interactive', 
        action='store_true',
        help='Run in interactive mode'
    )
    
    parser.add_argument(
        '--api-key', 
        help='Gemini API key (optional, can use GEMINI_API_KEY env var)'
    )
    
    parser.add_argument(
        '--output', 
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    
    args = parser.parse_args()
    
    # Create sample file if requested
    if args.create_sample:
        create_sample_issues_file(args.create_sample)
        return
    
    # Interactive mode
    if args.interactive:
        run_interactive_mode(args.issues, args.api_key)
        return
    
    # Validate required arguments for duplicate detection
    if not args.title or not args.description or not args.issues:
        parser.error("--title, --description, and --issues are required for duplicate detection")
    
    # Run duplicate detection
    run_duplicate_detection(args)


def run_duplicate_detection(args):
    """Run duplicate detection with provided arguments."""
    try:
        # Initialize analyzer
        analyzer = GeminiDuplicateAnalyzer(api_key=args.api_key)
        
        # Load existing issues
        existing_issues = load_issues_from_file(args.issues)
        print(f"📋 Loaded {len(existing_issues)} existing issues")
        
        # Perform duplicate detection
        print(f"🔍 Checking for duplicates...")
        result = analyzer.detect_duplicate(
            args.title,
            args.description,
            existing_issues
        )
        
        # Output results
        if args.output == 'json':
            output_json(result)
        else:
            output_text(result, args.title)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def run_interactive_mode(issues_file: str, api_key: str):
    """Run the analyzer in interactive mode."""
    if not issues_file:
        print("❌ Error: --issues file is required for interactive mode")
        sys.exit(1)
    
    try:
        # Initialize analyzer
        analyzer = GeminiDuplicateAnalyzer(api_key=api_key)
        
        # Load existing issues
        existing_issues = load_issues_from_file(issues_file)
        print(f"📋 Loaded {len(existing_issues)} existing issues")
        
        print("\n" + "=" * 60)
        print("GEMINI DUPLICATE ISSUE ANALYZER - Interactive Mode")
        print("=" * 60)
        print("Enter 'quit' or 'exit' to stop\n")
        
        while True:
            try:
                # Get user input
                print("-" * 40)
                title = input("Enter issue title: ").strip()
                
                if title.lower() in ['quit', 'exit']:
                    print("👋 Goodbye!")
                    break
                
                if not title:
                    print("❌ Title cannot be empty")
                    continue
                
                description = input("Enter issue description: ").strip()
                
                if not description:
                    print("❌ Description cannot be empty")
                    continue
                
                # Perform duplicate detection
                print("\n🔍 Analyzing for duplicates...")
                result = analyzer.detect_duplicate(title, description, existing_issues)
                
                # Display results
                output_text(result, title)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def output_text(result, title: str):
    """Output results in text format."""
    print(f"\n📊 DUPLICATE DETECTION RESULTS")
    print("=" * 50)
    print(f"Issue Title: {title}")
    print(f"Is Duplicate: {'✅ YES' if result.is_duplicate else '❌ NO'}")
    print(f"Similarity Score: {result.similarity_score:.2f}")
    print(f"Confidence Score: {result.confidence_score:.2f}")
    
    if result.is_duplicate and result.duplicate_of:
        print(f"\n🔗 DUPLICATE OF:")
        print(f"   ID: {result.duplicate_of.issue_id}")
        print(f"   Title: {result.duplicate_of.title}")
        print(f"   Status: {result.duplicate_of.status}")
        if result.duplicate_of.url:
            print(f"   URL: {result.duplicate_of.url}")
    
    if result.similarity_reasons:
        print(f"\n📝 SIMILARITY REASONS:")
        for reason in result.similarity_reasons:
            print(f"   • {reason}")
    
    print(f"\n💡 RECOMMENDATION:")
    print(f"   {result.recommendation}")


def output_json(result):
    """Output results in JSON format."""
    output_data = {
        "is_duplicate": result.is_duplicate,
        "similarity_score": result.similarity_score,
        "confidence_score": result.confidence_score,
        "similarity_reasons": result.similarity_reasons,
        "recommendation": result.recommendation,
        "duplicate_of": None,
        "timestamp": datetime.now().isoformat()
    }
    
    if result.duplicate_of:
        output_data["duplicate_of"] = {
            "issue_id": result.duplicate_of.issue_id,
            "title": result.duplicate_of.title,
            "status": result.duplicate_of.status,
            "url": result.duplicate_of.url
        }
    
    print(json.dumps(output_data, indent=2))


if __name__ == "__main__":
    main()
