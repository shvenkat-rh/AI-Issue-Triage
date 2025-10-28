"""Tests for the batch Gemini duplicate issue analyzer."""

import json
import os
from unittest.mock import Mock, patch

import pytest

from utils.duplicate.batch_gemini_duplicate import GeminiBatchDuplicateAnalyzer
from utils.models import DuplicateDetectionResult, IssueReference


@pytest.fixture
def sample_new_issues():
    """Sample new issues to check."""
    return [
        {"title": "Login bug", "description": "Users can't login"},
        {"title": "Timeout error", "description": "Database connection times out"},
    ]


@pytest.fixture
def sample_existing_issues():
    """Sample existing issues."""
    return [
        IssueReference(
            issue_id="ISSUE-001",
            title="Login page crash",
            description="Application crashes on login",
            status="open",
            created_date="2024-01-01",
            url="https://github.com/test/repo/issues/1",
        ),
        IssueReference(
            issue_id="ISSUE-002",
            title="Database timeout",
            description="DB connection times out after 30 seconds",
            status="open",
            created_date="2024-01-02",
            url="https://github.com/test/repo/issues/2",
        ),
    ]


@pytest.fixture
def mock_batch_result():
    """Mock batch result for duplicate detection."""
    result = Mock()
    result.task_id = "duplicate_check_0"
    result.response = Mock()
    result.response.candidates = [Mock()]
    result.response.candidates[0].content = Mock()
    result.response.candidates[0].content.parts = [Mock()]
    result.response.candidates[0].content.parts[0].text = json.dumps(
        {
            "is_duplicate": True,
            "duplicate_issue_id": "ISSUE-001",
            "similarity_score": 0.85,
            "similarity_reasons": ["Similar error messages", "Same affected component"],
            "confidence_score": 0.90,
            "recommendation": "This is a duplicate of ISSUE-001",
        }
    )
    return result


