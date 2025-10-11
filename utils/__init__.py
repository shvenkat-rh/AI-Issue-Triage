"""
AI Issue Triage - Core Library

A comprehensive AI-powered issue analysis system using Google's Gemini AI.
"""

__version__ = "1.0.0"

from utils.analyzer import GeminiIssueAnalyzer
from utils.models import (
    AnalysisResult,
    CodeLocation,
    DuplicateResult,
    IssueType,
    PromptInjectionResult,
    ProposedSolution,
    RiskLevel,
    RootCauseAnalysis,
    Severity,
)

__all__ = [
    "GeminiIssueAnalyzer",
    "AnalysisResult",
    "CodeLocation",
    "DuplicateResult",
    "IssueType",
    "ProposedSolution",
    "PromptInjectionResult",
    "RiskLevel",
    "RootCauseAnalysis",
    "Severity",
]
