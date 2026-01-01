#!/usr/bin/env python3
"""
PR Reviewer using Gemini API
"""
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from dotenv import load_dotenv
from google import genai

from utils.models import PRFileChange, PRReview, PRReviewComment

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class PRAnalyzer:
    """Analyze pull requests using Gemini API"""

    def __init__(self, api_key: Optional[str] = None, config_path: Optional[str] = None, model_name: Optional[str] = None):
        """Initialize the PR analyzer with Gemini API key

        Args:
            api_key: Gemini API key. If not provided, will use GEMINI_API_KEY or GOOGLE_API_KEY env var.
            config_path: Path to prompt configuration file. If not provided, uses default config.
            model_name: Gemini model name. If not provided, defaults to gemini-2.0-flash-001.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name or "gemini-2.0-flash-001"

        if not self.api_key:
            logger.warning("Gemini API key not provided")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

        # Load prompt configuration
        self.prompt_config = self._load_prompt_config(config_path)
        logger.info(f"Loaded prompt configuration with repo types: {list(self.prompt_config.get('prompts', {}).keys())}")

    def _load_prompt_config(self, config_path: Optional[str] = None) -> Dict:
        """Load prompt configuration from YAML file

        Args:
            config_path: Path to the configuration file

        Returns:
            Configuration dictionary
        """
        if config_path is None:
            # Default to pr_prompt_config.yml in the project root
            config_path = Path(__file__).parent.parent / "pr_prompt_config.yml"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            logger.warning(f"Prompt config file not found: {config_path}. Using default prompts.")
            return self._get_default_config()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.info(f"Successfully loaded prompt config from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading prompt config: {e}. Using default prompts.")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Return default configuration if YAML file is not available

        Returns:
            Default configuration dictionary
        """
        return {
            "repo_mappings": {},
            "prompts": {
                "default": {
                    "pr_review": {
                        "system_role": "You are an expert code reviewer. Review the following pull request and provide constructive feedback.",
                        "review_structure": """Please provide a comprehensive code review with the following structure:

1. **Overall Assessment**: Brief summary of the PR
2. **Strengths**: What was done well
3. **Issues Found**: List any bugs, security issues, performance problems, or code quality concerns
4. **Suggestions**: Recommendations for improvement
5. **File-specific Comments**: For each file with issues, provide:
   - File path
   - Line number (if applicable)
   - Specific comment
6. Every new function should contain a docstring explaining its purpose and parameters. Please point it out.

Format your response clearly with markdown. Be constructive and professional.""",
                        "workflow_analysis": """Please provide:
1. **Summary**: Brief overview of the workflow execution
2. **Success Analysis**: If successful, highlight what worked well
3. **Failure Analysis**: If failed, identify:
   - Root causes of failures
   - Common patterns in errors
   - Suggestions for fixing the issues
4. **Recommendations**: Actionable steps to improve the workflow or fix issues
5. **Best Practices**: Suggestions for workflow improvements

Be concise, actionable, and helpful. Format your response with clear markdown sections.""",
                    }
                }
            },
        }

    def _get_repo_type(self, repo_url: str) -> str:
        """Determine repo type based on URL patterns

        Args:
            repo_url: Repository URL

        Returns:
            Repository type identifier
        """
        if not repo_url:
            return "default"

        repo_mappings = self.prompt_config.get("repo_mappings", {})

        # Check each repo type's URL patterns
        for repo_type, patterns in repo_mappings.items():
            for pattern in patterns:
                try:
                    if re.search(pattern, repo_url, re.IGNORECASE):
                        logger.info(f"Matched repo URL '{repo_url}' to type '{repo_type}' using pattern '{pattern}'")
                        return repo_type
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{pattern}': {e}")

        logger.info(f"No match found for repo URL '{repo_url}', using default prompt")
        return "default"

    def _get_prompt(self, prompt_type: str, repo_type: str = "default") -> Dict:
        """Get prompt configuration for a specific type and repo

        Args:
            prompt_type: Type of prompt (e.g., 'pr_review', 'workflow_analysis')
            repo_type: Type of repository

        Returns:
            Prompt configuration dictionary
        """
        prompts = self.prompt_config.get("prompts", {})

        # Try to get repo-specific prompt
        if repo_type in prompts:
            repo_prompts = prompts[repo_type]
            if prompt_type in repo_prompts:
                return repo_prompts[prompt_type]

        # Fallback to default
        default_prompts = prompts.get("default", {})
        if prompt_type in default_prompts:
            return default_prompts[prompt_type]

        # Ultimate fallback
        logger.warning(f"Prompt type '{prompt_type}' not found, using empty dict")
        return {}

    def _get_workflow_analysis_prompt(self, repo_type: str = "default") -> str:
        """Get workflow analysis prompt template for a specific repo type

        Args:
            repo_type: Type of repository

        Returns:
            Workflow analysis prompt string
        """
        prompts = self.prompt_config.get("prompts", {})

        # Try to get repo-specific workflow analysis
        if repo_type in prompts:
            repo_prompts = prompts[repo_type]
            if "pr_review" in repo_prompts and "workflow_analysis" in repo_prompts["pr_review"]:
                return repo_prompts["pr_review"]["workflow_analysis"]

        # Fallback to default
        default_prompts = prompts.get("default", {})
        if "pr_review" in default_prompts and "workflow_analysis" in default_prompts["pr_review"]:
            return default_prompts["pr_review"]["workflow_analysis"]

        return ""

    def review_pr(self, title: str, body: str, file_changes: List[Dict], repo_url: Optional[str] = None) -> PRReview:
        """
        Review a pull request and generate comments

        Args:
            title: PR title
            body: PR description
            file_changes: List of file change dictionaries with keys: filename, status, additions, deletions, patch
            repo_url: Optional repository URL for determining review style

        Returns:
            PRReview object containing review summary and file comments
        """
        if not self.client:
            logger.error("Gemini client not initialized")
            return PRReview(
                summary="Error: Gemini API key not configured",
                file_comments=[],
                overall_assessment="Unable to perform review without API key",
                strengths=[],
                issues_found=[],
                suggestions=[],
                confidence_score=0.0,
            )

        try:
            # Determine repo type and get appropriate prompt
            repo_type = self._get_repo_type(repo_url or "")

            # Prepare context for review
            review_prompt = self._build_review_prompt(title, body, file_changes, repo_type)

            # Generate review
            logger.info("Generating review with Gemini API...")
            response = self.client.models.generate_content(model=self.model_name, contents=review_prompt)

            # Parse response
            review_text = response.text

            # Structure the review
            review = self._parse_review(review_text, file_changes, title, body)

            return review

        except Exception as e:
            logger.error(f"Error generating review: {e}")
            return PRReview(
                summary=f"Error generating review: {str(e)}",
                file_comments=[],
                overall_assessment=f"Review failed: {str(e)}",
                strengths=[],
                issues_found=[],
                suggestions=[],
                confidence_score=0.0,
            )

    def _build_review_prompt(self, title: str, body: str, file_changes: List[Dict], repo_type: str = "default") -> str:
        """Build the prompt for Gemini API using repo-specific configuration

        Args:
            title: PR title
            body: PR description
            file_changes: List of file changes
            repo_type: Type of repository

        Returns:
            Formatted prompt string
        """
        # Get prompt configuration for this repo type
        prompt_config = self._get_prompt("pr_review", repo_type)
        system_role = prompt_config.get(
            "system_role",
            "You are an expert code reviewer. Review the following pull request and provide constructive feedback.",
        )
        review_structure = prompt_config.get("review_structure", "")

        # Build the prompt
        prompt = f"""{system_role}

Pull Request Title: {title}

Pull Request Description:
{body}

Changed Files:
"""

        for file_change in file_changes:
            filename = file_change.get("filename", "unknown")
            status = file_change.get("status", "unknown")
            additions = file_change.get("additions", 0)
            deletions = file_change.get("deletions", 0)
            patch = file_change.get("patch", "")

            prompt += f"\n--- File: {filename} ({status}) ---\n"
            prompt += f"Additions: +{additions}, Deletions: -{deletions}\n"

            if patch:
                # Limit patch size to avoid token limits
                patch_preview = patch[:5000] if len(patch) > 5000 else patch
                prompt += f"\nDiff:\n{patch_preview}\n"
                if len(patch) > 5000:
                    prompt += "\n[... diff truncated ...]\n"

        prompt += f"\n{review_structure}"

        return prompt

    def _parse_review(self, review_text: str, file_changes: List[Dict], title: str, body: str) -> PRReview:
        """Parse the review response into structured format

        Args:
            review_text: Raw review text from Gemini
            file_changes: List of file changes
            title: PR title
            body: PR description

        Returns:
            Structured PRReview object
        """
        # Extract file-specific comments
        file_comments = []

        # Try to extract file-specific comments from the review
        lines = review_text.split("\n")
        current_file = None
        current_line = None
        current_comment = []

        for i, line in enumerate(lines):
            # Look for file references
            if "File:" in line or "**" in line:
                # Try to extract filename
                for file_change in file_changes:
                    filename = file_change.get("filename", "")
                    if filename in line:
                        # Save previous comment if exists
                        if current_file and current_comment:
                            file_comments.append(
                                PRReviewComment(
                                    file_path=current_file,
                                    line_number=current_line,
                                    comment="\n".join(current_comment).strip(),
                                )
                            )
                        current_file = filename
                        current_line = None
                        current_comment = []
                        break

            # Look for line numbers
            if current_file and ("line" in line.lower() and any(char.isdigit() for char in line)):
                try:
                    # Extract line number
                    words = line.split()
                    for word in words:
                        if word.isdigit():
                            current_line = int(word)
                            break
                except:
                    pass

            # Collect comment lines
            if current_file and line.strip() and not line.startswith("#"):
                current_comment.append(line)

        # Save last comment if exists
        if current_file and current_comment:
            file_comments.append(
                PRReviewComment(file_path=current_file, line_number=current_line, comment="\n".join(current_comment).strip())
            )

        # Extract sections from review text
        overall_assessment = self._extract_section(review_text, ["Overall Assessment", "Summary"])
        strengths = self._extract_list_section(review_text, ["Strengths", "What was done well"])
        issues_found = self._extract_list_section(review_text, ["Issues Found", "Issues", "Problems"])
        suggestions = self._extract_list_section(review_text, ["Suggestions", "Recommendations"])

        # If we couldn't extract an overall assessment but have review text, use a summary
        if not overall_assessment and review_text:
            # Take the first paragraph or first 500 characters as assessment
            first_para = review_text.split("\n\n")[0].strip()
            if first_para and not first_para.startswith("#"):
                overall_assessment = first_para
            else:
                # Fallback: create assessment from what we found
                parts = []
                if strengths:
                    parts.append(f"Found {len(strengths)} strength(s)")
                if issues_found:
                    parts.append(f"{len(issues_found)} issue(s)")
                if suggestions:
                    parts.append(f"{len(suggestions)} suggestion(s)")

                if parts:
                    overall_assessment = "This PR has " + ", ".join(parts) + "."
                else:
                    overall_assessment = "Review completed. See full summary below."

        # Create structured review
        return PRReview(
            summary=review_text,
            file_comments=file_comments,
            overall_assessment=overall_assessment or "Review completed successfully.",
            strengths=strengths,
            issues_found=issues_found,
            suggestions=suggestions,
            confidence_score=0.85,  # Default confidence
        )

    def _extract_section(self, text: str, section_headers: List[str]) -> Optional[str]:
        """Extract a section from markdown text based on headers

        Args:
            text: Text to search
            section_headers: List of possible section headers

        Returns:
            Extracted section text or None
        """
        for header in section_headers:
            # Look for markdown headers
            pattern = rf"#+\s*\*?\*?{re.escape(header)}\*?\*?:?\s*\n(.*?)(?=\n#+|\Z)"
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_list_section(self, text: str, section_headers: List[str]) -> List[str]:
        """Extract a list section from markdown text

        Args:
            text: Text to search
            section_headers: List of possible section headers

        Returns:
            List of extracted items
        """
        section_text = self._extract_section(text, section_headers)
        if not section_text:
            return []

        # Extract list items (both - and numbered)
        items = []
        for line in section_text.split("\n"):
            line = line.strip()
            # Match bullet points or numbered lists
            if re.match(r"^[-*•]\s+", line) or re.match(r"^\d+\.\s+", line):
                # Remove the bullet or number
                item = re.sub(r"^[-*•]\s+", "", line)
                item = re.sub(r"^\d+\.\s+", "", item)
                items.append(item.strip())

        return items

    def format_review_summary(self, review: PRReview) -> str:
        """Format review for GitHub comment or display

        Args:
            review: PRReview object

        Returns:
            Formatted markdown string
        """
        # Add header
        formatted = "## 🤖 AI Code Review (Powered by Gemini)\n\n"

        # Add overall assessment
        if review.overall_assessment:
            formatted += f"### 📋 Overall Assessment\n\n{review.overall_assessment}\n\n"
            formatted += "---\n\n"

        # Add strengths
        if review.strengths:
            formatted += "### ✅ Strengths\n\n"
            for strength in review.strengths:
                formatted += f"- {strength}\n"
            formatted += "\n"

        # Add issues
        if review.issues_found:
            formatted += "### ⚠️ Issues Found\n\n"
            for issue in review.issues_found:
                formatted += f"- {issue}\n"
            formatted += "\n"

        # Add suggestions
        if review.suggestions:
            formatted += "### 💡 Suggestions\n\n"
            for suggestion in review.suggestions:
                formatted += f"- {suggestion}\n"
            formatted += "\n"

        # Add file-specific comments if any
        if review.file_comments:
            formatted += "### 📝 File-specific Comments\n\n"
            for comment in review.file_comments:
                formatted += f"**`{comment.file_path}`**"
                if comment.line_number:
                    formatted += f" (line {comment.line_number})"
                formatted += f":\n{comment.comment}\n\n"

        # If no structured content was extracted, show the full summary
        if not any([review.strengths, review.issues_found, review.suggestions, review.file_comments]):
            formatted += "### 📝 Full Review\n\n"
            formatted += "<details>\n<summary><b>View Complete Analysis</b></summary>\n\n"
            formatted += review.summary
            formatted += "\n\n</details>\n\n"

        # Add confidence score
        confidence_percent = int(review.confidence_score * 100)
        formatted += f"\n📊 **Confidence Score:** {confidence_percent}%\n\n"

        formatted += "---\n"
        formatted += "<sub>🤖 <i>This review was generated automatically by the Gemini AI Code Review Bot.</i></sub>"

        return formatted

    def analyze_workflow_run(
        self,
        workflow_name: str,
        conclusion: str,
        jobs: List[Dict],
        failed_jobs: List[str],
        workflow_url: str = "",
        repo_url: Optional[str] = None,
    ) -> str:
        """
        Analyze a GitHub Actions workflow run and provide insights

        Args:
            workflow_name: Name of the workflow
            conclusion: Workflow conclusion (success, failure, cancelled, etc.)
            jobs: List of job information dictionaries
            failed_jobs: List of failed job names
            workflow_url: URL to the workflow run
            repo_url: Optional repository URL for determining analysis style

        Returns:
            Analysis text string
        """
        if not self.client:
            logger.error("Gemini client not initialized")
            return self._format_basic_workflow_analysis(conclusion, failed_jobs)

        try:
            # Determine repo type and get appropriate prompt
            repo_type = self._get_repo_type(repo_url or "")

            # Build prompt for workflow analysis
            prompt = self._build_workflow_analysis_prompt(workflow_name, conclusion, jobs, failed_jobs, repo_type)

            # Generate analysis
            logger.info("Generating workflow analysis with Gemini API...")
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            analysis = response.text

            return analysis

        except Exception as e:
            logger.error(f"Error generating workflow analysis: {e}")
            return self._format_basic_workflow_analysis(conclusion, failed_jobs)

    def _build_workflow_analysis_prompt(
        self, workflow_name: str, conclusion: str, jobs: List[Dict], failed_jobs: List[str], repo_type: str = "default"
    ) -> str:
        """Build the prompt for workflow analysis using repo-specific configuration

        Args:
            workflow_name: Name of the workflow
            conclusion: Workflow conclusion
            jobs: List of job information
            failed_jobs: List of failed job names
            repo_type: Type of repository

        Returns:
            Formatted prompt string
        """
        # Get workflow analysis template for this repo type
        workflow_analysis_template = self._get_workflow_analysis_prompt(repo_type)

        prompt = f"""You are analyzing a GitHub Actions workflow run. Provide insights about the workflow execution.

Workflow Name: {workflow_name}
Conclusion: {conclusion}

Jobs Executed:
"""

        for job in jobs:
            job_name = job.get("name", "Unknown")
            job_conclusion = job.get("conclusion", "unknown")
            job_status = job.get("status", "unknown")
            steps = job.get("steps", [])

            prompt += f"\n- **{job_name}**\n"
            prompt += f"  Status: {job_status}, Conclusion: {job_conclusion}\n"

            if steps:
                prompt += "  Steps:\n"
                for step in steps:
                    step_name = step.get("name", "Unknown")
                    step_conclusion = step.get("conclusion", "unknown")
                    step_status = step.get("status", "unknown")
                    status_icon = "✅" if step_conclusion == "success" else "❌" if step_conclusion == "failure" else "⏳"
                    prompt += f"    {status_icon} {step_name}: {step_status} ({step_conclusion})\n"

        if failed_jobs:
            prompt += f"\n**Failed Jobs:** {', '.join(failed_jobs)}\n"

        if workflow_analysis_template:
            prompt += f"\n{workflow_analysis_template}"
        else:
            # Fallback to default structure
            prompt += """
Please provide:
1. **Summary**: Brief overview of the workflow execution
2. **Success Analysis**: If successful, highlight what worked well
3. **Failure Analysis**: If failed, identify:
   - Root causes of failures
   - Common patterns in errors
   - Suggestions for fixing the issues
4. **Recommendations**: Actionable steps to improve the workflow or fix issues
5. **Best Practices**: Suggestions for workflow improvements

Be concise, actionable, and helpful. Format your response with clear markdown sections.
"""

        return prompt

    def _format_basic_workflow_analysis(self, conclusion: str, failed_jobs: List[str]) -> str:
        """Fallback basic analysis when Gemini is not available

        Args:
            conclusion: Workflow conclusion
            failed_jobs: List of failed job names

        Returns:
            Basic analysis string
        """
        if conclusion == "success":
            return "✅ **Workflow completed successfully!**\n\nAll jobs passed. Great work!"
        elif conclusion == "failure":
            analysis = "❌ **Workflow failed**\n\n"
            if failed_jobs:
                analysis += f"**Failed Jobs:** {', '.join(failed_jobs)}\n\n"
            analysis += "Please review the workflow logs to identify the issues."
            return analysis
        else:
            return f"⚠️ **Workflow {conclusion}**\n\nPlease check the workflow logs for details."
