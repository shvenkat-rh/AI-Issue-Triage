"""Test suite for data models."""

import pytest
from pydantic import ValidationError

from utils.models import (
    CodeLocation,
    CodeSolution,
    DuplicateDetectionResult,
    InjectionResult,
    InjectionRisk,
    IssueAnalysis,
    IssueReference,
    IssueType,
    RootCauseAnalysis,
    Severity,
)


class TestEnums:
    """Test enum classes."""

    def test_issue_type_values(self):
        """Test IssueType enum values."""
        assert IssueType.BUG.value == "bug"
        assert IssueType.ENHANCEMENT.value == "enhancement"
        assert IssueType.FEATURE_REQUEST.value == "feature_request"

    def test_severity_values(self):
        """Test Severity enum values."""
        assert Severity.LOW.value == "low"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.HIGH.value == "high"
        assert Severity.CRITICAL.value == "critical"

    def test_injection_risk_values(self):
        """Test InjectionRisk enum values."""
        assert InjectionRisk.SAFE.value == "safe"
        assert InjectionRisk.LOW.value == "low"
        assert InjectionRisk.MEDIUM.value == "medium"
        assert InjectionRisk.HIGH.value == "high"
        assert InjectionRisk.CRITICAL.value == "critical"


class TestCodeLocation:
    """Test CodeLocation model."""

    def test_code_location_creation(self):
        """Test creating a CodeLocation instance."""
        location = CodeLocation(
            file_path="src/main.py", line_number=42, function_name="process_data", class_name="DataProcessor"
        )

        assert location.file_path == "src/main.py"
        assert location.line_number == 42
        assert location.function_name == "process_data"
        assert location.class_name == "DataProcessor"

    def test_code_location_minimal(self):
        """Test creating a CodeLocation with minimal fields."""
        location = CodeLocation(file_path="src/utils.py")

        assert location.file_path == "src/utils.py"
        assert location.line_number is None
        assert location.function_name is None
        assert location.class_name is None

    def test_code_location_validation(self):
        """Test CodeLocation validation."""
        with pytest.raises(ValidationError):
            CodeLocation()  # Missing required file_path


class TestCodeSolution:
    """Test CodeSolution model."""

    def test_code_solution_creation(self):
        """Test creating a CodeSolution instance."""
        location = CodeLocation(file_path="src/app.py", line_number=10)
        solution = CodeSolution(
            description="Fix null pointer exception",
            code_changes="Add null check before accessing property",
            location=location,
            rationale="Prevents crash when object is null",
        )

        assert solution.description == "Fix null pointer exception"
        assert solution.code_changes == "Add null check before accessing property"
        assert solution.location == location
        assert solution.rationale == "Prevents crash when object is null"

    def test_code_solution_validation(self):
        """Test CodeSolution validation."""
        with pytest.raises(ValidationError):
            CodeSolution(description="Test")  # Missing required fields


class TestRootCauseAnalysis:
    """Test RootCauseAnalysis model."""

    def test_root_cause_creation(self):
        """Test creating a RootCauseAnalysis instance."""
        location = CodeLocation(file_path="src/auth.py")
        analysis = RootCauseAnalysis(
            primary_cause="Missing input validation",
            contributing_factors=["No error handling", "Incorrect type conversion"],
            affected_components=["authentication", "user management"],
            related_code_locations=[location],
        )

        assert analysis.primary_cause == "Missing input validation"
        assert len(analysis.contributing_factors) == 2
        assert len(analysis.affected_components) == 2
        assert len(analysis.related_code_locations) == 1


class TestIssueAnalysis:
    """Test IssueAnalysis model."""

    def test_issue_analysis_creation(self):
        """Test creating a complete IssueAnalysis instance."""
        location = CodeLocation(file_path="src/app.py", line_number=50)
        root_cause = RootCauseAnalysis(
            primary_cause="Logic error",
            contributing_factors=["Missing validation"],
            affected_components=["core"],
            related_code_locations=[location],
        )
        solution = CodeSolution(
            description="Add validation", code_changes="if x: return x", location=location, rationale="Prevents invalid state"
        )

        analysis = IssueAnalysis(
            title="App crashes on startup",
            description="The application crashes when started",
            issue_type=IssueType.BUG,
            severity=Severity.HIGH,
            root_cause_analysis=root_cause,
            proposed_solutions=[solution],
            confidence_score=0.85,
            analysis_summary="Critical bug affecting startup",
        )

        assert analysis.title == "App crashes on startup"
        assert analysis.issue_type == IssueType.BUG
        assert analysis.severity == Severity.HIGH
        assert analysis.confidence_score == 0.85
        assert len(analysis.proposed_solutions) == 1

    def test_confidence_score_validation(self):
        """Test that confidence score must be between 0 and 1."""
        location = CodeLocation(file_path="src/app.py")
        root_cause = RootCauseAnalysis(
            primary_cause="Test", contributing_factors=[], affected_components=[], related_code_locations=[location]
        )
        solution = CodeSolution(description="Test", code_changes="test", location=location, rationale="test")

        # Valid confidence score
        analysis = IssueAnalysis(
            title="Test",
            description="Test",
            issue_type=IssueType.BUG,
            severity=Severity.LOW,
            root_cause_analysis=root_cause,
            proposed_solutions=[solution],
            confidence_score=0.5,
            analysis_summary="Test",
        )
        assert analysis.confidence_score == 0.5

        # Invalid confidence score (too high)
        with pytest.raises(ValidationError):
            IssueAnalysis(
                title="Test",
                description="Test",
                issue_type=IssueType.BUG,
                severity=Severity.LOW,
                root_cause_analysis=root_cause,
                proposed_solutions=[solution],
                confidence_score=1.5,
                analysis_summary="Test",
            )

        # Invalid confidence score (negative)
        with pytest.raises(ValidationError):
            IssueAnalysis(
                title="Test",
                description="Test",
                issue_type=IssueType.BUG,
                severity=Severity.LOW,
                root_cause_analysis=root_cause,
                proposed_solutions=[solution],
                confidence_score=-0.1,
                analysis_summary="Test",
            )


