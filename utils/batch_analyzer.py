"""Gemini Batch API-powered issue analyzer for code repositories."""

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from utils.models import CodeLocation, CodeSolution, IssueAnalysis, IssueType, RootCauseAnalysis, Severity

# Load environment variables
load_dotenv()


class GeminiBatchIssueAnalyzer:
    """Analyzer that uses Google's Gemini Batch API to analyze multiple code issues efficiently."""

    def __init__(
        self, api_key: Optional[str] = None, source_path: Optional[str] = None, custom_prompt_path: Optional[str] = None
    ):
        """Initialize the Gemini batch analyzer.

        Args:
            api_key: Gemini API key. If not provided, will use GEMINI_API_KEY env var.
            source_path: Path to source of truth file. If not provided, defaults to repomix-output.txt.
            custom_prompt_path: Path to custom prompt template file. If not provided, uses default prompt.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")

        # Initialize the new Gen AI client
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-2.0-flash-001"

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

    def batch_analyze_issues(
        self, issues: List[Dict[str, str]], max_retries: int = 2, poll_interval: int = 10
    ) -> List[IssueAnalysis]:
        """Analyze multiple issues using Gemini Batch API.

        Args:
            issues: List of dictionaries with 'title' and 'description' keys
            max_retries: Maximum number of retry attempts for low quality responses (default: 2)
            poll_interval: Seconds to wait between polling for batch results (default: 10)

        Returns:
            List of complete issue analyses
        """
        if not issues:
            return []

        # Create batch request
        batch_request = self._create_batch_request(issues)

        # Submit batch job
        print(f"Submitting batch job with {len(issues)} issues...")
        batch_job = self.client.batches.create(model=self.model_name, requests=batch_request)

        print(f"Batch job created with ID: {batch_job.name}")
        print("Waiting for batch processing to complete...")

        # Poll for completion
        completed_job = self._poll_batch_job(batch_job.name, poll_interval)

        if completed_job.state != "SUCCEEDED":
            raise Exception(f"Batch job failed with state: {completed_job.state}")

        # Retrieve and parse results
        print("Batch processing complete. Retrieving results...")
        analyses = self._parse_batch_results(completed_job, issues)

        # Check for low-quality responses and retry if needed
        if max_retries > 0:
            analyses = self._retry_low_quality_responses(analyses, issues, max_retries, poll_interval)

        return analyses

    def _create_batch_request(self, issues: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Create batch request payload for Gemini Batch API.

        Args:
            issues: List of dictionaries with 'title' and 'description' keys

        Returns:
            List of request objects for batch API
        """
        batch_requests = []

        for i, issue in enumerate(issues):
            title = issue.get("title", "")
            description = issue.get("description", "")

            prompt = self._create_analysis_prompt(title, description)

            request = {
                "request": {"contents": [{"parts": [{"text": prompt}], "role": "user"}]},
                "task_id": f"issue_{i}",
            }

            batch_requests.append(request)

        return batch_requests

    def _poll_batch_job(self, batch_name: str, poll_interval: int) -> Any:
        """Poll batch job until completion.

        Args:
            batch_name: Name/ID of the batch job
            poll_interval: Seconds to wait between polls

        Returns:
            Completed batch job object
        """
        while True:
            job = self.client.batches.get(name=batch_name)

            if job.state in ["SUCCEEDED", "FAILED", "CANCELLED"]:
                return job

            print(f"Batch job status: {job.state}. Checking again in {poll_interval} seconds...")
            time.sleep(poll_interval)

    def _parse_batch_results(self, completed_job: Any, original_issues: List[Dict[str, str]]) -> List[IssueAnalysis]:
        """Parse batch job results into IssueAnalysis objects.

        Args:
            completed_job: Completed batch job object
            original_issues: Original list of issues that were analyzed

        Returns:
            List of IssueAnalysis objects
        """
        analyses = []

        # Get batch results
        results = self.client.batches.list_results(batch_name=completed_job.name)

        # Create a mapping of task_id to results
        results_map = {}
        for result in results:
            task_id = result.task_id
            results_map[task_id] = result

        # Process each issue in order
        for i, issue in enumerate(original_issues):
            task_id = f"issue_{i}"
            title = issue.get("title", "")
            description = issue.get("description", "")

            if task_id in results_map:
                result = results_map[task_id]

                try:
                    # Extract response text
                    response_text = result.response.candidates[0].content.parts[0].text

                    # Parse the response
                    analysis_data = self._parse_gemini_response(response_text)
                    analysis = IssueAnalysis(title=title, description=description, **analysis_data)
                    analyses.append(analysis)

                except Exception as e:
                    print(f"Error parsing result for issue {i}: {e}")
                    # Create fallback analysis
                    analyses.append(self._create_fallback_analysis(title, description, str(e)))
            else:
                print(f"Warning: No result found for issue {i}")
                analyses.append(self._create_fallback_analysis(title, description, "No result in batch"))

        return analyses

    def _retry_low_quality_responses(
        self, analyses: List[IssueAnalysis], original_issues: List[Dict[str, str]], max_retries: int, poll_interval: int
    ) -> List[IssueAnalysis]:
        """Retry low-quality responses.

        Args:
            analyses: List of initial analyses
            original_issues: Original list of issues
            max_retries: Maximum number of retries
            poll_interval: Polling interval in seconds

        Returns:
            Updated list of analyses with retried low-quality responses
        """
        retry_indices = []
        for i, analysis in enumerate(analyses):
            if self._is_low_quality_response(analysis):
                retry_indices.append(i)

        if not retry_indices:
            return analyses

        print(f"Found {len(retry_indices)} low-quality responses. Retrying...")

        # Retry low-quality analyses
        retry_issues = [original_issues[i] for i in retry_indices]
        retried_analyses = self.batch_analyze_issues(retry_issues, max_retries=max_retries - 1, poll_interval=poll_interval)

        # Replace low-quality analyses with retried ones
        for idx, retry_idx in enumerate(retry_indices):
            analyses[retry_idx] = retried_analyses[idx]

        return analyses

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
You are an expert software engineer analyzing a code issue for an Ansible Creator project. 
Your task is to perform comprehensive issue analysis based on the provided codebase.

