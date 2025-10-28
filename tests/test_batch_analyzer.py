"""Tests for the batch Gemini issue analyzer."""

import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from utils.batch_analyzer import GeminiBatchIssueAnalyzer
from utils.models import IssueAnalysis, IssueType, Severity


@pytest.fixture
def sample_issues():
    """Sample issues for batch processing."""
    return [
        {"title": "Login bug", "description": "Users can't login"},
        {"title": "Database timeout", "description": "Connection times out"},
    ]


@pytest.fixture
def mock_batch_job():
    """Mock batch job object."""
    job = Mock()
    job.name = "batch-123"
    job.state = "SUCCEEDED"
    return job


@pytest.fixture
def mock_batch_result():
    """Mock batch result object."""
    result = Mock()
    result.task_id = "issue_0"
    result.response = Mock()
    result.response.candidates = [Mock()]
    result.response.candidates[0].content = Mock()
    result.response.candidates[0].content.parts = [Mock()]
    result.response.candidates[0].content.parts[0].text = json.dumps(
        {
            "issue_type": "bug",
            "severity": "high",
            "root_cause_analysis": {
                "primary_cause": "Authentication module error",
                "contributing_factors": ["Missing validation"],
                "affected_components": ["auth"],
                "related_code_locations": [],
            },
            "proposed_solutions": [
                {
                    "description": "Add validation",
                    "code_changes": "Add input validation",
                    "location": {"file_path": "auth.py", "line_number": 10, "function_name": "login", "class_name": None},
                    "rationale": "Prevents invalid input",
                }
            ],
            "confidence_score": 0.85,
            "analysis_summary": "Authentication error in login module",
        }
    )
    return result


