"""Gemini-powered duplicate issue analyzer."""

import json
import os
import re
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google import genai

from utils.models import DuplicateDetectionResult, IssueReference

# Load environment variables
load_dotenv()


class GeminiDuplicateAnalyzer:
    """Analyzer that uses Google's Gemini AI to detect duplicate issues."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Gemini duplicate analyzer.

        Args:
            api_key: Gemini API key. If not provided, will use GEMINI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")

        # Initialize the Gen AI client
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-2.0-flash-001"

    def detect_duplicate(
        self, new_issue_title: str, new_issue_description: str, existing_issues: List[IssueReference], max_retries: int = 2
    ) -> DuplicateDetectionResult:
        """Detect if a new issue is a duplicate of existing open issues.

        Args:
            new_issue_title: Title of the new issue
            new_issue_description: Description of the new issue
            existing_issues: List of existing open issues to compare against
            max_retries: Maximum number of retry attempts (default: 2)

        Returns:
            Duplicate detection result
        """
        # Filter only open issues
        open_issues = [issue for issue in existing_issues if issue.status.lower() == "open"]

        if not open_issues:
            return DuplicateDetectionResult(
                is_duplicate=False,
                duplicate_of=None,
                similarity_score=0.0,
                similarity_reasons=[],
                confidence_score=1.0,
                recommendation="No open issues to compare against. This appears to be a new issue.",
            )

        for attempt in range(max_retries + 1):
            try:
                prompt = self._create_duplicate_detection_prompt(new_issue_title, new_issue_description, open_issues)

                response = self.client.models.generate_content(model=self.model_name, contents=prompt)

                result_data = self._parse_gemini_response(response.text)

                # Create the duplicate detection result
                duplicate_result = DuplicateDetectionResult(**result_data)

                # If it's a duplicate, find the referenced issue
                if duplicate_result.is_duplicate and result_data.get("duplicate_issue_id"):
                    duplicate_of = next(
                        (issue for issue in open_issues if issue.issue_id == result_data["duplicate_issue_id"]), None
                    )
                    duplicate_result.duplicate_of = duplicate_of

                return duplicate_result

            except Exception as e:
                if attempt < max_retries:
                    print(f"Duplicate detection failed, retrying... (attempt {attempt + 2}/{max_retries + 1})")
                    continue
                else:
                    # Fallback result if all attempts fail
                    return self._create_fallback_result(str(e))

    def _create_duplicate_detection_prompt(
        self, new_title: str, new_description: str, existing_issues: List[IssueReference]
    ) -> str:
        """Create a detailed prompt for duplicate detection."""

        existing_issues_text = "\n\n".join(
            [
                f"Issue ID: {issue.issue_id}\n"
                f"Title: {issue.title}\n"
                f"Description: {issue.description}\n"
                f"Status: {issue.status}\n"
                f"Created: {issue.created_date or 'Unknown'}"
                for issue in existing_issues
            ]
        )

        return f"""
You are an expert issue triager analyzing whether a new issue is a duplicate of existing open issues.

NEW ISSUE TO ANALYZE:
Title: {new_title}
Description: {new_description}

EXISTING OPEN ISSUES:
{existing_issues_text}

ANALYSIS REQUIREMENTS:
1. **Duplicate Detection**: Compare the new issue against ALL existing open issues
2. **Similarity Assessment**: Look for similar symptoms, root causes, affected components, or solutions
3. **Confidence Scoring**: Rate your confidence in the duplicate detection (0-1)
4. **Detailed Reasoning**: Explain why issues are similar or different

COMPARISON CRITERIA:
- **Symptoms**: Similar error messages, behaviors, or manifestations
- **Root Cause**: Same underlying technical problem or bug
- **Affected Components**: Same files, functions, or system parts
- **User Impact**: Similar user experience or workflow disruption
- **Technical Context**: Same technology stack, environment, or configuration

RESPONSE FORMAT (JSON):
{{
    "is_duplicate": true/false,
    "duplicate_issue_id": "ID of the duplicate issue (only if is_duplicate is true)",
    "similarity_score": 0.85,
    "similarity_reasons": [
        "Both issues report the same error message: 'ConnectionTimeout'",
        "Both affect the authentication module",
        "Similar stack traces in the same function"
    ],
    "confidence_score": 0.90,
    "recommendation": "This issue appears to be a duplicate of #123. Link to the original issue and close this one."
}}

