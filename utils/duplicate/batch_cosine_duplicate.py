"""Optimized batch cosine similarity-based duplicate issue analyzer."""

import re
from typing import List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from utils.models import DuplicateDetectionResult, IssueReference


class CosineBatchDuplicateAnalyzer:
    """Analyzer that uses cosine similarity with TF-IDF to detect duplicate issues in batch."""

    def __init__(self, similarity_threshold: float = 0.6, confidence_threshold: float = 0.6):
        """Initialize the cosine similarity batch duplicate analyzer.

        Args:
            similarity_threshold: Minimum similarity score to consider issues as duplicates (default: 0.6)
            confidence_threshold: Minimum confidence score for high-confidence results (default: 0.6)
        """
        self.similarity_threshold = similarity_threshold
        self.confidence_threshold = confidence_threshold
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            lowercase=True,
            ngram_range=(1, 2),  # Use unigrams and bigrams
            max_features=5000,  # Limit vocabulary size
            min_df=1,  # Minimum document frequency
            max_df=0.95,  # Maximum document frequency (ignore very common terms)
        )

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for better similarity matching.

        Args:
            text: Raw text to preprocess

        Returns:
            Preprocessed text
        """
        if not text:
            return ""

        # Convert to lowercase
        text = text.lower()

        # Remove special characters and extra whitespace
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _combine_issue_text(self, issue: IssueReference) -> str:
        """Combine issue title and description for analysis.

        Args:
            issue: Issue reference object

        Returns:
            Combined text for similarity analysis
        """
        # Give more weight to title by including it twice
        title = self._preprocess_text(issue.title)
        description = self._preprocess_text(issue.description)

        # Combine title (weighted) and description
        combined = f"{title} {title} {description}"
        return combined

    def _combine_new_issue_text(self, title: str, description: str) -> str:
        """Combine new issue title and description for analysis.

        Args:
            title: Issue title
            description: Issue description

        Returns:
            Combined text for similarity analysis
        """
        # Give more weight to title by including it twice
        title_clean = self._preprocess_text(title)
        description_clean = self._preprocess_text(description)

        # Combine title (weighted) and description
        combined = f"{title_clean} {title_clean} {description_clean}"
        return combined

    def _calculate_similarity_reasons(
        self, new_issue_title: str, new_issue_description: str, similar_issue: IssueReference, similarity_score: float
    ) -> List[str]:
        """Generate reasons for similarity between issues.

        Args:
            new_issue_title: Title of the new issue
            new_issue_description: Description of the new issue
            similar_issue: Most similar existing issue
            similarity_score: Calculated similarity score

        Returns:
            List of similarity reasons
        """
        reasons = []

        # Check title similarity
        title_similarity = self._calculate_text_similarity(
            self._preprocess_text(new_issue_title), self._preprocess_text(similar_issue.title)
        )

        if title_similarity > 0.5:
            reasons.append(f"Similar titles (similarity: {title_similarity:.2f})")

        # Check description similarity
        if new_issue_description and similar_issue.description:
            desc_similarity = self._calculate_text_similarity(
                self._preprocess_text(new_issue_description), self._preprocess_text(similar_issue.description)
            )

            if desc_similarity > 0.3:
                reasons.append(f"Similar descriptions (similarity: {desc_similarity:.2f})")

        # Check for common keywords
        new_words = set(self._preprocess_text(f"{new_issue_title} {new_issue_description}").split())
        existing_words = set(self._preprocess_text(f"{similar_issue.title} {similar_issue.description}").split())

        common_words = new_words.intersection(existing_words)
        if len(common_words) > 3:  # If more than 3 common words
            important_words = [word for word in common_words if len(word) > 3]  # Filter short words
            if important_words:
                reasons.append(f"Common keywords: {', '.join(list(important_words)[:5])}")

        # Overall similarity assessment
        if similarity_score > 0.8:
            reasons.append("Very high overall similarity score")
        elif similarity_score > 0.6:
            reasons.append("High overall similarity score")
        elif similarity_score > 0.4:
            reasons.append("Moderate overall similarity score")

        return reasons

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings.

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Similarity score between 0 and 1
        """
        if not text1 or not text2:
            return 0.0

        try:
            # Create a temporary vectorizer for this comparison
            temp_vectorizer = TfidfVectorizer(stop_words="english", lowercase=True)
            tfidf_matrix = temp_vectorizer.fit_transform([text1, text2])
            similarity_matrix = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            return float(similarity_matrix[0][0])
        except:
            return 0.0

    def batch_detect_duplicates(
        self, new_issues: List[dict], existing_issues: List[IssueReference]
    ) -> List[DuplicateDetectionResult]:
        """Detect duplicates for multiple new issues at once (optimized batch processing).

        Args:
            new_issues: List of dictionaries with 'title' and 'description' keys
            existing_issues: List of existing issues to compare against

        Returns:
            List of duplicate detection results
        """
        if not new_issues:
            return []

        # Filter only open issues
        open_issues = [issue for issue in existing_issues if issue.status.lower() == "open"]

        if not open_issues:
            # Return non-duplicate results for all issues
            return [
                DuplicateDetectionResult(
                    is_duplicate=False,
                    duplicate_of=None,
                    similarity_score=0.0,
                    similarity_reasons=[],
                    confidence_score=1.0,
                    recommendation="No open issues to compare against. This appears to be a new issue.",
                )
                for _ in new_issues
            ]

        try:
            # Prepare texts for all new issues
            new_issue_texts = [
                self._combine_new_issue_text(issue.get("title", ""), issue.get("description", "")) for issue in new_issues
            ]

            # Prepare texts for existing issues
            existing_texts = [self._combine_issue_text(issue) for issue in open_issues]

            # Combine all texts for vectorization
            all_texts = new_issue_texts + existing_texts

            # Vectorize all texts at once
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)

            # Split into new and existing matrices
            num_new = len(new_issues)
            new_vectors = tfidf_matrix[:num_new]
            existing_vectors = tfidf_matrix[num_new:]

            # Calculate similarities between all new issues and all existing issues
            # This creates a matrix where rows are new issues and columns are existing issues
            similarities_matrix = cosine_similarity(new_vectors, existing_vectors)

            # Process each new issue
            results = []
            for i, new_issue in enumerate(new_issues):
                similarities = similarities_matrix[i]

                # Find the most similar issue
                max_similarity_idx = np.argmax(similarities)
                max_similarity_score = float(similarities[max_similarity_idx])
                most_similar_issue = open_issues[max_similarity_idx]

                # Determine if it's a duplicate
                is_duplicate = max_similarity_score >= self.similarity_threshold

                # Calculate confidence score
                confidence_score = min(max_similarity_score * 1.2, 1.0)  # Boost confidence slightly
                if max_similarity_score < 0.3:
                    confidence_score = max_similarity_score  # Low similarity = low confidence

                # Generate similarity reasons
                similarity_reasons = self._calculate_similarity_reasons(
                    new_issue.get("title", ""),
                    new_issue.get("description", ""),
                    most_similar_issue,
                    max_similarity_score,
                )

                # Generate recommendation
                if is_duplicate:
                    recommendation = (
                        f"This issue appears to be a duplicate of issue {most_similar_issue.issue_id}. "
                        f"Consider linking to the original issue and closing this one."
                    )
                elif max_similarity_score > 0.5:
                    recommendation = (
                        f"This issue shows moderate similarity to issue {most_similar_issue.issue_id}. "
                        f"Review both issues to determine if they are related or should be merged."
                    )
                else:
                    recommendation = "This appears to be a new, unique issue."

                result = DuplicateDetectionResult(
                    is_duplicate=is_duplicate,
                    duplicate_of=most_similar_issue if is_duplicate else None,
                    similarity_score=max_similarity_score,
                    similarity_reasons=similarity_reasons,
                    confidence_score=confidence_score,
                    recommendation=recommendation,
                )

                results.append(result)

            return results

        except Exception as e:
            # Fallback results if analysis fails
            return [
                DuplicateDetectionResult(
                    is_duplicate=False,
                    duplicate_of=None,
                    similarity_score=0.0,
                    similarity_reasons=[],
                    confidence_score=0.0,
                    recommendation=f"Unable to perform similarity analysis due to error: {str(e)}. Manual review required.",
                )
                for _ in new_issues
            ]

    def find_most_similar_issues_batch(
        self, new_issues: List[dict], existing_issues: List[IssueReference], top_k: int = 5
    ) -> List[List[Tuple[IssueReference, float]]]:
        """Find the top-k most similar issues for each new issue (batch processing).

        Args:
            new_issues: List of dictionaries with 'title' and 'description' keys
            existing_issues: List of existing issues to compare against
            top_k: Number of most similar issues to return per new issue

        Returns:
            List of lists of tuples (issue, similarity_score) for each new issue
        """
        if not new_issues or not existing_issues:
            return [[] for _ in new_issues]

        try:
            # Prepare texts for all new issues
            new_issue_texts = [
                self._combine_new_issue_text(issue.get("title", ""), issue.get("description", "")) for issue in new_issues
            ]

            # Prepare texts for existing issues
            existing_texts = [self._combine_issue_text(issue) for issue in existing_issues]

            # Combine all texts for vectorization
            all_texts = new_issue_texts + existing_texts

            # Vectorize all texts at once
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)

            # Split into new and existing matrices
            num_new = len(new_issues)
            new_vectors = tfidf_matrix[:num_new]
            existing_vectors = tfidf_matrix[num_new:]

            # Calculate similarities between all new issues and all existing issues
            similarities_matrix = cosine_similarity(new_vectors, existing_vectors)

            # Process each new issue
            all_results = []
            for i in range(num_new):
                similarities = similarities_matrix[i]

                # Get top-k most similar issues
                top_indices = np.argsort(similarities)[::-1][:top_k]  # Sort descending, take top-k

                results = []
                for idx in top_indices:
                    similarity_score = float(similarities[idx])
                    if similarity_score > 0.0:  # Only include issues with some similarity
                        results.append((existing_issues[idx], similarity_score))

                all_results.append(results)

            return all_results

        except Exception:
            return [[] for _ in new_issues]
