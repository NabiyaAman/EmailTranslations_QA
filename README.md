# Email Translations QA Tool

A Streamlit-based application for comparing EML email files against Excel sheets to expedite QA testing of multilingual emails.

## Features

- Upload EML files to parse email content
- Load Excel sheets with expected translations
- Compare full emails or individual sections
- Visual diff highlighting
- Generate test reports

## Getting Started

### Installation

```bash
pip install -r requirements.txt
```

### Running the App

```bash
streamlit run app.py
```

## Project Structure

```
.
├── app.py                 # Main Streamlit application
├── src/
│   ├── eml_parser.py      # EML file parsing logic
│   ├── excel_reader.py    # Excel file reading logic
│   ├── comparator.py      # Comparison and matching logic
│   └── test_reporter.py   # Test result generation
├── requirements.txt       # Python dependencies
└── README.md             # This file
```
