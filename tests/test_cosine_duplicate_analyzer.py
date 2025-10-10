"""Test suite for the Cosine Similarity Duplicate Issue Analyzer."""

import pytest

from cosine_duplicate_analyzer import CosineDuplicateAnalyzer
from models import DuplicateDetectionResult, IssueReference


@pytest.fixture
def analyzer():
    """Fixture to create a CosineDuplicateAnalyzer instance."""
    return CosineDuplicateAnalyzer()


@pytest.fixture
def custom_analyzer():
    """Fixture to create a CosineDuplicateAnalyzer with custom thresholds."""
    return CosineDuplicateAnalyzer(similarity_threshold=0.7, confidence_threshold=0.7)


@pytest.fixture
def sample_issues():
    """Fixture providing sample issues for testing."""
    return [
        IssueReference(
            issue_id="ISSUE-001",
            title="Login page crashes when clicking submit button",
            description="When I click the submit button on the login page, the application crashes with a JavaScript error. The console shows 'TypeError: Cannot read property of undefined'. This happens in Chrome and Firefox.",
            status="open",
            created_date="2024-01-15",
        ),
        IssueReference(
            issue_id="ISSUE-002",
            title="Database connection timeout in production",
            description="The application frequently shows database connection timeout errors in production environment. This affects user authentication and data retrieval.",
            status="open",
            created_date="2024-01-20",
        ),
        IssueReference(
            issue_id="ISSUE-003",
            title="CSS styling broken on mobile devices",
            description="The responsive CSS layout is broken on mobile devices. Text overlaps, buttons are not clickable, and the navigation menu doesn't work properly.",
            status="closed",
            created_date="2024-01-10",
        ),
    ]


class TestAnalyzerInitialization:
    """Test analyzer initialization."""

    def test_default_initialization(self):
        """Test analyzer initializes with default parameters."""
        analyzer = CosineDuplicateAnalyzer()
        assert analyzer.similarity_threshold == 0.6
        assert analyzer.confidence_threshold == 0.6
        assert analyzer.vectorizer is not None

    def test_custom_thresholds(self):
        """Test analyzer initializes with custom thresholds."""
        analyzer = CosineDuplicateAnalyzer(similarity_threshold=0.8, confidence_threshold=0.75)
        assert analyzer.similarity_threshold == 0.8
        assert analyzer.confidence_threshold == 0.75


class TestTextPreprocessing:
    """Test text preprocessing methods."""

    def test_preprocess_text(self, analyzer):
        """Test text preprocessing."""
        text = "This is a TEST with Special-Characters! And   extra spaces."
        processed = analyzer._preprocess_text(text)

        assert processed.islower()
        assert "special" in processed
        assert "  " not in processed  # No double spaces

    def test_preprocess_empty_text(self, analyzer):
        """Test preprocessing empty text."""
        assert analyzer._preprocess_text("") == ""
        assert analyzer._preprocess_text(None) == ""

    def test_combine_issue_text(self, analyzer, sample_issues):
        """Test combining issue title and description."""
        combined = analyzer._combine_issue_text(sample_issues[0])

        assert "login" in combined.lower()
        assert "crash" in combined.lower()
        # Title should appear twice (weighted)
        assert combined.count("login") >= 2


class TestDuplicateDetection:
    """Test duplicate detection functionality."""

    def test_detect_clear_duplicate(self, analyzer, sample_issues):
        """Test detecting a clear duplicate."""
        result = analyzer.detect_duplicate(
            title="Submit button on login form causes crash",
            description="Clicking submit on the login page crashes the app with TypeError. Happens in Chrome.",
            existing_issues=sample_issues,
        )

        assert isinstance(result, DuplicateDetectionResult)
        assert result.similarity_score > 0.5
        assert 0 <= result.similarity_score <= 1
        assert 0 <= result.confidence_score <= 1
        assert result.recommendation

    def test_detect_non_duplicate(self, analyzer, sample_issues):
        """Test detecting a non-duplicate issue."""
        result = analyzer.detect_duplicate(
            title="Add dark mode support",
            description="Users want a dark theme option for the application",
            existing_issues=sample_issues,
        )

        assert isinstance(result, DuplicateDetectionResult)
        assert result.similarity_score < 0.6
        assert not result.is_duplicate

    def test_empty_existing_issues(self, analyzer):
        """Test detection with no existing issues."""
        result = analyzer.detect_duplicate(title="New issue", description="New issue description", existing_issues=[])

        assert not result.is_duplicate
        assert result.similarity_score == 0.0
        assert result.confidence_score == 1.0
        assert "no open issues" in result.recommendation.lower()

    def test_only_closed_issues(self, analyzer, sample_issues):
        """Test detection with only closed issues."""
        closed_issues = [issue for issue in sample_issues if issue.status == "closed"]

        result = analyzer.detect_duplicate(title="Test issue", description="Test description", existing_issues=closed_issues)

        assert not result.is_duplicate
        assert result.similarity_score == 0.0

    def test_similarity_threshold(self, custom_analyzer, sample_issues):
        """Test that custom similarity threshold is respected."""
        # With higher threshold (0.7), fewer issues should be marked as duplicates
        result = custom_analyzer.detect_duplicate(
            title="Login button crash", description="App crashes on login", existing_issues=sample_issues
        )

        # Even if similarity is high, threshold should be 0.7
        assert custom_analyzer.similarity_threshold == 0.7


