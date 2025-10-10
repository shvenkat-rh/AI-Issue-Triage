"""Test script for the Gemini Issue Analyzer."""

import os

import pytest
from dotenv import load_dotenv

from gemini_analyzer import GeminiIssueAnalyzer

# Load environment variables
load_dotenv()


@pytest.fixture
def analyzer():
    """Fixture to create a GeminiIssueAnalyzer instance."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not found in environment variables")
    return GeminiIssueAnalyzer()


@pytest.fixture
def sample_test_cases():
    """Fixture providing sample test cases for issue analysis."""
    return [
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
            """,
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
            """,
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
            """,
        },
    ]


class TestGeminiAnalyzer:
    """Test suite for GeminiIssueAnalyzer."""

    def test_analyzer_initialization(self):
        """Test that the analyzer initializes successfully."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            pytest.skip("GEMINI_API_KEY not found")

        analyzer = GeminiIssueAnalyzer()
        assert analyzer is not None

    def test_analyze_bug_issue(self, analyzer, sample_test_cases):
        """Test analyzing a bug report issue."""
        test_case = sample_test_cases[0]  # Bug report

        analysis = analyzer.analyze_issue(test_case["title"], test_case["description"])

        assert analysis is not None
        assert analysis.issue_type is not None
        assert analysis.severity is not None
        assert 0 <= analysis.confidence_score <= 1
        assert analysis.root_cause_analysis is not None
        assert analysis.root_cause_analysis.primary_cause

    def test_analyze_feature_request(self, analyzer, sample_test_cases):
        """Test analyzing a feature request issue."""
        test_case = sample_test_cases[1]  # Feature request

        analysis = analyzer.analyze_issue(test_case["title"], test_case["description"])

        assert analysis is not None
        assert analysis.issue_type is not None
        assert analysis.confidence_score > 0
        assert analysis.proposed_solutions is not None

    def test_analyze_performance_issue(self, analyzer, sample_test_cases):
        """Test analyzing a performance/memory issue."""
        test_case = sample_test_cases[2]  # Memory leak

        analysis = analyzer.analyze_issue(test_case["title"], test_case["description"])

        assert analysis is not None
        assert analysis.severity is not None
        assert analysis.proposed_solutions
        assert len(analysis.proposed_solutions) > 0

    def test_confidence_score_range(self, analyzer, sample_test_cases):
        """Test that confidence scores are within valid range."""
        for test_case in sample_test_cases:
            analysis = analyzer.analyze_issue(test_case["title"], test_case["description"])

            assert 0.0 <= analysis.confidence_score <= 1.0, f"Confidence score {analysis.confidence_score} out of range"

    def test_empty_issue(self, analyzer):
        """Test handling of empty issue."""
        with pytest.raises(Exception):
            analyzer.analyze_issue("", "")

    def test_minimal_issue(self, analyzer):
        """Test handling of minimal issue description."""
        analysis = analyzer.analyze_issue("App crashes", "The app crashes sometimes")

        assert analysis is not None
        assert analysis.issue_type is not None


def test_analyzer_without_api_key():
    """Test that analyzer raises error without API key."""
    original_key = os.getenv("GEMINI_API_KEY")

    # Temporarily remove API key
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]

    try:
        with pytest.raises(ValueError):
            GeminiIssueAnalyzer()
    finally:
        # Restore API key
        if original_key:
            os.environ["GEMINI_API_KEY"] = original_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
