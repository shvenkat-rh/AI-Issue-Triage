"""Tests for the batch cosine similarity duplicate issue analyzer."""

import pytest

from utils.duplicate.batch_cosine_duplicate import CosineBatchDuplicateAnalyzer
from utils.models import DuplicateDetectionResult, IssueReference


@pytest.fixture
def sample_new_issues():
    """Sample new issues to check."""
    return [
        {"title": "Login bug", "description": "Users can't login to the system"},
        {"title": "Timeout error", "description": "Database connection times out"},
        {"title": "New feature", "description": "Add dark mode to the application"},
    ]


@pytest.fixture
def sample_existing_issues():
    """Sample existing issues."""
    return [
        IssueReference(
            issue_id="ISSUE-001",
            title="Login page crash",
            description="Application crashes when users try to login",
            status="open",
            created_date="2024-01-01",
            url="https://github.com/test/repo/issues/1",
        ),
        IssueReference(
            issue_id="ISSUE-002",
            title="Database timeout",
            description="DB connection times out after 30 seconds during peak hours",
            status="open",
            created_date="2024-01-02",
            url="https://github.com/test/repo/issues/2",
        ),
        IssueReference(
            issue_id="ISSUE-003",
            title="UI improvement",
            description="Improve the user interface design",
            status="open",
            created_date="2024-01-03",
            url="https://github.com/test/repo/issues/3",
        ),
    ]


