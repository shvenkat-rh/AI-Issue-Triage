"""Tests for PR analyzer functionality."""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from utils.pr_analyzer import PRAnalyzer
from utils.models import PRReview, PRReviewComment


@pytest.fixture
def sample_pr_data():
    """Sample PR data for testing."""
    return {
        "title": "Add new feature",
        "body": "This PR adds a new feature to the codebase",
        "file_changes": [
            {
                "filename": "src/feature.py",
                "status": "added",
                "additions": 50,
                "deletions": 0,
                "patch": """@@ -0,0 +1,50 @@
+def new_feature():
+    pass
"""
            },
            {
                "filename": "tests/test_feature.py",
                "status": "added",
                "additions": 30,
                "deletions": 0,
                "patch": """@@ -0,0 +1,30 @@
+def test_new_feature():
+    assert True
"""
            }
        ]
    }


@pytest.fixture
def sample_gemini_response():
    """Sample Gemini API response."""
    return """## Overall Assessment

This PR adds a new feature with good test coverage.

## Strengths

- Clear code structure
- Good test coverage
- Well-documented functions

## Issues Found

- Missing docstrings in feature.py line 1
- No error handling for edge cases

## Suggestions

- Add type hints to all functions
- Consider adding more edge case tests
- Update the README with usage examples

## File-specific Comments

**`src/feature.py`** (line 1):
The function `new_feature` is missing a docstring explaining its purpose and parameters.

**`tests/test_feature.py`**:
Consider adding more test cases for edge cases and error conditions.
"""


@pytest.fixture
def mock_analyzer():
    """Create a mock PR analyzer without API key."""
    with patch.dict(os.environ, {}, clear=True):
        analyzer = PRAnalyzer(api_key=None)
    return analyzer


@pytest.fixture
def mock_analyzer_with_api():
    """Create a mock PR analyzer with mocked API."""
    with patch('utils.pr_analyzer.genai.Client') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        analyzer = PRAnalyzer(api_key="test_key")
        analyzer.client = mock_instance
        
        yield analyzer