ISSUE DETAILS:
Title: {title}
Description: {issue_description}

CODEBASE CONTENT:
{self.codebase_content}

ANALYSIS REQUIREMENTS:
1. **Issue Classification**: Determine if this is a 'bug', 'enhancement', or 'feature_request'
2. **Severity Assessment**: Rate as 'low', 'medium', 'high', or 'critical'
3. **Root Cause Analysis**: Identify the primary cause and contributing factors
4. **Code Location Identification**: Find relevant files, functions, and classes
5. **Solution Proposal**: Suggest specific code changes with rationale

RESPONSE FORMAT (JSON):
{{
    "issue_type": "bug|enhancement|feature_request",
    "severity": "low|medium|high|critical",
    "root_cause_analysis": {{
        "primary_cause": "Main reason for the issue",
        "contributing_factors": ["factor1", "factor2"],
        "affected_components": ["component1", "component2"],
        "related_code_locations": [
            {{
                "file_path": "path/to/file.py",
                "line_number": 123,
                "function_name": "function_name",
                "class_name": "ClassName"
            }}
        ]
    }},
    "proposed_solutions": [
        {{
            "description": "Solution description",
            "code_changes": "Specific code changes needed",
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
    "analysis_summary": "Brief summary of the analysis"
}}

ANALYSIS GUIDELINES:
- Focus on the Ansible Creator codebase structure (src/ansible_creator/)
- Consider Python-specific patterns and best practices
- Look for patterns in existing code for consistency
- Consider impact on CLI, configuration, templating, and utility modules
- Provide actionable, specific solutions

Please analyze the issue and provide your response in the exact JSON format specified above.
"""

    def _is_low_quality_response(self, analysis: IssueAnalysis) -> bool:
        """Check if the analysis response is low quality and should be retried."""
        low_quality_indicators = [
            # Check for generic/fallback descriptions
            "requires further investigation" in analysis.root_cause_analysis.primary_cause.lower(),
            "to be determined" in analysis.root_cause_analysis.primary_cause.lower(),
            "based on initial analysis" in analysis.root_cause_analysis.primary_cause.lower(),
            # Check for generic solution descriptions
            any("requires further investigation" in solution.description.lower() for solution in analysis.proposed_solutions),
            any("to be determined" in solution.code_changes.lower() for solution in analysis.proposed_solutions),
            any("based on initial analysis" in solution.rationale.lower() for solution in analysis.proposed_solutions),
            # Check for very low confidence
            analysis.confidence_score < 0.6,
            # Check for generic file paths
            any(solution.location.file_path == "src/ansible_creator/" for solution in analysis.proposed_solutions),
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
