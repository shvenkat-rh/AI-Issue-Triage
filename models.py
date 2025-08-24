"""Data models for the Gemini Issue Analyzer."""

from enum import Enum
from typing import Optional, List
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