class TestIssueReference:
    """Test IssueReference model."""

    def test_issue_reference_creation(self):
        """Test creating an IssueReference instance."""
        issue = IssueReference(
            issue_id="ISSUE-123",
            title="Bug in login",
            description="Login fails with error",
            status="open",
            created_date="2024-01-15",
            url="https://github.com/repo/issues/123",
        )

        assert issue.issue_id == "ISSUE-123"
        assert issue.title == "Bug in login"
        assert issue.status == "open"
        assert issue.created_date == "2024-01-15"
        assert issue.url == "https://github.com/repo/issues/123"

    def test_issue_reference_minimal(self):
        """Test creating an IssueReference with minimal fields."""
        issue = IssueReference(issue_id="ISSUE-456", title="Test issue", description="Test description", status="closed")

        assert issue.issue_id == "ISSUE-456"
        assert issue.created_date is None
        assert issue.url is None


class TestDuplicateDetectionResult:
    """Test DuplicateDetectionResult model."""

    def test_duplicate_result_creation(self):
        """Test creating a DuplicateDetectionResult instance."""
        original_issue = IssueReference(
            issue_id="ISSUE-001", title="Original issue", description="Original description", status="open"
        )

        result = DuplicateDetectionResult(
            is_duplicate=True,
            duplicate_of=original_issue,
            similarity_score=0.85,
            similarity_reasons=["Same error message", "Same component"],
            confidence_score=0.90,
            recommendation="Close as duplicate",
        )

        assert result.is_duplicate is True
        assert result.duplicate_of == original_issue
        assert result.similarity_score == 0.85
        assert len(result.similarity_reasons) == 2
        assert result.confidence_score == 0.90

    def test_non_duplicate_result(self):
        """Test creating a non-duplicate result."""
        result = DuplicateDetectionResult(
            is_duplicate=False,
            duplicate_of=None,
            similarity_score=0.2,
            similarity_reasons=[],
            confidence_score=0.95,
            recommendation="New unique issue",
        )

        assert result.is_duplicate is False
        assert result.duplicate_of is None
        assert result.similarity_score == 0.2

    def test_score_validation(self):
        """Test that scores must be between 0 and 1."""
        # Valid scores
        result = DuplicateDetectionResult(
            is_duplicate=False, similarity_score=0.5, similarity_reasons=[], confidence_score=0.7, recommendation="Test"
        )
        assert result.similarity_score == 0.5
        assert result.confidence_score == 0.7

        # Invalid similarity score
        with pytest.raises(ValidationError):
            DuplicateDetectionResult(
                is_duplicate=False, similarity_score=1.5, similarity_reasons=[], confidence_score=0.5, recommendation="Test"
            )

        # Invalid confidence score
        with pytest.raises(ValidationError):
            DuplicateDetectionResult(
                is_duplicate=False, similarity_score=0.5, similarity_reasons=[], confidence_score=-0.1, recommendation="Test"
            )


class TestInjectionResult:
    """Test InjectionResult dataclass."""

    def test_injection_result_creation(self):
        """Test creating an InjectionResult instance."""
        result = InjectionResult(
            is_injection=True,
            risk_level=InjectionRisk.HIGH,
            confidence_score=0.95,
            detected_patterns=["SQL injection", "XSS"],
            sanitized_text="Safe text",
            details="Detected malicious patterns",
        )

        assert result.is_injection is True
        assert result.risk_level == InjectionRisk.HIGH
        assert result.confidence_score == 0.95
        assert len(result.detected_patterns) == 2
        assert result.sanitized_text == "Safe text"
        assert result.details == "Detected malicious patterns"

    def test_injection_result_minimal(self):
        """Test creating an InjectionResult with minimal fields."""
        result = InjectionResult(
            is_injection=False, risk_level=InjectionRisk.SAFE, confidence_score=0.99, detected_patterns=[]
        )

        assert result.is_injection is False
        assert result.risk_level == InjectionRisk.SAFE
        assert result.sanitized_text is None
        assert result.details is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