class TestCosineBatchDuplicateAnalyzer:
    """Test suite for CosineBatchDuplicateAnalyzer."""

    def test_initialization(self):
        """Test initialization with custom thresholds."""
        analyzer = CosineBatchDuplicateAnalyzer(similarity_threshold=0.8, confidence_threshold=0.7)

        assert analyzer.similarity_threshold == 0.8
        assert analyzer.confidence_threshold == 0.7

    def test_initialization_defaults(self):
        """Test initialization with default thresholds."""
        analyzer = CosineBatchDuplicateAnalyzer()

        assert analyzer.similarity_threshold == 0.6
        assert analyzer.confidence_threshold == 0.6

    def test_preprocess_text(self):
        """Test text preprocessing."""
        analyzer = CosineBatchDuplicateAnalyzer()

        text = "This is a TEST with special@characters and   spaces"
        processed = analyzer._preprocess_text(text)

        assert processed == "this is a test with special characters and spaces"
        assert "@" not in processed
        assert "   " not in processed

    def test_combine_issue_text(self, sample_existing_issues):
        """Test combining issue text with title weighting."""
        analyzer = CosineBatchDuplicateAnalyzer()

        combined = analyzer._combine_issue_text(sample_existing_issues[0])

        # Title should appear twice (weighted)
        assert "login page crash" in combined
        assert combined.count("login") >= 2  # At least twice from weighted title

    def test_calculate_text_similarity(self):
        """Test text similarity calculation."""
        analyzer = CosineBatchDuplicateAnalyzer()

        # Similar texts
        text1 = "login bug authentication error"
        text2 = "login error authentication problem"
        similarity = analyzer._calculate_text_similarity(text1, text2)

        assert 0.5 < similarity < 1.0  # Should be quite similar

        # Different texts
        text3 = "database timeout connection"
        similarity2 = analyzer._calculate_text_similarity(text1, text3)

        assert similarity2 < similarity  # Should be less similar

    def test_batch_detect_duplicates_basic(self, sample_new_issues, sample_existing_issues):
        """Test basic batch duplicate detection."""
        analyzer = CosineBatchDuplicateAnalyzer(similarity_threshold=0.6)

        results = analyzer.batch_detect_duplicates(sample_new_issues, sample_existing_issues)

        assert len(results) == 3
        assert all(isinstance(r, DuplicateDetectionResult) for r in results)

        # First issue should be similar to ISSUE-001 (both about login)
        assert results[0].similarity_score > 0.0  # Has some similarity

        # Second issue should be similar to ISSUE-002 (both about timeout)
        assert results[1].similarity_score > 0.0  # Has some similarity

    def test_batch_detect_duplicates_no_open_issues(self, sample_new_issues):
        """Test batch detection with no open issues."""
        analyzer = CosineBatchDuplicateAnalyzer()

        closed_issues = [IssueReference(issue_id="ISSUE-001", title="Old issue", description="Closed issue", status="closed")]

        results = analyzer.batch_detect_duplicates(sample_new_issues, closed_issues)

        assert len(results) == 3
        assert all(not r.is_duplicate for r in results)
        assert all(r.confidence_score == 1.0 for r in results)

    def test_batch_detect_duplicates_empty_new_issues(self, sample_existing_issues):
        """Test batch detection with empty new issues."""
        analyzer = CosineBatchDuplicateAnalyzer()

        results = analyzer.batch_detect_duplicates([], sample_existing_issues)

        assert len(results) == 0

    def test_batch_detect_duplicates_high_similarity(self):
        """Test detection with very similar issues."""
        analyzer = CosineBatchDuplicateAnalyzer(similarity_threshold=0.6)

        existing = [
            IssueReference(
                issue_id="ISSUE-001",
                title="Login authentication fails completely",
                description="Users cannot authenticate when trying to login to the system at all",
                status="open",
            )
        ]

        new_issues = [
            {
                "title": "Login authentication failure completely broken",
                "description": "Cannot authenticate during login to the system at all",
            }
        ]

        results = analyzer.batch_detect_duplicates(new_issues, existing)

        assert len(results) == 1
        # These should be similar enough to detect - check for similarity reasons
        assert len(results[0].similarity_reasons) > 0
        # Should have common keywords or similar titles/descriptions
        reasons_text = " ".join(results[0].similarity_reasons).lower()
        assert "similar" in reasons_text or "common" in reasons_text

    def test_calculate_similarity_reasons(self, sample_existing_issues):
        """Test similarity reasons calculation."""
        analyzer = CosineBatchDuplicateAnalyzer()

        reasons = analyzer._calculate_similarity_reasons("Login bug", "Users can't login", sample_existing_issues[0], 0.8)

        assert len(reasons) > 0
        assert any("similar" in reason.lower() for reason in reasons)

    def test_find_most_similar_issues_batch(self, sample_new_issues, sample_existing_issues):
        """Test finding most similar issues for batch."""
        analyzer = CosineBatchDuplicateAnalyzer()

        results = analyzer.find_most_similar_issues_batch(sample_new_issues, sample_existing_issues, top_k=2)

        assert len(results) == 3  # One result per new issue
        assert all(len(r) <= 2 for r in results)  # At most 2 similar issues each
        assert all(isinstance(r, list) for r in results)

        # Each result should be a list of (IssueReference, similarity_score) tuples
        for issue_results in results:
            for issue, score in issue_results:
                assert isinstance(issue, IssueReference)
                assert 0 <= score <= 1

    def test_find_most_similar_issues_batch_empty(self):
        """Test finding similar issues with empty inputs."""
        analyzer = CosineBatchDuplicateAnalyzer()

        results = analyzer.find_most_similar_issues_batch([], [], top_k=5)

        assert results == []

    def test_batch_performance_with_large_dataset(self):
        """Test batch processing performance with larger dataset."""
        analyzer = CosineBatchDuplicateAnalyzer()

        # Create 50 existing issues
        existing = [
            IssueReference(
                issue_id=f"ISSUE-{i:03d}",
                title=f"Issue {i}",
                description=f"Description for issue number {i}",
                status="open",
            )
            for i in range(50)
        ]

        # Create 10 new issues
        new_issues = [{"title": f"New issue {i}", "description": f"New description {i}"} for i in range(10)]

        results = analyzer.batch_detect_duplicates(new_issues, existing)

        assert len(results) == 10
        assert all(isinstance(r, DuplicateDetectionResult) for r in results)

    def test_similarity_threshold_effect(self, sample_new_issues, sample_existing_issues):
        """Test that similarity threshold affects duplicate detection."""
        # Low threshold - more duplicates
        analyzer_low = CosineBatchDuplicateAnalyzer(similarity_threshold=0.3)
        results_low = analyzer_low.batch_detect_duplicates(sample_new_issues, sample_existing_issues)

        # High threshold - fewer duplicates
        analyzer_high = CosineBatchDuplicateAnalyzer(similarity_threshold=0.9)
        results_high = analyzer_high.batch_detect_duplicates(sample_new_issues, sample_existing_issues)

        duplicates_low = sum(1 for r in results_low if r.is_duplicate)
        duplicates_high = sum(1 for r in results_high if r.is_duplicate)

        # Lower threshold should find more or equal duplicates
        assert duplicates_low >= duplicates_high

    def test_error_handling_in_batch_detection(self):
        """Test error handling in batch detection."""
        analyzer = CosineBatchDuplicateAnalyzer()

        # Invalid issue format (missing description)
        invalid_issues = [{"title": "Test"}]
        existing = [IssueReference(issue_id="ISSUE-001", title="Test", description="Test", status="open")]

        # Should handle gracefully and return non-duplicate results
        results = analyzer.batch_detect_duplicates(invalid_issues, existing)

        assert len(results) == 1
        assert isinstance(results[0], DuplicateDetectionResult)

    def test_recommendation_generation(self, sample_existing_issues):
        """Test recommendation generation based on similarity."""
        analyzer = CosineBatchDuplicateAnalyzer(similarity_threshold=0.7)

        new_issues = [{"title": "Login crash similar", "description": "App crashes on login"}]

        results = analyzer.batch_detect_duplicates(new_issues, sample_existing_issues)

        assert len(results) == 1
        recommendation = results[0].recommendation

        assert isinstance(recommendation, str)
        assert len(recommendation) > 0

        if results[0].is_duplicate:
            assert "duplicate" in recommendation.lower()
        elif results[0].similarity_score > 0.5:
            assert "similar" in recommendation.lower() or "review" in recommendation.lower()
        else:
            assert "unique" in recommendation.lower() or "new" in recommendation.lower()