class TestGeminiBatchIssueAnalyzer:
    """Test suite for GeminiBatchIssueAnalyzer."""

    def test_initialization_with_api_key(self, tmp_path):
        """Test initialization with API key."""
        # Create a temporary source file
        source_file = tmp_path / "source.txt"
        source_file.write_text("Sample codebase content")

        analyzer = GeminiBatchIssueAnalyzer(api_key="test-key", source_path=str(source_file))

        assert analyzer.api_key == "test-key"
        assert analyzer.model_name == "gemini-2.0-flash-001"
        assert analyzer.codebase_content == "Sample codebase content"

    def test_initialization_without_api_key(self):
        """Test initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Gemini API key not found"):
                GeminiBatchIssueAnalyzer()

    def test_create_batch_request(self, sample_issues, tmp_path):
        """Test batch request creation."""
        source_file = tmp_path / "source.txt"
        source_file.write_text("Sample codebase")

        analyzer = GeminiBatchIssueAnalyzer(api_key="test-key", source_path=str(source_file))
        batch_request = analyzer._create_batch_request(sample_issues)

        assert len(batch_request) == 2
        assert batch_request[0]["task_id"] == "issue_0"
        assert batch_request[1]["task_id"] == "issue_1"
        assert "request" in batch_request[0]

    @patch("utils.batch_analyzer.time.sleep")
    def test_poll_batch_job_success(self, mock_sleep, tmp_path):
        """Test polling batch job until completion."""
        source_file = tmp_path / "source.txt"
        source_file.write_text("Sample codebase")

        analyzer = GeminiBatchIssueAnalyzer(api_key="test-key", source_path=str(source_file))

        # Mock client with state progression
        mock_client = Mock()
        job_states = [
            Mock(state="PROCESSING", name="batch-123"),
            Mock(state="PROCESSING", name="batch-123"),
            Mock(state="SUCCEEDED", name="batch-123"),
        ]
        mock_client.batches.get.side_effect = job_states

        analyzer.client = mock_client

        result = analyzer._poll_batch_job("batch-123", poll_interval=1)

        assert result.state == "SUCCEEDED"
        assert mock_sleep.call_count == 2  # Called twice before success

    def test_parse_batch_results(self, sample_issues, mock_batch_result, tmp_path):
        """Test parsing batch results."""
        source_file = tmp_path / "source.txt"
        source_file.write_text("Sample codebase")

        analyzer = GeminiBatchIssueAnalyzer(api_key="test-key", source_path=str(source_file))

        # Mock completed job
        completed_job = Mock()
        completed_job.name = "batch-123"

        # Mock client that returns results
        mock_client = Mock()
        mock_result_2 = Mock()
        mock_result_2.task_id = "issue_1"
        mock_result_2.response = mock_batch_result.response

        mock_client.batches.list_results.return_value = [mock_batch_result, mock_result_2]

        analyzer.client = mock_client

        analyses = analyzer._parse_batch_results(completed_job, sample_issues)

        assert len(analyses) == 2
        assert all(isinstance(a, IssueAnalysis) for a in analyses)
        assert analyses[0].issue_type == IssueType.BUG
        assert analyses[0].severity == Severity.HIGH

    def test_is_low_quality_response(self, tmp_path):
        """Test low quality response detection."""
        source_file = tmp_path / "source.txt"
        source_file.write_text("Sample codebase")

        analyzer = GeminiBatchIssueAnalyzer(api_key="test-key", source_path=str(source_file))

        # Create a low quality analysis
        low_quality = IssueAnalysis(
            title="Test",
            description="Test",
            issue_type=IssueType.BUG,
            severity=Severity.MEDIUM,
            root_cause_analysis={
                "primary_cause": "requires further investigation",
                "contributing_factors": [],
                "affected_components": [],
                "related_code_locations": [],
            },
            proposed_solutions=[],
            confidence_score=0.5,
            analysis_summary="Short",
        )

        assert analyzer._is_low_quality_response(low_quality) is True

    def test_parse_gemini_response_with_json(self, tmp_path):
        """Test parsing Gemini response with valid JSON."""
        source_file = tmp_path / "source.txt"
        source_file.write_text("Sample codebase")

        analyzer = GeminiBatchIssueAnalyzer(api_key="test-key", source_path=str(source_file))

        response_text = json.dumps(
            {
                "issue_type": "bug",
                "severity": "high",
                "root_cause_analysis": {
                    "primary_cause": "Test cause",
                    "contributing_factors": ["factor1"],
                    "affected_components": ["comp1"],
                    "related_code_locations": [],
                },
                "proposed_solutions": [
                    {
                        "description": "Fix it",
                        "code_changes": "Change code",
                        "location": {"file_path": "test.py"},
                        "rationale": "Because",
                    }
                ],
                "confidence_score": 0.9,
                "analysis_summary": "Test summary",
            }
        )

        result = analyzer._parse_gemini_response(response_text)

        assert result["issue_type"] == "bug"
        assert result["severity"] == "high"
        assert result["confidence_score"] == 0.9

    def test_create_fallback_analysis(self, tmp_path):
        """Test fallback analysis creation."""
        source_file = tmp_path / "source.txt"
        source_file.write_text("Sample codebase")

        analyzer = GeminiBatchIssueAnalyzer(api_key="test-key", source_path=str(source_file))

        fallback = analyzer._create_fallback_analysis("Test Title", "Test Description", "API Error")

        assert isinstance(fallback, IssueAnalysis)
        assert fallback.title == "Test Title"
        assert fallback.confidence_score == 0.0
        assert "API Error" in fallback.root_cause_analysis.primary_cause

    def test_extract_from_text(self, tmp_path):
        """Test extraction from plain text."""
        source_file = tmp_path / "source.txt"
        source_file.write_text("Sample codebase")

        analyzer = GeminiBatchIssueAnalyzer(api_key="test-key", source_path=str(source_file))

        text = "This is a critical bug that needs immediate attention"
        result = analyzer._extract_from_text(text)

        assert result["issue_type"] == "bug"
        assert result["severity"] == "critical"
        assert result["confidence_score"] == 0.5


@pytest.mark.integration
class TestGeminiBatchIssueAnalyzerIntegration:
    """Integration tests requiring actual API key."""

    @pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
    def test_batch_analyze_issues_real_api(self, tmp_path):
        """Test batch analysis with real API (requires API key)."""
        source_file = tmp_path / "source.txt"
        source_file.write_text("Sample Python codebase with authentication module")

        analyzer = GeminiBatchIssueAnalyzer(source_path=str(source_file))

        issues = [{"title": "Login error", "description": "Users cannot login to the system"}]

        # This will make a real API call
        analyses = analyzer.batch_analyze_issues(issues, max_retries=0, poll_interval=5)

        assert len(analyses) == 1
        assert isinstance(analyses[0], IssueAnalysis)
        assert analyses[0].title == "Login error"
