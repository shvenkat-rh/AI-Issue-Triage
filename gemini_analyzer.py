"""Gemini-powered issue analyzer for code repositories."""

import os
import re
import json
from typing import Optional, Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv

from models import IssueAnalysis, IssueType, Severity, RootCauseAnalysis, CodeSolution, CodeLocation

# Load environment variables
load_dotenv()


class GeminiIssueAnalyzer:
    """Analyzer that uses Google's Gemini AI to analyze code issues."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Gemini analyzer.
        
        Args:
            api_key: Gemini API key. If not provided, will use GEMINI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY environment variable.")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Load the codebase content
        self.codebase_content = self._load_codebase()
    
    def _load_codebase(self) -> str:
        """Load the codebase content from repomix-output.txt."""
        try:
            with open("repomix-output.txt", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError("repomix-output.txt not found. Please ensure it exists in the current directory.")
    
    def analyze_issue(self, title: str, issue_description: str) -> IssueAnalysis:
        """Analyze an issue using Gemini AI.
        
        Args:
            title: Issue title
            issue_description: Detailed issue description
            
        Returns:
            Complete issue analysis
        """
        prompt = self._create_analysis_prompt(title, issue_description)
        
        try:
            response = self.model.generate_content(prompt)
            analysis_data = self._parse_gemini_response(response.text)
            
            return IssueAnalysis(
                title=title,
                description=issue_description,
                **analysis_data
            )
        except Exception as e:
            # Fallback analysis if Gemini fails
            return self._create_fallback_analysis(title, issue_description, str(e))
    
    def _create_analysis_prompt(self, title: str, issue_description: str) -> str:
        """Create a detailed prompt for Gemini analysis."""
        return f"""
You are an expert software engineer analyzing a code issue for an Ansible Creator project. 
Your task is to perform comprehensive issue analysis based on the provided codebase.

ISSUE DETAILS:
Title: {title}
Description: {issue_description}

CODEBASE CONTENT:
{self.codebase_content[:50000]}  # Limiting to first 50k chars for context

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
    
    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini's response and extract analysis data."""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
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
                "related_code_locations": []
            },
            "proposed_solutions": [{
                "description": "Requires further investigation",
                "code_changes": "To be determined after detailed analysis",
                "location": {
                    "file_path": "src/ansible_creator/",
                    "line_number": None,
                    "function_name": None,
                    "class_name": None
                },
                "rationale": "Based on initial analysis"
            }],
            "confidence_score": 0.5,
            "analysis_summary": text[:500] + "..." if len(text) > 500 else text
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
                related_code_locations=[]
            ),
            proposed_solutions=[CodeSolution(
                description="Manual analysis required",
                code_changes="Please analyze manually",
                location=CodeLocation(file_path="unknown"),
                rationale="Automated analysis failed"
            )],
            confidence_score=0.0,
            analysis_summary="Analysis failed - manual review needed"
        )
