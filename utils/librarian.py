#!/usr/bin/env python3
"""
Librarian - Identifies relevant files for issue analysis using directory chunks.
This is Pass 1 of the Two-Pass Architecture.
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class LibrarianAnalyzer:
    """Identifies relevant files from directory-chunked codebase for issue analysis."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        chunks_dir: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """Initialize the Librarian analyzer.

        Args:
            api_key: Gemini API key. If not provided, will use GEMINI_API_KEY or GOOGLE_API_KEY env var.
            chunks_dir: Path to directory containing repomix chunks. Defaults to repomix-chunks.
            model_name: Gemini model name. Defaults to gemini-2.0-flash-001.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name or "gemini-2.0-flash-001"

        if not self.api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")

        # Initialize the Gen AI client
        self.client = genai.Client(api_key=self.api_key)

        # Store chunks directory
        self.chunks_dir = Path(chunks_dir or "repomix-chunks")

        # Load all directory chunks
        self.chunks = self._load_chunks()

    def _load_chunks(self) -> Dict[str, str]:
        """Load all repomix chunks from the chunks directory.

        Returns:
            Dictionary mapping chunk name to content
        """
        chunks = {}

        if not self.chunks_dir.exists():
            raise FileNotFoundError(f"Chunks directory '{self.chunks_dir}' not found. Please ensure it exists.")

        for chunk_file in self.chunks_dir.glob("*.txt"):
            chunk_name = chunk_file.stem
            try:
                with open(chunk_file, "r", encoding="utf-8") as f:
                    chunks[chunk_name] = f.read()
                logger.info(f"Loaded chunk: {chunk_name} ({len(chunks[chunk_name])} bytes)")
            except Exception as e:
                logger.warning(f"Failed to load chunk {chunk_name}: {e}")

        if not chunks:
            raise ValueError(f"No chunks found in {self.chunks_dir}")

        logger.info(f"Loaded {len(chunks)} chunks")
        return chunks

    def identify_relevant_files(self, title: str, issue_description: str) -> Dict[str, any]:
        """Identify the most relevant files for the given issue by analyzing directory chunks.

        Args:
            title: Issue title
            issue_description: Detailed issue description

        Returns:
            Dictionary with relevant_files list and analysis_summary
        """
        try:
            # Analyze each chunk to find relevant directories
            relevant_chunks = self._identify_relevant_chunks(title, issue_description)

            if not relevant_chunks:
                logger.warning("No relevant chunks identified")
                return {"relevant_files": [], "analysis_summary": "No relevant code found"}

            # Extract specific files from relevant chunks
            all_files = set()
            for chunk_name in relevant_chunks:
                files = self._extract_files_from_chunk(chunk_name, title, issue_description)
                all_files.update(files)

            # Analyze dependencies and add supporting files
            final_files = self._analyze_dependencies(all_files)

            logger.info(f"Identified {len(final_files)} relevant file(s) total")

            return {
                "relevant_files": sorted(list(final_files)),
                "relevant_chunks": relevant_chunks,
                "analysis_summary": f"Analyzed {len(self.chunks)} directories, found {len(relevant_chunks)} relevant, identified {len(final_files)} files",
            }

        except Exception as e:
            logger.error(f"Error identifying relevant files: {e}")
            return {"relevant_files": [], "analysis_summary": f"Analysis failed: {str(e)}"}

    def _identify_relevant_chunks(self, title: str, issue_description: str) -> List[str]:
        """Identify which directory chunks are relevant to the issue.

        Args:
            title: Issue title
            issue_description: Issue description

        Returns:
            List of chunk names that are relevant
        """
        prompt = f"""You are analyzing a software issue to identify which directories contain relevant code.

ISSUE:
Title: {title}
Description: {issue_description}

AVAILABLE DIRECTORIES:
{', '.join(self.chunks.keys())}

TASK: Return ONLY the directory names (from the list above) that are most likely to contain code related to this issue.

INSTRUCTIONS:
1. Consider the issue description and which directories would contain the relevant code
2. Include root if root-level files might be relevant
3. Return ONLY directory names, one per line
4. NO explanations, NO numbering, just the names

Example output format:
root
plugins_modules
lib_ansible
tests"""

        try:
            logger.info("Identifying relevant directories...")
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)

            relevant_chunks = []
            for line in response.text.strip().split("\n"):
                chunk_name = line.strip()
                if chunk_name in self.chunks:
                    relevant_chunks.append(chunk_name)
                    logger.info(f"  ✓ Relevant chunk: {chunk_name}")

            return relevant_chunks
        except Exception as e:
            logger.error(f"Error identifying relevant chunks: {e}")
            # Fallback: return all chunks if analysis fails
            return list(self.chunks.keys())

    def _extract_files_from_chunk(self, chunk_name: str, title: str, issue_description: str) -> Set[str]:
        """Extract specific relevant files from a chunk.

        Args:
            chunk_name: Name of the chunk to analyze
            title: Issue title
            issue_description: Issue description

        Returns:
            Set of file paths
        """
        chunk_content = self.chunks[chunk_name]

        prompt = f"""You are analyzing compressed code from the "{chunk_name}" directory to identify specific files relevant to this issue.

ISSUE:
Title: {title}
Description: {issue_description}

DIRECTORY CONTENT ({chunk_name}):
{chunk_content}

TASK: Return ONLY the file paths (with full relative paths) that are relevant to this issue.

INSTRUCTIONS:
1. Extract specific file paths from the content above
2. Include files that directly relate to the issue
3. Return ONLY file paths, one per line
4. Use the full relative path (e.g., "plugins/modules/file.py")
5. NO explanations, NO numbering

Example output format:
plugins/modules/ios_vlans.py
plugins/module_utils/network/ios/config/vlans/vlans.py
tests/unit/modules/network/ios/test_ios_vlans.py"""

        try:
            logger.info(f"Extracting files from chunk: {chunk_name}")
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)

            files = set()
            for line in response.text.strip().split("\n"):
                file_path = line.strip()
                # Basic validation - must have / and a file extension, not start with # or be too long
                if (
                    file_path
                    and "/" in file_path
                    and "." in file_path.split("/")[-1]  # Has extension in filename
                    and not file_path.startswith("#")
                    and not file_path.lower().startswith("there")  # Filter out error messages
                    and not file_path.lower().startswith("no ")
                    and len(file_path) < 200  # Reasonable path length
                ):
                    files.add(file_path)

            logger.info(f"  Found {len(files)} files in {chunk_name}")
            return files
        except Exception as e:
            logger.error(f"Error extracting files from chunk {chunk_name}: {e}")
            return set()

    def _analyze_dependencies(self, files: Set[str]) -> Set[str]:
        """Analyze files to identify dependencies and add supporting files.

        Args:
            files: Set of primary file paths

        Returns:
            Expanded set including dependencies
        """
        # For now, return files as-is
        # In future: could analyze import statements, module relationships, etc.
        # This would require more sophisticated parsing of the chunks
        logger.info(f"Dependency analysis: {len(files)} files")
        return files
