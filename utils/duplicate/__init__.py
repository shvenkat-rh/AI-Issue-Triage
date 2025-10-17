"""
Duplicate Detection Module

Provides both AI-powered and cosine similarity-based duplicate detection.
"""

from utils.duplicate.cosine_duplicate import CosineDuplicateAnalyzer
from utils.duplicate.gemini_duplicate import GeminiDuplicateAnalyzer

__all__ = ["GeminiDuplicateAnalyzer", "CosineDuplicateAnalyzer"]
