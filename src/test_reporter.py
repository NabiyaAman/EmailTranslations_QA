"""
Test reporter for generating comparison reports.
"""
import json
from typing import Dict, List
from datetime import datetime


class TestReporter:
    """Generate test reports from comparison results."""

    def __init__(self, test_name: str = "Email QA Test"):
        self.test_name = test_name
        self.timestamp = datetime.now().isoformat()

    def generate_summary(self, results: List) -> Dict:
        """Generate a test summary."""
        passed = sum(1 for r in results if r.match)
        failed = len(results) - passed
        return {
            'test_name': self.test_name,
            'timestamp': self.timestamp,
            'total_sections': len(results),
            'passed': passed,
            'failed': failed,
            'pass_rate': f"{(passed / len(results) * 100) if results else 0:.2f}%",
            'status': 'PASS' if failed == 0 else 'FAIL'
        }

    def generate_detailed_report(self, results: List) -> Dict:
        """Generate a detailed report with section-by-section breakdown."""
        summary = self.generate_summary(results)
        details = []
        for result in results:
            detail = {
                'section': result.section,
                'status': 'PASS' if result.match else 'FAIL',
                'similarity': f"{result.similarity * 100:.2f}%",
                'expected': result.expected[:100] + '...' if len(result.expected) > 100 else result.expected,
                'actual': result.actual[:100] + '...' if len(result.actual) > 100 else result.actual,
                'differences_count': len(result.differences)
            }
            details.append(detail)
        return {**summary, 'details': details}

    def export_json(self, results: List, file_path: str):
        """Export detailed results as JSON."""
        report = self.generate_detailed_report(results)
        with open(file_path, 'w') as f:
            json.dump(report, f, indent=2)

    def export_csv(self, results: List, file_path: str):
        """Export results as CSV."""
        import csv
        with open(file_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['Section', 'Status', 'Similarity', 'Differences'])
            writer.writeheader()
            for result in results:
                writer.writerow({
                    'Section': result.section,
                    'Status': 'PASS' if result.match else 'FAIL',
                    'Similarity': f"{result.similarity * 100:.2f}%",
                    'Differences': len(result.differences)
                })
