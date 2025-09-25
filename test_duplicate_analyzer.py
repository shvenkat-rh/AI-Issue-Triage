"""Test script for the Gemini Duplicate Issue Analyzer."""

import os
from datetime import datetime
from duplicate_analyzer import GeminiDuplicateAnalyzer
from models import IssueReference

def create_sample_issues():
    """Create sample issues for testing."""
    return [
        IssueReference(
            issue_id="ISSUE-001",
            title="Login page crashes when clicking submit button",
            description="When I click the submit button on the login page, the application crashes with a JavaScript error. The console shows 'TypeError: Cannot read property of undefined'. This happens in Chrome and Firefox.",
            status="open",
            created_date="2024-01-15",
            url="https://github.com/example/repo/issues/1"
        ),
        IssueReference(
            issue_id="ISSUE-002", 
            title="Database connection timeout in production",
            description="The application frequently shows database connection timeout errors in production environment. This affects user authentication and data retrieval. Error occurs approximately every 30 minutes.",
            status="open",
            created_date="2024-01-20",
            url="https://github.com/example/repo/issues/2"
        ),
        IssueReference(
            issue_id="ISSUE-003",
            title="User authentication module memory leak",
            description="Memory usage continuously increases in the authentication service. After 24 hours of operation, memory usage reaches 2GB and the service becomes unresponsive. Restarting the service temporarily fixes the issue.",
            status="open", 
            created_date="2024-01-25",
            url="https://github.com/example/repo/issues/3"
        ),
        IssueReference(
            issue_id="ISSUE-004",
            title="CSS styling broken on mobile devices",
            description="The responsive CSS layout is broken on mobile devices. Text overlaps, buttons are not clickable, and the navigation menu doesn't work properly on screens smaller than 768px.",
            status="closed",
            created_date="2024-01-10",
            url="https://github.com/example/repo/issues/4"
        )
    ]

def test_duplicate_detection():
    """Test the duplicate detection functionality."""
    print("=" * 60)
    print("GEMINI DUPLICATE ISSUE ANALYZER TEST")
    print("=" * 60)
    
    # Check if API key is available
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ ERROR: No Gemini API key found!")
        print("   Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")
        return
    
    try:
        # Initialize the analyzer
        analyzer = GeminiDuplicateAnalyzer(api_key=api_key)
        print("✅ Duplicate analyzer initialized successfully")
        
        # Create sample existing issues
        existing_issues = create_sample_issues()
        print(f"📋 Created {len(existing_issues)} sample issues")
        
        # Test cases
        test_cases = [
            {
                "name": "Clear Duplicate - Same Login Issue",
                "title": "Submit button on login form causes application crash",
                "description": "Clicking the submit button on the login form results in a crash. Getting a TypeError about undefined property in the browser console. Tested on Chrome and Safari."
            },
            {
                "name": "Potential Duplicate - Database Issue", 
                "title": "Connection timeouts to database server",
                "description": "Getting frequent timeout errors when connecting to the database. This is happening in our production environment and causing authentication failures."
            },
            {
                "name": "Different Issue - New Feature Request",
                "title": "Add dark mode theme support",
                "description": "Users are requesting a dark mode theme option in the application settings. This would improve user experience especially for users working in low-light environments."
            },
            {
                "name": "Similar but Different - Performance Issue",
                "title": "Application becomes slow after extended use",
                "description": "The application performance degrades significantly after being used for several hours. Pages take longer to load and user interactions become sluggish."
            }
        ]
        
        print("\n" + "=" * 60)
        print("RUNNING DUPLICATE DETECTION TESTS")
        print("=" * 60)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🔍 Test {i}: {test_case['name']}")
            print("-" * 40)
            print(f"New Issue Title: {test_case['title']}")
            print(f"New Issue Description: {test_case['description'][:100]}...")
            
            try:
                # Perform duplicate detection
                result = analyzer.detect_duplicate(
                    test_case["title"],
                    test_case["description"],
                    existing_issues
                )
                
                # Display results
                print(f"\n📊 RESULTS:")
                print(f"   Is Duplicate: {'✅ YES' if result.is_duplicate else '❌ NO'}")
                print(f"   Similarity Score: {result.similarity_score:.2f}")
                print(f"   Confidence Score: {result.confidence_score:.2f}")
                
                if result.is_duplicate and result.duplicate_of:
                    print(f"   Duplicate of: {result.duplicate_of.issue_id} - {result.duplicate_of.title}")
                
                print(f"   Similarity Reasons:")
                for reason in result.similarity_reasons:
                    print(f"     • {reason}")
                
                print(f"   Recommendation: {result.recommendation}")
                
            except Exception as e:
                print(f"❌ Error in test {i}: {str(e)}")
        
        print("\n" + "=" * 60)
        print("TESTING BATCH DUPLICATE DETECTION")
        print("=" * 60)
        
        # Test batch processing
        new_issues = [
            {
                "title": "Login form JavaScript error on submit",
                "description": "JavaScript error occurs when submitting login form, causing page crash"
            },
            {
                "title": "Add user profile picture upload feature",
                "description": "Users should be able to upload and change their profile pictures"
            }
        ]
        
        try:
            batch_results = analyzer.batch_detect_duplicates(new_issues, existing_issues)
            
            for i, (issue, result) in enumerate(zip(new_issues, batch_results), 1):
                print(f"\n🔍 Batch Test {i}: {issue['title']}")
                print(f"   Is Duplicate: {'✅ YES' if result.is_duplicate else '❌ NO'}")
                print(f"   Similarity Score: {result.similarity_score:.2f}")
                if result.duplicate_of:
                    print(f"   Duplicate of: {result.duplicate_of.issue_id}")
                    
        except Exception as e:
            print(f"❌ Error in batch testing: {str(e)}")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Failed to initialize analyzer: {str(e)}")

def test_edge_cases():
    """Test edge cases for the duplicate analyzer."""
    print("\n" + "=" * 60)
    print("TESTING EDGE CASES")
    print("=" * 60)
    
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ No API key available for edge case testing")
        return
    
    try:
        analyzer = GeminiDuplicateAnalyzer(api_key=api_key)
        
        # Test with empty issues list
        print("\n🔍 Testing with no existing issues...")
        result = analyzer.detect_duplicate(
            "New issue title",
            "New issue description",
            []
        )
        print(f"   Result: {'Duplicate' if result.is_duplicate else 'Not duplicate'}")
        print(f"   Recommendation: {result.recommendation}")
        
        # Test with only closed issues
        print("\n🔍 Testing with only closed issues...")
        closed_issues = [
            IssueReference(
                issue_id="CLOSED-001",
                title="Old resolved bug",
                description="This bug was fixed in version 2.0",
                status="closed",
                created_date="2023-12-01"
            )
        ]
        
        result = analyzer.detect_duplicate(
            "Similar old bug",
            "This looks like the old bug that was fixed",
            closed_issues
        )
        print(f"   Result: {'Duplicate' if result.is_duplicate else 'Not duplicate'}")
        print(f"   Recommendation: {result.recommendation}")
        
    except Exception as e:
        print(f"❌ Error in edge case testing: {str(e)}")

if __name__ == "__main__":
    test_duplicate_detection()
    test_edge_cases()
