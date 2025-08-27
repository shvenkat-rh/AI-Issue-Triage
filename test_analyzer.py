"""Test script for the Gemini Issue Analyzer."""

import os
from dotenv import load_dotenv
from gemini_analyzer import GeminiIssueAnalyzer

# Load environment variables
load_dotenv()


def test_analyzer():
    """Test the analyzer with sample issues."""
    
    # Check if we have an API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found in environment variables.")
        print("Please create a .env file with your API key.")
        return
    
    print("Testing Gemini Issue Analyzer...")
    
    try:
        # Initialize analyzer
        analyzer = GeminiIssueAnalyzer()
        print("Analyzer initialized successfully")
        
        # Test cases
        test_cases = [
            {
                "title": "CLI argument parsing fails with special characters",
                "description": """
                When running ansible-creator with arguments containing special characters like quotes or backslashes,
                the argument parser throws an error. This happens specifically when using:
                
                ansible-creator init --name "my-collection" --path "/path/with spaces/"
                
                Expected: Should handle special characters gracefully
                Actual: Crashes with ArgumentError
                
                Error message: ArgumentError: argument --name: invalid value
                Environment: Python 3.9, Linux
                """
            },
            {
                "title": "Add support for custom Jinja2 filters in templates", 
                "description": """
                It would be useful to allow users to define custom Jinja2 filters that can be used
                in ansible-creator templates. Currently, only built-in filters are available.
                
                Proposed functionality:
                - Allow users to register custom filters
                - Provide a plugin system for filters
                - Include some common utility filters by default
                
                Use case: Custom date formatting, string manipulation, etc.
                """
            },
            {
                "title": "Memory leak in template rendering for large collections",
                "description": """
                When generating large collections with many files, the memory usage grows continuously
                and doesn't get released. This eventually leads to OOM errors on systems with limited RAM.
                
                Steps to reproduce:
                1. Create a collection with 1000+ files
                2. Run ansible-creator init
                3. Monitor memory usage during generation
                4. Memory keeps growing and never gets released
                
                System: 8GB RAM, Python 3.10, Ubuntu 22.04
                """
            }
        ]
        
        # Analyze each test case
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest Case {i}: {test_case['title']}")
            print("=" * 60)
            
            try:
                analysis = analyzer.analyze_issue(
                    test_case["title"],
                    test_case["description"]
                )
                
                print(f"Analysis completed!")
                print(f"Issue Type: {analysis.issue_type.value}")
                print(f"Severity: {analysis.severity.value}")
                print(f"Confidence: {analysis.confidence_score:.1%}")
                print(f"Primary Cause: {analysis.root_cause_analysis.primary_cause}")
                print(f"Solutions: {len(analysis.proposed_solutions)} proposed")
                
                if analysis.proposed_solutions:
                    print(f"   First solution: {analysis.proposed_solutions[0].description}")
                
            except Exception as e:
                print(f"Analysis failed: {str(e)}")
        
        print(f"\nTesting completed successfully!")
        
    except Exception as e:
        print(f"Initialization failed: {str(e)}")


if __name__ == "__main__":
    test_analyzer()
