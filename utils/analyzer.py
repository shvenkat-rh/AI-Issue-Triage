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

INSTRUCTIONS:
1. Analyze the provided codebase content thoroughly
2. Provide concrete code solutions in diff format when you have sufficient context
3. If the relevant files or context are available, propose specific code changes
4. If critical information is missing, acknowledge this and provide solutions at the appropriate level of detail
5. Aim to provide 2-3 solutions when feasible

ISSUE DETAILS:
Title: {title}
Description: {issue_description}

CODEBASE CONTENT:
{self.codebase_content}

ANALYSIS REQUIREMENTS:
1. **Issue Classification**: Determine if this is a 'bug', 'enhancement', or 'feature_request'
2. **Severity Assessment**: Rate as 'low', 'medium', 'high', or 'critical'
3. **Root Cause Analysis**: Identify the primary cause based on available information
4. **Code Location Identification**: Identify relevant files, functions, and classes when found
5. **Solution Proposal**: Provide 2-3 solutions with code changes when applicable

RESPONSE FORMAT (JSON):
{{
    "issue_type": "bug|enhancement|feature_request",
    "severity": "low|medium|high|critical",
    "root_cause_analysis": {{
        "primary_cause": "Main reason based on code analysis",
        "contributing_factors": ["factor1 with reference", "factor2 with reference"],
        "affected_components": ["component1 (file:line)", "component2 (file:line)"],
        "related_code_locations": [
            {{
                "file_path": "path/from/codebase.py",
                "line_number": 123,
                "function_name": "function_name",
                "class_name": "ClassName"
            }}
        ]
    }},
    "proposed_solutions": [
        {{
            "description": "Detailed solution description",
            "code_changes": "Code changes in diff format when applicable, or description if insufficient context",
            "location": {{
                "file_path": "path/to/file.py",
                "line_number": 123,
                "function_name": "function_name",
                "class_name": "ClassName"
            }},
            "rationale": "Why this solution works"
        }}
    ],
    "confidence_score": 0.85,
    "analysis_summary": "Brief summary of analysis"
}}

CODE SOLUTION GUIDELINES (when applicable):
- Use diff format for code changes when you have sufficient context:
  ```diff
  --- a/path/to/file.py
  +++ b/path/to/file.py
  @@ -10,5 +10,8 @@
       existing_code()
  -    old_line_to_remove()
  +    new_line_to_add()
  +    another_new_line()
  ```
- Include actual code from the codebase in your diffs
- Show context lines for clarity (unchanged code around the changes)
- Reference specific file paths, line numbers, and function/class names
- If exact implementation details are unclear, provide conceptual guidance instead of guessing

ANALYSIS BEST PRACTICES:
- Be accurate and honest about what you can determine from the codebase
- Provide code-level solutions when the relevant files and context are available
- Offer architectural or conceptual guidance when specific implementation details are missing
- Reference actual code patterns and structures from the codebase
- Prioritize correctness over completeness

Please analyze the issue and provide your response in the exact JSON format specified above.
"""

    def _is_low_quality_response(self, analysis: IssueAnalysis) -> bool:
        """Check if the analysis response is low quality and should be retried."""
        low_quality_indicators = [
            # Check for insufficient number of solutions
            len(analysis.proposed_solutions) < 1,
            # Check for very low confidence (extremely low threshold)
            analysis.confidence_score < 0.3,
            # Check for generic placeholder file paths that indicate no real analysis
            any("path/to/" in solution.location.file_path.lower() for solution in analysis.proposed_solutions),
            any("example.py" == solution.location.file_path.lower() for solution in analysis.proposed_solutions),
            # Check for empty or extremely short analysis (likely a failure case)
            len(analysis.analysis_summary.strip()) < 20,
            # Check for completely empty primary cause
            len(analysis.root_cause_analysis.primary_cause.strip()) < 10,
            # Check for solutions with no meaningful content
            any(len(solution.description.strip()) < 10 for solution in analysis.proposed_solutions),
        ]

        # Return True if any low quality indicators are present
        return any(low_quality_indicators)

    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini's response and extract analysis data."""
        # Strategy 1: Try to find JSON in code blocks first
        json_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if json_block_match:
            try:
                return json.loads(json_block_match.group(1))
            except json.JSONDecodeError:
                pass  # Try next strategy

        # Strategy 2: Try to find a JSON object by counting braces
        try:
            start_idx = response_text.find("{")
            if start_idx != -1:
                brace_count = 0
                end_idx = start_idx
                for i in range(start_idx, len(response_text)):
                    if response_text[i] == "{":
                        brace_count += 1
                    elif response_text[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break

                if end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    return json.loads(json_str)
        except json.JSONDecodeError:
            pass  # Try next strategy

        # Strategy 3: Try greedy regex as last resort
        try:
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

        # All strategies failed, fall back to text extraction
        print("Warning: Could not parse JSON from Gemini response, using fallback text extraction")
        print(f"Response preview: {response_text[:500]}...")
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

        # Try to extract meaningful content from the text
        primary_cause = "Unable to parse structured analysis from response"
        contributing_factors = []
        affected_components = []
        solutions = []

        # Try to extract sections by looking for common patterns
        cause_match = re.search(
            r"(?:primary[_\s]cause|root[_\s]cause)[:\s]*(.+?)(?:\n\n|\n[A-Z]|$)", text, re.IGNORECASE | re.DOTALL
        )
        if cause_match:
            primary_cause = cause_match.group(1).strip()[:500]

        # Extract solutions if present
        solution_pattern = r"(?:solution|fix|approach)[:\s]*(.+?)(?=(?:solution|fix|approach)[:\s]|\Z)"
        solution_matches = re.finditer(solution_pattern, text, re.IGNORECASE | re.DOTALL)
        for match in solution_matches:
            solution_text = match.group(1).strip()
            if solution_text and len(solution_text) > 20:
                # Extract code changes if present
                code_match = re.search(r"```.*?```", solution_text, re.DOTALL)
                code_changes = code_match.group(0) if code_match else solution_text[:300]

                solutions.append(
                    {
                        "description": solution_text[:200].split("\n")[0],  # First line as description
                        "code_changes": code_changes,
                        "location": {
                            "file_path": "See analysis text",
                            "line_number": None,
                            "function_name": None,
                            "class_name": None,
                        },
                        "rationale": "Extracted from unstructured response",
                    }
                )

        # If no solutions found, create one with the full text
        if not solutions:
            solutions = [
                {
                    "description": "Please review the full analysis text below",
                    "code_changes": text[:1000] if len(text) > 1000 else text,
                    "location": {
                        "file_path": "See analysis text",
                        "line_number": None,
                        "function_name": None,
                        "class_name": None,
                    },
                    "rationale": "Full response text provided due to parsing failure",
                }
            ]

        return {
            "issue_type": issue_type,
            "severity": severity,
            "root_cause_analysis": {
                "primary_cause": primary_cause,
                "contributing_factors": contributing_factors or ["See analysis text for details"],
                "affected_components": affected_components or ["See analysis text for details"],
                "related_code_locations": [],
            },
            "proposed_solutions": solutions,
            "confidence_score": 0.5,
            "analysis_summary": f"Note: Response could not be parsed as structured JSON. Raw analysis text:\n\n{text[:500]}{'...' if len(text) > 500 else ''}",
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
