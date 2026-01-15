"""Data models for the Gemini Issue Analyzer."""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class IssueType(str, Enum):
    """Enum for issue types."""

    BUG = "bug"
    ENHANCEMENT = "enhancement"
    FEATURE_REQUEST = "feature_request"


class Severity(str, Enum):
    """Enum for issue severity."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CodeLocation(BaseModel):
    """Model for code location references."""

    file_path: str = Field(description="Path to the file")
    line_number: Optional[int] = Field(None, description="Line number if applicable")
    function_name: Optional[str] = Field(None, description="Function or method name")
    class_name: Optional[str] = Field(None, description="Class name if applicable")


class CodeSolution(BaseModel):
    """Model for proposed code solutions."""

    description: str = Field(description="Description of the solution")
    code_changes: str = Field(description="Proposed code changes")
    location: CodeLocation = Field(description="Where to apply the changes")
    rationale: str = Field(description="Why this solution addresses the issue")


class RootCauseAnalysis(BaseModel):
    """Model for root cause analysis results."""

    primary_cause: str = Field(description="Primary cause of the issue")
    contributing_factors: List[str] = Field(description="Contributing factors")
    affected_components: List[str] = Field(description="Components affected by this issue")
    related_code_locations: List[CodeLocation] = Field(description="Related code locations")


class IssueAnalysis(BaseModel):
    """Complete analysis of an issue."""

    title: str = Field(description="Issue title")
    description: str = Field(description="Issue description")
    issue_type: IssueType = Field(description="Type of issue")
    severity: Severity = Field(description="Issue severity")
    root_cause_analysis: RootCauseAnalysis = Field(description="Root cause analysis")
    proposed_solutions: List[CodeSolution] = Field(description="Proposed solutions")
    confidence_score: float = Field(description="Confidence in the analysis (0-1)", ge=0, le=1)
    analysis_summary: str = Field(description="Summary of the analysis")


class IssueReference(BaseModel):
    """Reference to an existing issue."""

    issue_id: str = Field(description="Unique identifier for the issue")
    title: str = Field(description="Issue title")
    description: str = Field(description="Issue description")
    status: str = Field(description="Current status of the issue (e.g., 'open', 'closed', 'in_progress')")
    created_date: Optional[str] = Field(None, description="When the issue was created")
    url: Optional[str] = Field(None, description="URL to the issue if available")


class DuplicateDetectionResult(BaseModel):
    """Result of duplicate issue detection."""

    is_duplicate: bool = Field(description="Whether the issue is a duplicate")
    duplicate_of: Optional[IssueReference] = Field(None, description="Reference to the original issue if duplicate")
    similarity_score: float = Field(description="Similarity score (0-1)", ge=0, le=1)
    similarity_reasons: List[str] = Field(description="Reasons why issues are considered similar")
    confidence_score: float = Field(description="Confidence in the duplicate detection (0-1)", ge=0, le=1)
    recommendation: str = Field(description="Recommendation for handling the duplicate")


class InjectionRisk(Enum):
    """Risk levels for prompt injection detection."""

    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class InjectionResult:
    """Result of prompt injection detection."""

    is_injection: bool
    risk_level: InjectionRisk
    confidence_score: float
    detected_patterns: List[str]
    sanitized_text: Optional[str] = None
    details: Optional[str] = None


class PRReviewComment(BaseModel):
    """Model for PR review file-specific comments."""

    file_path: str = Field(description="Path to the file")
    line_number: Optional[int] = Field(None, description="Line number if applicable")
    comment: str = Field(description="Review comment for this location")


class PRFileChange(BaseModel):
    """Model for PR file changes."""

    filename: str = Field(description="Name/path of the changed file")
    status: str = Field(description="Change status (added, modified, removed, renamed)")
    additions: int = Field(description="Number of lines added")
    deletions: int = Field(description="Number of lines deleted")
    patch: Optional[str] = Field(None, description="Git diff patch")


class PRReview(BaseModel):
    """Complete PR review analysis.

    All fields are mandatory and will always be present in the output.
    """

    summary: str = Field(description="Full review summary text", min_length=1)
    file_comments: List[PRReviewComment] = Field(default_factory=list, description="File-specific review comments")
    overall_assessment: str = Field(description="Overall assessment of the PR", min_length=1)
    strengths: List[str] = Field(default_factory=list, description="Strengths identified in the PR")
    issues_found: List[str] = Field(default_factory=list, description="Issues found in the PR")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")
    confidence_score: float = Field(description="Confidence in the review (0-1)", ge=0, le=1)
