"""
Email Translation QA Tool - Backend
Complete rewrite for multilingual email comparison across brands and reservation types
"""

import email
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class EmailSection:
    """Represents a section of an email"""
    name: str
    content: str
    language: str = "en"


@dataclass
class ComparisonResult:
    """Result of comparing email section to expected translation"""
    section_name: str
    language: str
    brand: str
    reservation_type: str
    file_name: str
    expected: str
    actual: str
    match: bool
    similarity: float
    status: str  # "PASS", "FAIL", "MISSING"


class EMLParser:
    """Parse EML files and extract structured sections"""
    
    SECTION_MARKERS = {
        'subject': 'Subject',
        'hero_section': 'Hero Section',
        'reservation_module': 'Reservation Module',
        'contact_module': 'Contact Module',
        'woh_module': 'WOH Module',
        'app_module': 'App Module',
        'need_to_make_change': 'Need to make change',
        'footer_links': 'Footer links',
        'footer_copy': 'Footer copy',
    }
    
    def __init__(self, file_path: Optional[str] = None, file_content: Optional[bytes] = None):
        if file_path:
            with open(file_path, 'rb') as f:
                self.message = email.message_from_binary_file(f)
        elif file_content:
            self.message = email.message_from_bytes(file_content)
        else:
            raise ValueError("Either file_path or file_content must be provided")
    
    def get_subject(self) -> str:
        """Extract email subject"""
        return self.message.get('Subject', '')
    
    def get_body(self, part_type: str = 'text/plain') -> str:
        """Extract email body"""
        body = ""
        if self.message.is_multipart():
            for part in self.message.walk():
                if part.get_content_type() == part_type:
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        body = payload.decode(charset, errors='replace')
                        break
                    except Exception as e:
                        print(f"Error: {e}")
        else:
            try:
                payload = self.message.get_payload(decode=True)
                charset = self.message.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='replace')
            except:
                body = self.message.get_payload()
        return body
    
    def extract_sections(self) -> Dict[str, str]:
        """
        Extract defined sections from email body
        Assumes sections are marked in the email like:
        [SECTION_NAME]
        content here
        [/SECTION_NAME]
        """
        body = self.get_body()
        sections = {'subject': self.get_subject()}
        
        # Try to extract sections based on markers
        for section_key, section_name in self.SECTION_MARKERS.items():
            if section_key == 'subject':
                continue
            
            # Look for [Section Name] ... [/Section Name] pattern
            start_marker = f"[{section_name}]"
            end_marker = f"[/{section_name}]"
            
            if start_marker in body:
                start_idx = body.find(start_marker) + len(start_marker)
                end_idx = body.find(end_marker)
                if end_idx > start_idx:
                    sections[section_key] = body[start_idx:end_idx].strip()
        
        # Fallback: if no marked sections, split by common section patterns
        if len(sections) == 1:
            sections.update(self._extract_sections_by_content(body))
        
        return sections
    
    def _extract_sections_by_content(self, body: str) -> Dict[str, str]:
        """Fallback: extract sections by content patterns"""
        sections = {}
        body_lower = body.lower()
        
        for section_key, section_name in self.SECTION_MARKERS.items():
            if section_key == 'subject':
                continue
            if section_name.lower() in body_lower:
                # Extract text after section name
                idx = body_lower.find(section_name.lower())
                # Get next 200 chars or until next section
                content = body[idx + len(section_name):idx + 500].strip()
                sections[section_key] = content
        
        return sections


