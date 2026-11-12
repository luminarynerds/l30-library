# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
from app.core.logging import get_logger
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .base_client import NormalizedSearchResult

logger = get_logger(__name__)


@dataclass
class DuplicateGroup:
    primary_result: NormalizedSearchResult
    duplicate_results: List[NormalizedSearchResult] = field(default_factory=list)
    confidence_score: float = 1.0
    match_reason: str = ""

    def merge_metadata(self) -> NormalizedSearchResult:
        merged = NormalizedSearchResult(
            source_id=self.primary_result.source_id,
            source_name=self.primary_result.source_name,
            protocol=self.primary_result.protocol,
            retrieved_at=self.primary_result.retrieved_at,
        )

        all_results = [self.primary_result] + self.duplicate_results

        # Title: use first non-null
        merged.title = next(
            (r.title for r in all_results if r.title), self.primary_result.title
        )

        # Author: use first non-null
        merged.author = next(
            (r.author for r in all_results if r.author), self.primary_result.author
        )

        # ISBN: use first non-null (should be same for duplicates)
        merged.isbn = next(
            (r.isbn for r in all_results if r.isbn), self.primary_result.isbn
        )

        # ISSN: use first non-null
        merged.issn = next(
            (r.issn for r in all_results if r.issn), self.primary_result.issn
        )

        # Publisher: use first non-null
        merged.publisher = next(
            (r.publisher for r in all_results if r.publisher),
            self.primary_result.publisher,
        )

        # Publication year: use first non-null
        merged.publication_year = next(
            (r.publication_year for r in all_results if r.publication_year),
            self.primary_result.publication_year,
        )

        # Description: use longest
        merged.description = max(
            (r.description for r in all_results if r.description),
            key=len,
            default=self.primary_result.description,
        )

        # Subjects: combine and deduplicate
        all_subjects = set()
        for r in all_results:
            if r.subjects:
                all_subjects.update(s.lower() for s in r.subjects)
        merged.subjects = sorted(list(all_subjects))

        # Classifications: use first non-null
        merged.lc_classification = next(
            (r.lc_classification for r in all_results if r.lc_classification),
            self.primary_result.lc_classification,
        )

        merged.dewey_decimal = next(
            (r.dewey_decimal for r in all_results if r.dewey_decimal),
            self.primary_result.dewey_decimal,
        )

        # Extent: use first non-null
        merged.extent = next(
            (r.extent for r in all_results if r.extent), self.primary_result.extent
        )

        # Language: use first non-null
        merged.language = next(
            (r.language for r in all_results if r.language), self.primary_result.language
        )

        # Control numbers: collect from all sources
        control_numbers = [r.control_number for r in all_results if r.control_number]
        merged.control_number = control_numbers[0] if control_numbers else None

        merged.oclc_number = next(
            (r.oclc_number for r in all_results if r.oclc_number),
            self.primary_result.oclc_number,
        )

        # Work type: use first non-null
        merged.work_type = next(
            (r.work_type for r in all_results if r.work_type), self.primary_result.work_type
        )

        # Edition: use first non-null
        merged.edition = next(
            (r.edition for r in all_results if r.edition), self.primary_result.edition
        )

        # Series: use first non-null
        merged.series = next(
            (r.series for r in all_results if r.series), self.primary_result.series
        )

        # Holdings: sum availability
        available = sum(r.available_count or 0 for r in all_results)
        total = sum(r.total_count or 0 for r in all_results)
        merged.available_count = available if available > 0 else None
        merged.total_count = total if total > 0 else None

        # Relevance: average of all scores
        relevance_scores = [r.relevance_score for r in all_results if r.relevance_score]
        merged.relevance_score = (
            sum(relevance_scores) / len(relevance_scores) if relevance_scores else 1.0
        )

        return merged