class TestGeminiBatchDuplicateAnalyzer:
    """Test suite for GeminiBatchDuplicateAnalyzer."""

    def test_initialization_with_api_key(self):
        """Test initialization with API key."""
        analyzer = GeminiBatchDuplicateAnalyzer(api_key="test-key")

        assert analyzer.api_key == "test-key"
        assert analyzer.model_name == "gemini-2.0-flash-001"

    def test_initialization_without_api_key(self):
        """Test initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Gemini API key not found"):
                GeminiBatchDuplicateAnalyzer()

    def test_create_batch_request(self, sample_new_issues, sample_existing_issues):
        """Test batch request creation."""
        analyzer = GeminiBatchDuplicateAnalyzer(api_key="test-key")
        batch_request = analyzer._create_batch_request(sample_new_issues, sample_existing_issues)

        assert len(batch_request) == 2
        assert batch_request[0]["task_id"] == "duplicate_check_0"
        assert batch_request[1]["task_id"] == "duplicate_check_1"
        assert "request" in batch_request[0]

    def test_batch_detect_duplicates_no_open_issues(self, sample_new_issues):
        """Test batch duplicate detection with no open issues."""
        analyzer = GeminiBatchDuplicateAnalyzer(api_key="test-key")

        closed_issues = [
            IssueReference(
                issue_id="ISSUE-001",
                title="Old issue",
                description="Closed issue",
                status="closed",
            )
        ]

        results = analyzer.batch_detect_duplicates(sample_new_issues, closed_issues)

        assert len(results) == 2
        assert all(not r.is_duplicate for r in results)
        assert all(r.confidence_score == 1.0 for r in results)

    def test_batch_detect_duplicates_no_new_issues(self, sample_existing_issues):
        """Test batch duplicate detection with no new issues."""
        analyzer = GeminiBatchDuplicateAnalyzer(api_key="test-key")

        results = analyzer.batch_detect_duplicates([], sample_existing_issues)

        assert len(results) == 0

    @patch("utils.duplicate.batch_gemini_duplicate.time.sleep")
    def test_poll_batch_job(self, mock_sleep):
        """Test polling batch job."""
        analyzer = GeminiBatchDuplicateAnalyzer(api_key="test-key")

        # Mock client with state progression
        mock_client = Mock()
        job_states = [
            Mock(state="PROCESSING", name="batch-123"),
            Mock(state="SUCCEEDED", name="batch-123"),
        ]
        mock_client.batches.get.side_effect = job_states

        analyzer.client = mock_client

        result = analyzer._poll_batch_job("batch-123", poll_interval=1)

        assert result.state == "SUCCEEDED"
        assert mock_sleep.call_count == 1

    def test_parse_batch_results(self, sample_new_issues, sample_existing_issues, mock_batch_result):
        """Test parsing batch results."""
        analyzer = GeminiBatchDuplicateAnalyzer(api_key="test-key")

        # Mock completed job
        completed_job = Mock()
        completed_job.name = "batch-123"

        # Create second result
        mock_result_2 = Mock()
        mock_result_2.task_id = "duplicate_check_1"
        mock_result_2.response = Mock()
        mock_result_2.response.candidates = [Mock()]
        mock_result_2.response.candidates[0].content = Mock()
        mock_result_2.response.candidates[0].content.parts = [Mock()]
        mock_result_2.response.candidates[0].content.parts[0].text = json.dumps(
            {
                "is_duplicate": False,
                "similarity_score": 0.3,
                "similarity_reasons": [],
                "confidence_score": 0.8,
                "recommendation": "This is a unique issue",
            }
        )

        # Mock client that returns results
        mock_client = Mock()
        mock_client.batches.list_results.return_value = [mock_batch_result, mock_result_2]

        analyzer.client = mock_client

        results = analyzer._parse_batch_results(completed_job, sample_new_issues, sample_existing_issues)

        assert len(results) == 2
        assert all(isinstance(r, DuplicateDetectionResult) for r in results)
        assert results[0].is_duplicate is True
        assert results[0].duplicate_of.issue_id == "ISSUE-001"
        assert results[1].is_duplicate is False

    def test_parse_gemini_response_with_json(self):
        """Test parsing Gemini response with valid JSON."""
        analyzer = GeminiBatchDuplicateAnalyzer(api_key="test-key")

        response_text = json.dumps(
            {
                "is_duplicate": True,
                "duplicate_issue_id": "ISSUE-123",
                "similarity_score": 0.9,
                "similarity_reasons": ["Same error", "Same component"],
                "confidence_score": 0.95,
                "recommendation": "Mark as duplicate",
            }
        )

        result = analyzer._parse_gemini_response(response_text)

        assert result["is_duplicate"] is True
        assert result["duplicate_issue_id"] == "ISSUE-123"
        assert result["similarity_score"] == 0.9
        assert len(result["similarity_reasons"]) == 2

    def test_parse_gemini_response_without_json(self):
        """Test parsing Gemini response without JSON."""
        analyzer = GeminiBatchDuplicateAnalyzer(api_key="test-key")

        response_text = "This appears to be a duplicate issue with similar symptoms"

        result = analyzer._parse_gemini_response(response_text)

        assert result["is_duplicate"] is True
        assert result["confidence_score"] == 0.4  # Low confidence for fallback

    def test_extract_from_text(self):
        """Test extraction from plain text."""
        analyzer = GeminiBatchDuplicateAnalyzer(api_key="test-key")

        text_duplicate = "This is a duplicate issue that is the same issue already reported"
        result = analyzer._extract_from_text(text_duplicate)

        assert result["is_duplicate"] is True
        assert result["similarity_score"] > 0

        text_unique = "This is a completely new and unique issue"
        result = analyzer._extract_from_text(text_unique)

        assert result["is_duplicate"] is False

    def test_create_fallback_result(self):
        """Test fallback result creation."""
        analyzer = GeminiBatchDuplicateAnalyzer(api_key="test-key")

        fallback = analyzer._create_fallback_result("API Error")

        assert isinstance(fallback, DuplicateDetectionResult)
        assert fallback.is_duplicate is False
        assert fallback.confidence_score == 0.0
        assert "API Error" in fallback.recommendation


@pytest.mark.integration
class TestGeminiBatchDuplicateAnalyzerIntegration:
    """Integration tests requiring actual API key."""

    @pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
    def test_batch_detect_duplicates_real_api(self, sample_existing_issues):
        """Test batch duplicate detection with real API."""
        analyzer = GeminiBatchDuplicateAnalyzer()

        new_issues = [{"title": "Login crash", "description": "App crashes when logging in"}]

        # This will make a real API call
        results = analyzer.batch_detect_duplicates(new_issues, sample_existing_issues, poll_interval=5)

        assert len(results) == 1
        assert isinstance(results[0], DuplicateDetectionResult)