class ExcelTranslationReader:
    """Read Excel file with translation data"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.excel_file = pd.ExcelFile(file_path)
        self.sheets = self.excel_file.sheet_names
    
    def get_sheet_names(self) -> List[str]:
        return self.sheets
    
    def read_sheet(self, sheet_name: str) -> pd.DataFrame:
        return pd.read_excel(self.file_path, sheet_name=sheet_name)
    
    def get_translations_by_brand_and_type(self, sheet_name: str) -> Dict:
        """
        Read translations structured as:
        Columns: Section | Brand | Reservation Type | Language | Content
        or
        Columns: Section | Confirmation | CheckIn | CheckOut | Reservation | Modification | Reminder
        (with sub-columns for each language)
        """
        df = self.read_sheet(sheet_name)
        
        translations = {}
        
        # Detect structure
        if 'Section' in df.columns and 'Brand' in df.columns:
            # Structure 1: Long format
            for _, row in df.iterrows():
                section = row.get('Section', '')
                brand = row.get('Brand', '')
                res_type = row.get('Reservation Type', '')
                language = row.get('Language', '')
                content = row.get('Content', '')
                
                key = f"{section}_{brand}_{res_type}_{language}"
                translations[key] = content
        else:
            # Structure 2: Wide format - need to parse differently
            translations = df.to_dict()
        
        return translations


class SectionComparator:
    """Compare email sections with expected translations"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        return ' '.join(str(text).strip().lower().split())
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        import difflib
        norm1 = self.normalize_text(text1)
        norm2 = self.normalize_text(text2)
        if not norm1 or not norm2:
            return 0.0 if norm1 != norm2 else 1.0
        return difflib.SequenceMatcher(None, norm1, norm2).ratio()
    
    def compare(self, expected: str, actual: str, 
                section_name: str, language: str, 
                brand: str, reservation_type: str, 
                file_name: str) -> ComparisonResult:
        """Compare a section"""
        if not actual:
            status = "MISSING"
            match = False
            similarity = 0.0
        else:
            similarity = self.calculate_similarity(expected, actual)
            match = similarity >= self.similarity_threshold
            status = "PASS" if match else "FAIL"
        
        return ComparisonResult(
            section_name=section_name,
            language=language,
            brand=brand,
            reservation_type=reservation_type,
            file_name=file_name,
            expected=expected,
            actual=actual,
            match=match,
            similarity=similarity,
            status=status
        )


class QAReportGenerator:
    """Generate QA reports"""
    
    def __init__(self):
        self.timestamp = datetime.now().isoformat()
    
    def generate_summary(self, results: List[ComparisonResult]) -> Dict:
        """Generate test summary"""
        total = len(results)
        passed = sum(1 for r in results if r.status == "PASS")
        failed = sum(1 for r in results if r.status == "FAIL")
        missing = sum(1 for r in results if r.status == "MISSING")
        
        return {
            'timestamp': self.timestamp,
            'total': total,
            'passed': passed,
            'failed': failed,
            'missing': missing,
            'pass_rate': f"{(passed / total * 100) if total > 0 else 0:.1f}%",
            'summary_status': 'PASS' if failed == 0 and missing == 0 else 'FAIL'
        }
    
    def generate_detailed_report(self, results: List[ComparisonResult]) -> Dict:
        """Generate detailed report grouped by email file"""
        summary = self.generate_summary(results)
        
        # Group by file
        by_file = {}
        for result in results:
            if result.file_name not in by_file:
                by_file[result.file_name] = []
            by_file[result.file_name].append(result)
        
        files_report = []
        for file_name, file_results in by_file.items():
            file_passed = sum(1 for r in file_results if r.status == "PASS")
            file_total = len(file_results)
            
            sections_report = []
            for result in file_results:
                sections_report.append({
                    'section': result.section_name,
                    'language': result.language,
                    'brand': result.brand,
                    'reservation_type': result.reservation_type,
                    'status': result.status,
                    'similarity': f"{result.similarity * 100:.1f}%",
                    'expected_preview': result.expected[:100] + '...' if len(result.expected) > 100 else result.expected,
                    'actual_preview': result.actual[:100] + '...' if len(result.actual) > 100 else result.actual,
                })
            
            files_report.append({
                'file_name': file_name,
                'total': file_total,
                'passed': file_passed,
                'failed': file_total - file_passed,
                'pass_rate': f"{(file_passed / file_total * 100) if file_total > 0 else 0:.1f}%",
                'sections': sections_report
            })
        
        return {
            **summary,
            'files': files_report
        }
