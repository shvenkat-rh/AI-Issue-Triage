#!/usr/bin/env python3
"""
Librarian - Identifies relevant files for issue analysis using compressed context.
This is Pass 1 of the Two-Pass Architecture.
"""

import logging
import os
import re
from typing import List, Optional

from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class LibrarianAnalyzer:
    """Identifies relevant files from compressed/skeleton codebase for issue analysis."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        skeleton_path: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """Initialize the Librarian analyzer.

        Args:
            api_key: Gemini API key. If not provided, will use GEMINI_API_KEY or GOOGLE_API_KEY env var.
            skeleton_path: Path to compressed/skeleton codebase file. Defaults to repomix-output.txt.
            model_name: Gemini model name. Defaults to gemini-2.0-flash-001.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name or "gemini-2.0-flash-001"

        if not self.api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")

        # Initialize the Gen AI client
        self.client = genai.Client(api_key=self.api_key)

        # Store skeleton path for codebase loading
        self.skeleton_path = skeleton_path or "repomix-output.txt"

        # Load the skeleton/compressed codebase
        self.skeleton_content = self._load_skeleton()

    def _load_skeleton(self) -> str:
        """Load the compressed/skeleton codebase from the specified path."""
        try:
            with open(self.skeleton_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Skeleton file '{self.skeleton_path}' not found. Please ensure it exists and the path is correct."
            )

    def identify_relevant_files(self, title: str, issue_description: str) -> List[str]:
        """Identify the most relevant files for the given issue.

        Args:
            title: Issue title
            issue_description: Detailed issue description

        Returns:
            List of file paths most relevant to the issue (AI determines the count)
        """
        try:
            prompt = self._create_librarian_prompt(title, issue_description)

            logger.info("Identifying relevant files with Gemini (Librarian pass)...")
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)

            # Parse the response to extract file paths
            file_paths = self._parse_file_list(response.text)

            logger.info(f"Identified {len(file_paths)} relevant file(s): {file_paths}")
            return file_paths

        except Exception as e:
            logger.error(f"Error identifying relevant files: {e}")
            return []

    def _create_librarian_prompt(self, title: str, issue_description: str) -> str:
        """Create the prompt for the Librarian pass.

        Args:
            title: Issue title
            issue_description: Issue description

        Returns:
            Formatted prompt string
        """
        return f"""You are an expert software engineer analyzing an issue to identify relevant code files.

TASK: Identify ALL file paths that are relevant to understanding and fixing this issue.

ISSUE DETAILS:
Title: {title}
Description: {issue_description}

CODEBASE SKELETON:
{self.skeleton_content}

INSTRUCTIONS:
1. Analyze the issue description and codebase structure carefully
2. Identify ALL files that are relevant, including:
   - Files directly mentioned or implied in the issue
   - Modules/components that handle the described functionality
   - Files that import or are imported by the primary files
   - Related configuration files
   - Test files that might reveal or reproduce the issue
   - Utility/helper files used by the main files
3. Include dependency chains: if file A imports file B, include both
4. Return ONLY a numbered list of file paths, one per line
5. Do NOT include explanations or commentary
6. List files in order of relevance (most relevant first)

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
1. path/to/primary_file.py
2. path/to/related_file.py
3. path/to/imported_module.py
4. tests/test_feature.py
5. config/settings.py

Return ALL relevant files - let me handle the full context.
"""

    def _parse_file_list(self, response_text: str) -> List[str]:
        """Parse the response to extract file paths.

        Args:
            response_text: Raw response from Gemini

        Returns:
            List of file paths
        """
        file_paths = []

        # Extract lines that look like file paths
        lines = response_text.strip().split("\n")

        for line in lines:
            line = line.strip()

            # Remove leading numbers and dots (e.g., "1. ", "2. ")
            line = re.sub(r"^\d+\.\s*", "", line)

            # Remove markdown formatting
            line = re.sub(r"^[-*]\s*", "", line)
            line = re.sub(r"`", "", line)

            # Skip empty lines and obvious non-file-paths
            if not line or line.startswith("#") or line.startswith("**"):
                continue

            # Check if it looks like a file path
            if "/" in line or "\\" in line or "." in line:
                # Extract just the path if there's explanatory text
                path_match = re.search(r"([a-zA-Z0-9_/\-\.\\]+\.[a-zA-Z0-9]+)", line)
                if path_match:
                    file_paths.append(path_match.group(1))
                elif not line.startswith("(") and not line.startswith("["):
                    # Looks like a clean path
                    file_paths.append(line)

        return file_paths
