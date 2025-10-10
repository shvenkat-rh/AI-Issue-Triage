"""Test suite for the Gemini Duplicate Issue Analyzer."""

import os
import pytest
from datetime import datetime
from duplicate_analyzer import GeminiDuplicateAnalyzer
from models import IssueReference, DuplicateDetectionResult


@pytest.fixture
def api_key():
    """Fixture to get API key."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        pytest.skip("API key not found")
    return key


@pytest.fixture
def analyzer(api_key):
    """Fixture to create a GeminiDuplicateAnalyzer instance."""
    return GeminiDuplicateAnalyzer(api_key=api_key)


@pytest.fixture
def sample_existing_issues():
    """Fixture providing sample existing issues."""
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


class TestDuplicateAnalyzer:
    """Test suite for duplicate detection functionality."""
    
    def test_analyzer_initialization(self, api_key):
        """Test that analyzer initializes correctly with API key."""
        analyzer = GeminiDuplicateAnalyzer(api_key=api_key)
        assert analyzer is not None
        assert analyzer.api_key == api_key
    
    def test_analyzer_without_api_key(self):
        """Test that analyzer raises error without API key."""
        original_key = os.getenv("GEMINI_API_KEY")
        original_google_key = os.getenv("GOOGLE_API_KEY")
        
        # Temporarily remove API keys
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        if "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]
        
        try:
            with pytest.raises(ValueError):
                GeminiDuplicateAnalyzer()
        finally:
            # Restore API keys
            if original_key:
                os.environ["GEMINI_API_KEY"] = original_key
            if original_google_key:
                os.environ["GOOGLE_API_KEY"] = original_google_key
    
    def test_clear_duplicate_detection(self, analyzer, sample_existing_issues):
        """Test detecting a clear duplicate issue."""
        result = analyzer.detect_duplicate(
            title="Submit button on login form causes application crash",
            description="Clicking the submit button on the login form results in a crash. Getting a TypeError about undefined property in the browser console. Tested on Chrome and Safari.",
            existing_issues=sample_existing_issues
        )
        
        assert isinstance(result, DuplicateDetectionResult)
        assert result.is_duplicate or result.similarity_score > 0.5
        assert 0 <= result.similarity_score <= 1
        assert 0 <= result.confidence_score <= 1
        assert result.recommendation
    
    def test_different_issue_detection(self, analyzer, sample_existing_issues):
        """Test detecting a clearly different (non-duplicate) issue."""
        result = analyzer.detect_duplicate(
            title="Add dark mode theme support",
            description="Users are requesting a dark mode theme option in the application settings. This would improve user experience especially for users working in low-light environments.",
            existing_issues=sample_existing_issues
        )
        
        assert isinstance(result, DuplicateDetectionResult)
        assert not result.is_duplicate
        assert result.similarity_score < 0.7
        assert result.recommendation
    
    def test_empty_existing_issues(self, analyzer):
        """Test duplicate detection with no existing issues."""
        result = analyzer.detect_duplicate(
            title="New issue title",
            description="New issue description",
            existing_issues=[]
        )
        
        assert not result.is_duplicate
        assert result.duplicate_of is None
        assert result.similarity_score == 0.0
        assert "no open issues" in result.recommendation.lower()
    
    def test_only_closed_issues(self, analyzer):
        """Test duplicate detection with only closed issues."""
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
            title="Similar old bug",
            description="This looks like the old bug",
            existing_issues=closed_issues
        )
        
        assert not result.is_duplicate
        assert result.duplicate_of is None
    
    def test_batch_detection(self, analyzer, sample_existing_issues):
        """Test batch duplicate detection."""
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
        
        results = analyzer.batch_detect_duplicates(new_issues, sample_existing_issues)
        
        assert len(results) == len(new_issues)
        for result in results:
            assert isinstance(result, DuplicateDetectionResult)
            assert 0 <= result.similarity_score <= 1
            assert 0 <= result.confidence_score <= 1
    
    def test_duplicate_result_fields(self, analyzer, sample_existing_issues):
        """Test that duplicate detection result has all required fields."""
        result = analyzer.detect_duplicate(
            title="Test issue",
            description="Test description",
            existing_issues=sample_existing_issues
        )
        
        assert hasattr(result, 'is_duplicate')
        assert hasattr(result, 'duplicate_of')
        assert hasattr(result, 'similarity_score')
        assert hasattr(result, 'similarity_reasons')
        assert hasattr(result, 'confidence_score')
        assert hasattr(result, 'recommendation')
        
        assert isinstance(result.is_duplicate, bool)
        assert isinstance(result.similarity_score, (int, float))
        assert isinstance(result.confidence_score, (int, float))
        assert isinstance(result.similarity_reasons, list)
        assert isinstance(result.recommendation, str)
    
    def test_similarity_score_range(self, analyzer, sample_existing_issues):
        """Test that similarity scores are within valid range."""
        test_cases = [
            ("Login crash", "App crashes on login"),
            ("Database timeout", "Connection timeout to DB"),
            ("New feature request", "Add export functionality")
        ]
        
        for title, description in test_cases:
            result = analyzer.detect_duplicate(title, description, sample_existing_issues)
            assert 0.0 <= result.similarity_score <= 1.0
            assert 0.0 <= result.confidence_score <= 1.0
    
    def test_find_most_similar_issue(self, analyzer, sample_existing_issues):
        """Test finding the most similar issue."""
        result = analyzer.find_most_similar_issue(
            "Login button causes crash",
            "Clicking login button crashes the app",
            sample_existing_issues
        )
        
        if result is not None:
            issue, score = result
            assert isinstance(issue, IssueReference)
            assert 0.0 <= score <= 1.0


class TestEdgeCases:
    """Test edge cases for duplicate detection."""
    
    def test_very_long_description(self, analyzer, sample_existing_issues):
        """Test handling very long issue descriptions."""
        long_description = "This is a test. " * 1000  # Very long description
        
        result = analyzer.detect_duplicate(
            title="Test issue",
            description=long_description,
            existing_issues=sample_existing_issues
        )
        
        assert isinstance(result, DuplicateDetectionResult)
    
    def test_special_characters(self, analyzer, sample_existing_issues):
        """Test handling special characters in issue text."""
        result = analyzer.detect_duplicate(
            title="Error: <script>alert('XSS')</script>",
            description="Issue with special chars: @#$%^&*(){}[]|\\:;\"'<>,.?/",
            existing_issues=sample_existing_issues
        )
        
        assert isinstance(result, DuplicateDetectionResult)
    
    def test_unicode_characters(self, analyzer, sample_existing_issues):
        """Test handling Unicode characters."""
        result = analyzer.detect_duplicate(
            title="Unicode test: 你好 مرحبا привет",
            description="Testing emoji: 🐛 🔧 ⚡ and unicode: ñ ü ö",
            existing_issues=sample_existing_issues
        )
        
        assert isinstance(result, DuplicateDetectionResult)
    
    def test_minimal_input(self, analyzer):
        """Test with minimal input."""
        result = analyzer.detect_duplicate(
            title="A",
            description="B",
            existing_issues=[]
        )
        
        assert not result.is_duplicate


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