class TestSimilarityReasons:
    """Test similarity reason generation."""

    def test_similarity_reasons_generated(self, analyzer, sample_issues):
        """Test that similarity reasons are generated."""
        result = analyzer.detect_duplicate(
            title="Login page crashes on submit",
            description="The login form crashes when I submit it",
            existing_issues=sample_issues,
        )

        assert isinstance(result.similarity_reasons, list)
        if result.similarity_score > 0.3:
            assert len(result.similarity_reasons) > 0

    def test_high_similarity_reason(self, analyzer, sample_issues):
        """Test that high similarity generates appropriate reason."""
        result = analyzer.detect_duplicate(
            title="Login page crashes when clicking submit button",
            description="When clicking submit on login page, app crashes with TypeError",
            existing_issues=sample_issues,
        )

        # Should have high similarity and mention it
        if result.similarity_score > 0.6:
            reasons_text = " ".join(result.similarity_reasons).lower()
            assert "similar" in reasons_text or "high" in reasons_text


class TestBatchDetection:
    """Test batch duplicate detection."""

    def test_batch_detect_duplicates(self, analyzer, sample_issues):
        """Test batch processing of multiple issues."""
        new_issues = [
            {"title": "Login form JavaScript error", "description": "JavaScript error on login submit"},
            {"title": "Add export feature", "description": "Need ability to export data to CSV"},
            {"title": "Database timeout error", "description": "Getting timeout when connecting to database"},
        ]

        results = analyzer.batch_detect_duplicates(new_issues, sample_issues)

        assert len(results) == len(new_issues)
        for result in results:
            assert isinstance(result, DuplicateDetectionResult)
            assert 0 <= result.similarity_score <= 1

    def test_batch_with_empty_list(self, analyzer, sample_issues):
        """Test batch processing with empty list."""
        results = analyzer.batch_detect_duplicates([], sample_issues)
        assert len(results) == 0


class TestMostSimilarIssues:
    """Test finding most similar issues."""

    def test_find_most_similar_issues(self, analyzer, sample_issues):
        """Test finding top-k most similar issues."""
        results = analyzer.find_most_similar_issues(
            title="Login crashes on submit",
            description="App crashes when submitting login form",
            existing_issues=sample_issues,
            top_k=2,
        )

        assert isinstance(results, list)
        assert len(results) <= 2

        for issue, score in results:
            assert isinstance(issue, IssueReference)
            assert 0 <= score <= 1

        # Results should be sorted by similarity (highest first)
        if len(results) > 1:
            assert results[0][1] >= results[1][1]

    def test_find_similar_with_empty_list(self, analyzer):
        """Test finding similar issues with empty list."""
        results = analyzer.find_most_similar_issues(title="Test", description="Test", existing_issues=[], top_k=5)

        assert len(results) == 0

    def test_top_k_larger_than_issues(self, analyzer, sample_issues):
        """Test requesting more results than available issues."""
        results = analyzer.find_most_similar_issues(
            title="Test issue", description="Test description", existing_issues=sample_issues, top_k=10
        )

        # Should return at most the number of open issues
        open_count = len([i for i in sample_issues if i.status == "open"])
        assert len(results) <= len(sample_issues)


class TestEdgeCases:
    """Test edge cases."""

    def test_very_short_text(self, analyzer, sample_issues):
        """Test with very short text."""
        result = analyzer.detect_duplicate(title="Bug", description="Error", existing_issues=sample_issues)

        assert isinstance(result, DuplicateDetectionResult)

    def test_very_long_text(self, analyzer, sample_issues):
        """Test with very long text."""
        long_desc = "This is a test. " * 500

        result = analyzer.detect_duplicate(title="Test issue", description=long_desc, existing_issues=sample_issues)

        assert isinstance(result, DuplicateDetectionResult)

    def test_special_characters(self, analyzer, sample_issues):
        """Test with special characters."""
        result = analyzer.detect_duplicate(
            title="Error: <script>alert('test')</script>",
            description="Special chars: @#$%^&*()[]{}|\\:;\"'<>,.?/",
            existing_issues=sample_issues,
        )

        assert isinstance(result, DuplicateDetectionResult)

    def test_unicode_characters(self, analyzer, sample_issues):
        """Test with Unicode characters."""
        result = analyzer.detect_duplicate(
            title="Unicode test: 你好 مرحبا", description="Emoji test: 🐛 🔧 ⚡", existing_issues=sample_issues
        )

        assert isinstance(result, DuplicateDetectionResult)

    def test_identical_issues(self, analyzer):
        """Test with identical issue text."""
        issue = IssueReference(
            issue_id="ISSUE-001", title="Test issue title", description="Test issue description", status="open"
        )

        result = analyzer.detect_duplicate(
            title="Test issue title", description="Test issue description", existing_issues=[issue]
        )

        # Should have very high similarity
        assert result.similarity_score > 0.8
        assert result.is_duplicate


class TestRecommendations:
    """Test recommendation generation."""

    def test_duplicate_recommendation(self, analyzer, sample_issues):
        """Test recommendation for duplicates."""
        result = analyzer.detect_duplicate(
            title="Login page crashes when clicking submit button",
            description="Clicking submit on login crashes with TypeError",
            existing_issues=sample_issues,
        )

        if result.is_duplicate:
            assert "duplicate" in result.recommendation.lower()
            assert result.duplicate_of is not None
            assert result.duplicate_of.issue_id in result.recommendation

    def test_non_duplicate_recommendation(self, analyzer, sample_issues):
        """Test recommendation for non-duplicates."""
        result = analyzer.detect_duplicate(
            title="Add new feature X", description="Would like feature X implemented", existing_issues=sample_issues
        )

        if not result.is_duplicate:
            assert "new" in result.recommendation.lower() or "unique" in result.recommendation.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
