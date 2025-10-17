"""
AI Issue Triage - Core Library

A comprehensive AI-powered issue analysis system using Google's Gemini AI.
"""

__version__ = "1.0.0"

from utils.analyzer import GeminiIssueAnalyzer
from utils.models import (
    CodeLocation,
    CodeSolution,
    DuplicateDetectionResult,
    InjectionResult,
    InjectionRisk,
    IssueAnalysis,
    IssueType,
    RootCauseAnalysis,
    Severity,
)

__all__ = [
    "GeminiIssueAnalyzer",
    "IssueAnalysis",
    "CodeLocation",
    "CodeSolution",
    "DuplicateDetectionResult",
    "IssueType",
    "InjectionResult",
    "InjectionRisk",
    "RootCauseAnalysis",
    "Severity",
]
