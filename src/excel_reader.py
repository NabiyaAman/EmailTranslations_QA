"""
Excel file reader for loading comparison data.
"""
import pandas as pd
from typing import Dict, List, Optional


class ExcelReader:
    """Read and parse Excel files containing email translation data."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.excel_file = pd.ExcelFile(file_path)
        self.sheets = self.excel_file.sheet_names

    def get_sheet_names(self) -> List[str]:
        """Get all sheet names in the Excel file."""
        return self.sheets

    def read_sheet(self, sheet_name: str) -> pd.DataFrame:
        """Read a specific sheet."""
        return pd.read_excel(self.file_path, sheet_name=sheet_name)

    def get_translations(self, sheet_name: str, key_column: str = 'key', 
                        value_column: str = 'value') -> Dict[str, str]:
        """Extract key-value translations from a sheet."""
        df = self.read_sheet(sheet_name)
        if key_column not in df.columns or value_column not in df.columns:
            raise ValueError(f"Columns '{key_column}' or '{value_column}' not found")
        return dict(zip(df[key_column], df[value_column]))

    def get_section_data(self, sheet_name: str, section_column: str = 'section',
                        language_columns: Optional[List[str]] = None) -> Dict[str, Dict[str, str]]:
        """Extract section-based translations (multiple languages)."""
        df = self.read_sheet(sheet_name)
        if section_column not in df.columns:
            raise ValueError(f"Section column '{section_column}' not found")
        if language_columns is None:
            language_columns = [col for col in df.columns if col != section_column]
        result = {}
        for _, row in df.iterrows():
            section = str(row[section_column])
            result[section] = {lang: str(row[lang]) for lang in language_columns if lang in df.columns}
        return result

    def get_all_data(self, sheet_name: str) -> pd.DataFrame:
        """Get raw DataFrame for a sheet."""
        return self.read_sheet(sheet_name)