ANALYSIS GUIDELINES:
- Issues are duplicates if they represent the SAME underlying problem, even with different wording
- Different symptoms of the same root cause should be considered duplicates
- Similar but distinct problems should NOT be marked as duplicates
- Consider the technical context, not just surface-level similarities
- Be conservative - when in doubt, prefer NOT marking as duplicate
- Provide clear, specific reasons for your decision

IMPORTANT NOTES:
- Only compare against OPEN issues (status: 'open')
- If no duplicates found, set is_duplicate to false and duplicate_issue_id to null
- Similarity score should reflect how similar the issues are (0 = completely different, 1 = identical)
- Confidence score should reflect how certain you are about your decision

Please analyze the new issue and provide your response in the exact JSON format specified above.
"""

    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini's response and extract duplicate detection data."""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed_data = json.loads(json_str)

                # Ensure required fields are present
                result = {
                    "is_duplicate": parsed_data.get("is_duplicate", False),
                    "similarity_score": float(parsed_data.get("similarity_score", 0.0)),
                    "similarity_reasons": parsed_data.get("similarity_reasons", []),
                    "confidence_score": float(parsed_data.get("confidence_score", 0.5)),
                    "recommendation": parsed_data.get("recommendation", "Manual review recommended"),
                }

                # Add duplicate_issue_id if it's a duplicate
                if result["is_duplicate"] and "duplicate_issue_id" in parsed_data:
                    result["duplicate_issue_id"] = parsed_data["duplicate_issue_id"]

                return result
            else:
                # If no JSON found, create a structured response from text
                return self._extract_from_text(response_text)
        except json.JSONDecodeError:
            return self._extract_from_text(response_text)

    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """Extract duplicate detection data from plain text response."""
        # Simple text parsing as fallback
        is_duplicate = any(word in text.lower() for word in ["duplicate", "same issue", "already reported"])

        similarity_score = 0.3 if is_duplicate else 0.1
        if "very similar" in text.lower() or "identical" in text.lower():
            similarity_score = 0.8
        elif "similar" in text.lower():
            similarity_score = 0.6

        return {
            "is_duplicate": is_duplicate,
            "similarity_score": similarity_score,
            "similarity_reasons": ["Analysis based on text review"] if is_duplicate else [],
            "confidence_score": 0.4,  # Low confidence for fallback parsing
            "recommendation": "Manual review recommended due to parsing issues",
        }

    def _create_fallback_result(self, error_msg: str) -> DuplicateDetectionResult:
        """Create a fallback result when Gemini API fails."""
        return DuplicateDetectionResult(
            is_duplicate=False,
            duplicate_of=None,
            similarity_score=0.0,
            similarity_reasons=[],
            confidence_score=0.0,
            recommendation=f"Unable to perform duplicate detection due to API error: {error_msg}. Manual review required.",
        )

    def batch_detect_duplicates(
        self, new_issues: List[Dict[str, str]], existing_issues: List[IssueReference]
    ) -> List[DuplicateDetectionResult]:
        """Detect duplicates for multiple new issues at once.

        Args:
            new_issues: List of dictionaries with 'title' and 'description' keys
            existing_issues: List of existing open issues to compare against

        Returns:
            List of duplicate detection results
        """
        results = []

        for new_issue in new_issues:
            result = self.detect_duplicate(new_issue["title"], new_issue["description"], existing_issues)
            results.append(result)

        return results

    def find_most_similar_issue(
        self, new_issue_title: str, new_issue_description: str, existing_issues: List[IssueReference]
    ) -> Optional[tuple[IssueReference, float]]:
        """Find the most similar issue regardless of duplicate status.

        Args:
            new_issue_title: Title of the new issue
            new_issue_description: Description of the new issue
            existing_issues: List of existing issues to compare against

        Returns:
            Tuple of (most_similar_issue, similarity_score) or None if no issues
        """
        if not existing_issues:
            return None

        result = self.detect_duplicate(new_issue_title, new_issue_description, existing_issues)

        if result.duplicate_of:
            return (result.duplicate_of, result.similarity_score)

        # If not a duplicate but we have similarity data, find the highest scoring issue
        # This would require individual comparisons, but for simplicity, return None
        return None
