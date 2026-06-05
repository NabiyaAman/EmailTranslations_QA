"""
Comparator for matching email content against expected translations.
"""
import difflib
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class ComparisonResult:
    """Result of a comparison operation."""
    section: str
    expected: str
    actual: str
    match: bool
    similarity: float
    differences: List[str]


class EmailComparator:
    """Compare email content against expected values."""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison (strip whitespace, lowercase)."""
        return ' '.join(text.strip().lower().split())

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity score between two texts."""
        text1 = self._normalize_text(text1)
        text2 = self._normalize_text(text2)
        return difflib.SequenceMatcher(None, text1, text2).ratio()

    def _get_differences(self, text1: str, text2: str) -> List[str]:
        """Get detailed differences between two texts."""
        differ = difflib.Differ()
        diff = list(differ.compare(text1.splitlines(), text2.splitlines()))
        return [line for line in diff if line.startswith('- ') or line.startswith('+ ')]

    def compare_texts(self, expected: str, actual: str, section: str = 'content') -> ComparisonResult:
        """Compare two text blocks."""
        similarity = self._calculate_similarity(expected, actual)
        match = similarity >= self.similarity_threshold
        differences = self._get_differences(expected, actual) if not match else []
        return ComparisonResult(
            section=section,
            expected=expected,
            actual=actual,
            match=match,
            similarity=similarity,
            differences=differences
        )

    def compare_sections(self, expected_sections: Dict[str, str], 
                        actual_sections: Dict[str, str]) -> List[ComparisonResult]:
        """Compare multiple sections."""
        results = []
        for section_name, expected_content in expected_sections.items():
            actual_content = actual_sections.get(section_name, '')
            result = self.compare_texts(expected_content, actual_content, section_name)
            results.append(result)
        return results

    def generate_report(self, results: List[ComparisonResult]) -> Dict:
        """Generate a summary report from comparison results."""
        passed = sum(1 for r in results if r.match)
        total = len(results)
        return {
            'total_sections': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': (passed / total * 100) if total > 0 else 0,
            'average_similarity': sum(r.similarity for r in results) / total if total > 0 else 0,
            'results': [
                {
                    'section': r.section,
                    'status': 'PASS' if r.match else 'FAIL',
                    'similarity': round(r.similarity * 100, 2),
                }
                for r in results
            ]
        }