class DeduplicationEngine:

    # Fuzzy matching thresholds (0.0 to 1.0)
    ISBN_EXACT_THRESHOLD = 1.0
    TITLE_FUZZY_THRESHOLD = 0.85  # High bar for title matching
    AUTHOR_FUZZY_THRESHOLD = 0.80
    COMBINED_THRESHOLD = 0.90  # Multiple matches

    def __init__(self, enable_fuzzy: bool = True, enable_fingerprinting: bool = True):
        self.enable_fuzzy = enable_fuzzy
        self.enable_fingerprinting = enable_fingerprinting
        self.fingerprint_cache: Dict[str, str] = {}

    def deduplicate(self, results: List[NormalizedSearchResult]) -> List[DuplicateGroup]:
        if not results:
            return []

        # Track which results have been assigned to groups
        assigned = set()
        groups: List[DuplicateGroup] = []

        for i, result in enumerate(results):
            if i in assigned:
                continue

            # Create new group with this result as primary
            group = DuplicateGroup(primary_result=result, confidence_score=1.0)

            # Find duplicates for this result
            for j, other in enumerate(results):
                if j <= i or j in assigned:
                    continue

                match_info = self._find_match(result, other)
                if match_info:
                    group.duplicate_results.append(other)
                    group.confidence_score = min(group.confidence_score, match_info[1])
                    group.match_reason = match_info[0]
                    assigned.add(j)

            groups.append(group)
            assigned.add(i)

        return groups

    def merge_groups(self, groups: List[DuplicateGroup]) -> List[NormalizedSearchResult]:
        return [group.merge_metadata() for group in groups]

    def deduplicate_and_merge(
        self, results: List[NormalizedSearchResult]
    ) -> List[NormalizedSearchResult]:
        groups = self.deduplicate(results)
        return self.merge_groups(groups)

    # =========================================================================
    # Match Detection
    # =========================================================================

    def _find_match(
        self, result1: NormalizedSearchResult, result2: NormalizedSearchResult
    ) -> Optional[Tuple[str, float]]:
        # ISBN matching (highest confidence)
        if self._isbn_match(result1, result2):
            return ("isbn_match", 1.0)

        # Fingerprint matching
        if self.enable_fingerprinting and self._fingerprint_match(result1, result2):
            return ("fingerprint_match", 0.95)

        # Combined title + author match
        if self.enable_fuzzy:
            title_sim = self._title_similarity(result1.title, result2.title)
            author_sim = self._author_similarity(result1.author, result2.author)

            # Both title and author match well
            if (
                title_sim >= self.TITLE_FUZZY_THRESHOLD
                and author_sim >= self.AUTHOR_FUZZY_THRESHOLD
            ):
                avg_sim = (title_sim + author_sim) / 2
                if avg_sim >= self.COMBINED_THRESHOLD:
                    return ("title_author_match", avg_sim)

            # Title match only (if very high confidence)
            if title_sim >= 0.95 and result1.isbn and result2.isbn:
                if result1.isbn == result2.isbn:
                    return ("title_isbn_match", title_sim)

        return None

    def _isbn_match(self, result1: NormalizedSearchResult, result2: NormalizedSearchResult) -> bool:
        if not result1.isbn or not result2.isbn:
            return False

        isbn1 = self._normalize_isbn(result1.isbn)
        isbn2 = self._normalize_isbn(result2.isbn)

        return isbn1 == isbn2 if isbn1 and isbn2 else False

    def _normalize_isbn(self, isbn: str) -> Optional[str]:
        if not isbn:
            return None

        normalized = isbn.replace("-", "").replace(" ", "").strip()

        # Valid ISBNs are 10 or 13 digits
        if not normalized.isdigit() or len(normalized) not in (10, 13):
            return None

        return normalized

    # =========================================================================
    # Fingerprinting
    # =========================================================================

    def _fingerprint_match(
        self, result1: NormalizedSearchResult, result2: NormalizedSearchResult
    ) -> bool:
        if not result1.title or not result2.title:
            return False

        fp1 = self._compute_fingerprint(result1.title, result1.author)
        fp2 = self._compute_fingerprint(result2.title, result2.author)

        return fp1 == fp2

    def _compute_fingerprint(self, title: Optional[str], author: Optional[str]) -> str:
        # Extract first letters of each word in title (title fingerprint)
        title_fp = ""
        if title:
            # Keep only alphanumeric characters and spaces
            clean = re.sub(r"[^a-z0-9\s]", "", title.lower())
            words = clean.split()[:5]  # First 5 words max
            title_fp = "".join(w[0] for w in words if w)

        # Extract last name from author
        author_fp = ""
        if author:
            author_clean = re.sub(r"[^a-z\s]", "", author.lower())
            last_word = author_clean.split()[-1] if author_clean.split() else ""
            author_fp = last_word[:3] if last_word else ""

        # Combine and hash
        combined = f"{title_fp}|{author_fp}"
        return hashlib.md5(combined.encode()).hexdigest()[:8]

    # =========================================================================
    # String Similarity (Fuzzy Matching)
    # =========================================================================

    def _title_similarity(self, title1: Optional[str], title2: Optional[str]) -> float:
        if not title1 or not title2:
            return 0.0

        # Normalize titles
        t1 = self._normalize_text(title1)
        t2 = self._normalize_text(title2)

        if not t1 or not t2:
            return 0.0

        # Quick exact match
        if t1 == t2:
            return 1.0

        # Calculate Levenshtein distance
        distance = self._levenshtein_distance(t1, t2)
        max_len = max(len(t1), len(t2))

        if max_len == 0:
            return 1.0

        similarity = 1.0 - (distance / max_len)
        return max(0.0, min(1.0, similarity))

    def _author_similarity(self, author1: Optional[str], author2: Optional[str]) -> float:
        if not author1 or not author2:
            return 0.0

        # Normalize author names
        a1 = self._normalize_text(author1)
        a2 = self._normalize_text(author2)

        if not a1 or not a2:
            return 0.0

        # Quick exact match
        if a1 == a2:
            return 1.0

        # Extract last names and compare
        a1_last = a1.split()[-1] if a1.split() else a1
        a2_last = a2.split()[-1] if a2.split() else a2

        if a1_last == a2_last:
            return 0.9  # High confidence for same last name

        # Full Levenshtein distance
        distance = self._levenshtein_distance(a1, a2)
        max_len = max(len(a1), len(a2))

        if max_len == 0:
            return 1.0

        similarity = 1.0 - (distance / max_len)
        return max(0.0, min(1.0, similarity))

    def _normalize_text(self, text: str) -> str:
        # Convert to lowercase
        text = text.lower()

        # Remove punctuation and extra spaces
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text).strip()

        # Remove common articles and prepositions
        for word in ["a", "an", "the", "and", "or", "in", "on", "at", "to", "from"]:
            text = re.sub(rf"\b{word}\b\s+", "", text)

        return text

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return DeduplicationEngine._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        # Use space-efficient matrix approach
        previous_row = range(len(s2) + 1)

        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # j+1 instead of j since previous_row and current_row are one character longer than s2
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))

            previous_row = current_row

        return previous_row[-1]

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def estimate_deduplication_rate(self, results: List[NormalizedSearchResult]) -> float:
        if not results:
            return 0.0

        groups = self.deduplicate(results)
        total_duplicates = sum(len(g.duplicate_results) for g in groups)

        return total_duplicates / len(results) if results else 0.0