class TestPRAnalyzer:
    """Tests for PRAnalyzer class."""

    def test_init_without_api_key(self, mock_analyzer):
        """Test initialization without API key."""
        assert mock_analyzer.client is None
        assert mock_analyzer.prompt_config is not None

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        with patch('utils.pr_analyzer.genai.Client') as mock_client:
            analyzer = PRAnalyzer(api_key="test_key")
            assert analyzer.client is not None
            assert analyzer.model_name == "gemini-2.0-flash-001"

    def test_init_with_custom_model(self):
        """Test initialization with custom model name."""
        with patch('utils.pr_analyzer.genai.Client'):
            analyzer = PRAnalyzer(api_key="test_key", model_name="gemini-pro")
            assert analyzer.model_name == "gemini-pro"

    def test_load_default_config(self, mock_analyzer):
        """Test loading default configuration."""
        config = mock_analyzer.prompt_config
        assert "prompts" in config
        assert "default" in config["prompts"]
        assert "pr_review" in config["prompts"]["default"]

    def test_get_repo_type_default(self, mock_analyzer):
        """Test repo type detection with no match."""
        repo_type = mock_analyzer._get_repo_type("")
        assert repo_type == "default"

        repo_type = mock_analyzer._get_repo_type("https://github.com/user/repo")
        assert repo_type == "default"

    def test_get_repo_type_with_pattern(self):
        """Test repo type detection with pattern match."""
        with patch('utils.pr_analyzer.genai.Client'):
            analyzer = PRAnalyzer(api_key="test_key")
            # Add custom mapping
            analyzer.prompt_config["repo_mappings"] = {
                "python": [".*python.*", ".*py.*"]
            }
            
            repo_type = analyzer._get_repo_type("https://github.com/user/python-project")
            assert repo_type == "python"

    def test_get_prompt(self, mock_analyzer):
        """Test prompt retrieval."""
        prompt = mock_analyzer._get_prompt("pr_review", "default")
        assert "system_role" in prompt
        assert "review_structure" in prompt

    def test_get_prompt_fallback(self, mock_analyzer):
        """Test prompt retrieval with fallback."""
        prompt = mock_analyzer._get_prompt("nonexistent", "default")
        assert prompt == {}

    def test_build_review_prompt(self, mock_analyzer, sample_pr_data):
        """Test review prompt building."""
        prompt = mock_analyzer._build_review_prompt(
            sample_pr_data["title"],
            sample_pr_data["body"],
            sample_pr_data["file_changes"]
        )
        
        assert sample_pr_data["title"] in prompt
        assert sample_pr_data["body"] in prompt
        assert "src/feature.py" in prompt
        assert "tests/test_feature.py" in prompt

    def test_build_review_prompt_with_large_patch(self, mock_analyzer):
        """Test review prompt with large patch truncation."""
        large_patch = "+" * 10000  # Large patch
        file_changes = [{
            "filename": "large_file.py",
            "status": "modified",
            "additions": 5000,
            "deletions": 0,
            "patch": large_patch
        }]
        
        prompt = mock_analyzer._build_review_prompt(
            "Test PR",
            "Test body",
            file_changes
        )
        
        assert "truncated" in prompt
        assert len(prompt) < len(large_patch)

    def test_extract_section(self, mock_analyzer, sample_gemini_response):
        """Test section extraction from review text."""
        assessment = mock_analyzer._extract_section(
            sample_gemini_response,
            ["Overall Assessment"]
        )
        assert assessment is not None
        assert "new feature" in assessment

    def test_extract_list_section(self, mock_analyzer, sample_gemini_response):
        """Test list section extraction."""
        strengths = mock_analyzer._extract_list_section(
            sample_gemini_response,
            ["Strengths"]
        )
        assert len(strengths) > 0
        assert any("code structure" in s.lower() for s in strengths)

    def test_parse_review(self, mock_analyzer, sample_gemini_response, sample_pr_data):
        """Test review parsing."""
        review = mock_analyzer._parse_review(
            sample_gemini_response,
            sample_pr_data["file_changes"],
            sample_pr_data["title"],
            sample_pr_data["body"]
        )
        
        assert isinstance(review, PRReview)
        assert review.summary == sample_gemini_response
        assert len(review.strengths) > 0
        assert len(review.issues_found) > 0
        assert len(review.suggestions) > 0

    def test_format_review_summary(self, mock_analyzer):
        """Test review formatting."""
        review = PRReview(
            summary="Test review",
            file_comments=[
                PRReviewComment(
                    file_path="test.py",
                    line_number=10,
                    comment="Test comment"
                )
            ],
            overall_assessment="Good PR",
            strengths=["Good tests"],
            issues_found=["Missing docs"],
            suggestions=["Add more tests"],
            confidence_score=0.9
        )
        
        formatted = mock_analyzer.format_review_summary(review)
        
        assert "Overall Assessment" in formatted
        assert "Good PR" in formatted
        assert "Strengths" in formatted
        assert "Issues Found" in formatted
        assert "Suggestions" in formatted
        assert "test.py" in formatted
        assert "line 10" in formatted

    def test_review_pr_without_api_key(self, mock_analyzer, sample_pr_data):
        """Test PR review without API key."""
        review = mock_analyzer.review_pr(
            sample_pr_data["title"],
            sample_pr_data["body"],
            sample_pr_data["file_changes"]
        )
        
        assert isinstance(review, PRReview)
        assert "Error" in review.summary
        assert review.confidence_score == 0.0

    def test_review_pr_with_api(self, mock_analyzer_with_api, sample_pr_data, sample_gemini_response):
        """Test PR review with mocked API."""
        # Mock the API response
        mock_response = Mock()
        mock_response.text = sample_gemini_response
        mock_analyzer_with_api.client.models.generate_content.return_value = mock_response
        
        review = mock_analyzer_with_api.review_pr(
            sample_pr_data["title"],
            sample_pr_data["body"],
            sample_pr_data["file_changes"]
        )
        
        assert isinstance(review, PRReview)
        assert len(review.strengths) > 0
        assert len(review.issues_found) > 0

    def test_review_pr_with_repo_url(self, mock_analyzer_with_api, sample_pr_data, sample_gemini_response):
        """Test PR review with repository URL."""
        mock_response = Mock()
        mock_response.text = sample_gemini_response
        mock_analyzer_with_api.client.models.generate_content.return_value = mock_response
        
        review = mock_analyzer_with_api.review_pr(
            sample_pr_data["title"],
            sample_pr_data["body"],
            sample_pr_data["file_changes"],
            repo_url="https://github.com/user/python-repo"
        )
        
        assert isinstance(review, PRReview)

    def test_review_pr_api_error(self, mock_analyzer_with_api, sample_pr_data):
        """Test PR review with API error."""
        mock_analyzer_with_api.client.models.generate_content.side_effect = Exception("API Error")
        
        review = mock_analyzer_with_api.review_pr(
            sample_pr_data["title"],
            sample_pr_data["body"],
            sample_pr_data["file_changes"]
        )
        
        assert isinstance(review, PRReview)
        assert "Error" in review.summary
        assert review.confidence_score == 0.0

    def test_workflow_analysis(self, mock_analyzer_with_api):
        """Test workflow run analysis."""
        mock_response = Mock()
        mock_response.text = "Workflow analysis result"
        mock_analyzer_with_api.client.models.generate_content.return_value = mock_response
        
        jobs = [
            {
                "name": "test",
                "conclusion": "success",
                "status": "completed",
                "steps": [
                    {"name": "Run tests", "conclusion": "success", "status": "completed"}
                ]
            }
        ]
        
        analysis = mock_analyzer_with_api.analyze_workflow_run(
            workflow_name="CI",
            conclusion="success",
            jobs=jobs,
            failed_jobs=[]
        )
        
        assert "Workflow analysis result" in analysis

    def test_workflow_analysis_without_api(self, mock_analyzer):
        """Test workflow analysis without API key."""
        analysis = mock_analyzer.analyze_workflow_run(
            workflow_name="CI",
            conclusion="success",
            jobs=[],
            failed_jobs=[]
        )
        
        assert "successfully" in analysis.lower()

    def test_workflow_analysis_failure(self, mock_analyzer):
        """Test workflow analysis for failed workflow."""
        analysis = mock_analyzer.analyze_workflow_run(
            workflow_name="CI",
            conclusion="failure",
            jobs=[],
            failed_jobs=["test", "lint"]
        )
        
        assert "failed" in analysis.lower()
        assert "test" in analysis
        assert "lint" in analysis


class TestPRAnalyzerIntegration:
    """Integration tests for PR analyzer (requires actual API key)."""

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"),
        reason="Requires GEMINI_API_KEY or GOOGLE_API_KEY environment variable"
    )
    def test_real_api_call(self, sample_pr_data):
        """Test with real API call (only runs if API key is available)."""
        analyzer = PRAnalyzer()
        
        review = analyzer.review_pr(
            sample_pr_data["title"],
            sample_pr_data["body"],
            sample_pr_data["file_changes"]
        )
        
        assert isinstance(review, PRReview)
        assert review.summary
        assert review.confidence_score > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

