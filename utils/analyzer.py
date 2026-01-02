"""Gemini-powered issue analyzer for code repositories."""

import json
import os
import re
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from utils.models import CodeLocation, CodeSolution, IssueAnalysis, IssueType, RootCauseAnalysis, Severity

# Load environment variables
load_dotenv()


class GeminiIssueAnalyzer:
    """Analyzer that uses Google's Gemini AI to analyze code issues."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        source_path: Optional[str] = None,
        custom_prompt_path: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """Initialize the Gemini analyzer.

        Args:
            api_key: Gemini API key. If not provided, will use GEMINI_API_KEY env var.
            source_path: Path to source of truth file. If not provided, defaults to repomix-output.txt.
            custom_prompt_path: Path to custom prompt template file. If not provided, uses default prompt.
            model_name: Gemini model name. If not provided, defaults to gemini-2.0-flash-001.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")

        # Initialize the new Gen AI client
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name or "gemini-2.0-flash-001"

        # Store source path for codebase loading
        self.source_path = source_path or "repomix-output.txt"

        # Store custom prompt path
        self.custom_prompt_path = custom_prompt_path

        # Load the codebase content
        self.codebase_content = self._load_codebase()

    def _load_codebase(self) -> str:
        """Load the codebase content from the specified source path."""
        try:
            with open(self.source_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Source file '{self.source_path}' not found. Please ensure it exists and the path is correct."
            )

    def analyze_issue(self, title: str, issue_description: str, max_retries: int = 2) -> IssueAnalysis:
        """Analyze an issue using Gemini AI with retry mechanism.

        Args:
            title: Issue title
            issue_description: Detailed issue description
            max_retries: Maximum number of retry attempts (default: 2)

        Returns:
            Complete issue analysis
        """
        for attempt in range(max_retries + 1):
            try:
                prompt = self._create_analysis_prompt(title, issue_description)

                response = self.client.models.generate_content(model=self.model_name, contents=prompt)
                analysis_data = self._parse_gemini_response(response.text)

                analysis = IssueAnalysis(title=title, description=issue_description, **analysis_data)

                # Check if this is a low-quality/fallback response
                if self._is_low_quality_response(analysis):
                    if attempt < max_retries:
                        print(f"Low quality response detected, retrying... (attempt {attempt + 2}/{max_retries + 1})")
                        continue
                    else:
                        print("Max retries reached, returning best available analysis")

                return analysis

            except Exception as e:
                if attempt < max_retries:
                    print(f"Analysis failed, retrying... (attempt {attempt + 2}/{max_retries + 1})")
                    continue
                else:
                    # Fallback analysis if all attempts fail
                    return self._create_fallback_analysis(title, issue_description, str(e))

    def _create_analysis_prompt(self, title: str, issue_description: str) -> str:
        """Create a detailed prompt for Gemini analysis."""
        if self.custom_prompt_path:
            return self._load_custom_prompt(title, issue_description)

        return self._get_default_prompt(title, issue_description)

    def _load_custom_prompt(self, title: str, issue_description: str) -> str:
        """Load and process custom prompt template."""
        try:
            with open(self.custom_prompt_path, "r", encoding="utf-8") as f:
                custom_prompt_template = f.read()

            # Replace placeholders in the custom prompt
            return custom_prompt_template.format(
                title=title, issue_description=issue_description, codebase_content=self.codebase_content
            )
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Custom prompt file '{self.custom_prompt_path}' not found. Please ensure it exists and the path is correct."
            )
        except KeyError as e:
            raise ValueError(
                f"Custom prompt template missing required placeholder: {e}. Available placeholders: {{title}}, {{issue_description}}, {{codebase_content}}"
            )

    def _get_default_prompt(self, title: str, issue_description: str) -> str:
        """Get the default analysis prompt."""
        return f"""
You are an expert software engineer analyzing a code issue. 
Your task is to perform comprehensive issue analysis based on the provided codebase.

CRITICAL INSTRUCTIONS:
1. You MUST use actual code from the CODEBASE CONTENT section below
2. You MUST include actual code snippets in diff format in your solutions
3. You MUST reference specific file paths, line numbers, and function names from the provided code
4. DO NOT use generic placeholders like "path/to/file.py" - use actual paths from the codebase
5. If the codebase is insufficient, state what specific files/code you need

ISSUE DETAILS:
Title: {title}
Description: {issue_description}

CODEBASE CONTENT:
{self.codebase_content}

ANALYSIS REQUIREMENTS:
1. **Issue Classification**: Determine if this is a 'bug', 'enhancement', or 'feature_request'
2. **Severity Assessment**: Rate as 'low', 'medium', 'high', or 'critical'
3. **Root Cause Analysis**: Identify the primary cause and contributing factors using actual code references
4. **Code Location Identification**: Find relevant files, functions, and classes from the PROVIDED codebase
5. **Solution Proposal**: Suggest specific code changes with actual code snippets in diff format

RESPONSE FORMAT (JSON):
{{
    "issue_type": "bug|enhancement|feature_request",
    "severity": "low|medium|high|critical",
    "root_cause_analysis": {{
        "primary_cause": "Main reason based on actual code analysis",
        "contributing_factors": ["factor1 with code reference", "factor2 with code reference"],
        "affected_components": ["component1 (file:line)", "component2 (file:line)"],
        "related_code_locations": [
            {{
                "file_path": "actual/path/from/codebase.py",
                "line_number": 123,
                "function_name": "actual_function_name",
                "class_name": "ActualClassName"
            }}
        ]
    }},
    "proposed_solutions": [
        {{
            "description": "Solution description based on actual code structure",
            "code_changes": "```diff\\n- old_code_line_from_codebase\\n+ new_code_line_with_fix\\n```",
            "location": {{
                "file_path": "actual/path/from/codebase.py",
                "line_number": 123,
                "function_name": "actual_function_name",
                "class_name": "ActualClassName"
            }},
            "rationale": "Why this solution works based on the actual code patterns"
        }}
    ],
    "confidence_score": 0.85,
    "analysis_summary": "Brief summary referencing actual code elements"
}}

ANALYSIS GUIDELINES:
- Use ONLY information from the provided codebase
- Include actual code snippets in diff format for all proposed solutions
- Reference actual file paths, function names, and line numbers
- Consider language-specific patterns and best practices
- Look for patterns in existing code for consistency
- Provide actionable, specific solutions with before/after code examples
- If codebase is insufficient, explicitly state what additional context is needed

VALIDATION CHECKLIST (Your response MUST satisfy ALL):
✓ All file paths are from the actual provided codebase (not generic placeholders)
✓ All code snippets are actual code from the codebase (not hypothetical examples)
✓ All proposed solutions include diff-format code changes with real code
✓ All line numbers and function names reference actual code locations
✓ Code changes show both before (from codebase) and after (with fix)

Please analyze the issue and provide your response in the exact JSON format specified above.
"""

    def _is_low_quality_response(self, analysis: IssueAnalysis) -> bool:
        """Check if the analysis response is low quality and should be retried."""
        low_quality_indicators = [
            # Check for generic/fallback descriptions
            "requires further investigation" in analysis.root_cause_analysis.primary_cause.lower(),
            "to be determined" in analysis.root_cause_analysis.primary_cause.lower(),
            "based on initial analysis" in analysis.root_cause_analysis.primary_cause.lower(),
            "limited" in analysis.root_cause_analysis.primary_cause.lower() and "codebase" in analysis.root_cause_analysis.primary_cause.lower(),
            "extremely limited" in analysis.root_cause_analysis.primary_cause.lower(),
            "no codebase" in analysis.root_cause_analysis.primary_cause.lower(),
            # Check for generic solution descriptions
            any("requires further investigation" in solution.description.lower() for solution in analysis.proposed_solutions),
            any("to be determined" in solution.code_changes.lower() for solution in analysis.proposed_solutions),
            any("based on initial analysis" in solution.rationale.lower() for solution in analysis.proposed_solutions),
            any("without the actual codebase" in solution.description.lower() for solution in analysis.proposed_solutions),
            # Check for very low confidence
            analysis.confidence_score < 0.6,
            # Check for generic file paths (placeholders)
            any("path/to/" in solution.location.file_path.lower() for solution in analysis.proposed_solutions),
            any("/path/" in solution.location.file_path.lower() for solution in analysis.proposed_solutions),
            any("file.py" == solution.location.file_path.lower() for solution in analysis.proposed_solutions),
            any("example" in solution.location.file_path.lower() for solution in analysis.proposed_solutions),
            # Check for missing diff format in code changes
            any("```diff" not in solution.code_changes for solution in analysis.proposed_solutions if solution.code_changes),
            # Check for empty or very short analysis
            len(analysis.analysis_summary.strip()) < 50,
        ]

        # Return True if any low quality indicators are present
        return any(low_quality_indicators)

    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini's response and extract analysis data."""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                # If no JSON found, create a structured response from text
                return self._extract_from_text(response_text)
        except json.JSONDecodeError:
            return self._extract_from_text(response_text)

    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """Extract analysis data from plain text response."""
        # Simple text parsing as fallback
        issue_type = "bug"  # default
        if any(word in text.lower() for word in ["enhancement", "improve", "optimize"]):
            issue_type = "enhancement"
        elif any(word in text.lower() for word in ["feature", "new", "add"]):
            issue_type = "feature_request"

        severity = "medium"  # default
        if any(word in text.lower() for word in ["critical", "severe", "urgent"]):
            severity = "critical"
        elif any(word in text.lower() for word in ["high", "important"]):
            severity = "high"
        elif any(word in text.lower() for word in ["low", "minor"]):
            severity = "low"

        return {
            "issue_type": issue_type,
            "severity": severity,
            "root_cause_analysis": {
                "primary_cause": "Analysis based on codebase review",
                "contributing_factors": ["Requires detailed code inspection"],
                "affected_components": ["To be determined"],
                "related_code_locations": [],
            },
            "proposed_solutions": [
                {
                    "description": "Requires further investigation",
                    "code_changes": "To be determined after detailed analysis",
                    "location": {
                        "file_path": "src/ansible_creator/",
                        "line_number": None,
                        "function_name": None,
                        "class_name": None,
                    },
                    "rationale": "Based on initial analysis",
                }
            ],
            "confidence_score": 0.5,
            "analysis_summary": text[:500] + "..." if len(text) > 500 else text,
        }

    def _create_fallback_analysis(self, title: str, description: str, error_msg: str) -> IssueAnalysis:
        """Create a fallback analysis when Gemini API fails."""
        return IssueAnalysis(
            title=title,
            description=description,
            issue_type=IssueType.BUG,
            severity=Severity.MEDIUM,
            root_cause_analysis=RootCauseAnalysis(
                primary_cause=f"Unable to analyze due to API error: {error_msg}",
                contributing_factors=["API unavailable"],
                affected_components=["Unknown"],
                related_code_locations=[],
            ),
            proposed_solutions=[
                CodeSolution(
                    description="Manual analysis required",
                    code_changes="Please analyze manually",
                    location=CodeLocation(file_path="unknown"),
                    rationale="Automated analysis failed",
                )
            ],
            confidence_score=0.0,
            analysis_summary="Analysis failed - manual review needed",
        )
