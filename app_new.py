"""
Email Translation QA Tool - Streamlit UI (Revised)
Multi-language, multi-brand email comparison interface with full email preview
"""

import streamlit as st
import pandas as pd
import tempfile
import os
from io import StringIO
import json

from src.email_qa import (
    EMLParser, ExcelTranslationReader, SectionComparator, QAReportGenerator
)

# Page config
st.set_page_config(
    page_title="Email Translation QA",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
    <style>
    .header {font-size: 2.5em; color: #1f77b4; margin-bottom: 0.5em;}
    .subheader {font-size: 1.5em; color: #333; margin-top: 1em;}
    .section-box {
        border: 1px solid #ddd;
        padding: 1em;
        border-radius: 0.5em;
        background-color: #f9f9f9;
        margin: 1em 0;
    }
    .pass {color: #28a745; font-weight: bold;}
    .fail {color: #dc3545; font-weight: bold;}
    .missing {color: #ffc107; font-weight: bold;}
    .email-preview {
        border: 1px solid #ccc;
        padding: 1em;
        border-radius: 0.5em;
        background-color: #f5f5f5;
        max-height: 600px;
        overflow-y: auto;
        font-family: monospace;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="header">📧 Email Translation QA Tool</p>', unsafe_allow_html=True)
st.markdown("Compare multilingual email templates across brands and reservation types")

# Initialize session state
if 'uploaded_emails' not in st.session_state:
    st.session_state.uploaded_emails = []
if 'uploaded_excel' not in st.session_state:
    st.session_state.uploaded_excel = None
if 'comparison_results' not in st.session_state:
    st.session_state.comparison_results = []
if 'selected_email_content' not in st.session_state:
    st.session_state.selected_email_content = None
if 'excel_data' not in st.session_state:
    st.session_state.excel_data = None

# ============================================================================
# SIDEBAR - FILE UPLOAD
# ============================================================================
with st.sidebar:
    st.markdown('<p class="subheader">📁 File Upload</p>', unsafe_allow_html=True)
    
    st.markdown("### Step 1: Upload Email Files")
    email_files = st.file_uploader(
        "Upload one or more EML files",
        type=['eml'],
        accept_multiple_files=True,
        help="Upload email files to test"
    )
    
    if email_files:
        st.session_state.uploaded_emails = email_files
        st.success(f"✓ {len(email_files)} email(s) uploaded")
    
    st.divider()
    
    st.markdown("### Step 2: Upload Translation Base")
    excel_file = st.file_uploader(
        "Upload Excel file with translations",
        type=['xlsx', 'xls'],
        help="Excel file with expected translations"
    )
    
    if excel_file:
        st.session_state.uploaded_excel = excel_file
        st.success("✓ Translation base uploaded")
    
    st.divider()
    
    st.markdown("### Step 3: Configuration")
    similarity_threshold = st.slider(
        "Similarity Threshold",
        min_value=0.0,
        max_value=1.0,
        value=0.85,
        step=0.05,
        help="Minimum match score (0.0-1.0)"
    )

# ============================================================================
# MAIN CONTENT
# ============================================================================

if not st.session_state.uploaded_emails or not st.session_state.uploaded_excel:
    st.info("👈 Please upload email files and translation base in the sidebar to begin")
    st.stop()

# Read translation file
try:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
        tmp.write(st.session_state.uploaded_excel.read())
        excel_path = tmp.name
    
    excel_reader = ExcelTranslationReader(excel_path)
    sheet_names = excel_reader.get_sheet_names()
except Exception as e:
    st.error(f"Error reading Excel file: {e}")
    st.stop()

# ============================================================================
# TAB 1: EMAIL & EXCEL PREVIEW WITH SECTION MAPPING
# ============================================================================

tab1, tab2, tab3 = st.tabs(["📧 Email & Translation Preview", "🔍 Compare Sections", "📊 Results"])

with tab1:
    st.markdown('<p class="subheader">Step 1: Select Email & View Full Content</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### Email Files")
        email_names = [f.name for f in st.session_state.uploaded_emails]
        selected_email_idx = st.selectbox(
            "Select email to preview",
            range(len(email_names)),
            format_func=lambda i: email_names[i],
            key="email_select"
        )
        
        if selected_email_idx is not None:
            selected_email_file = st.session_state.uploaded_emails[selected_email_idx]
            email_content = selected_email_file.read()
            
            try:
                parser = EMLParser(file_content=email_content)
                subject = parser.get_subject()
                body = parser.get_body()
                
                st.markdown(f"**Subject:** {subject}")
                
                st.markdown("### Full Email Content")
                st.markdown('<div class="email-preview">' + body.replace("<", "&lt;").replace(">", "&gt;") + '</div>', unsafe_allow_html=True)
                
                st.session_state.selected_email_content = {
                    'file_name': selected_email_file.name,
                    'subject': subject,
                    'body': body,
                    'parser': parser,
                    'sections': parser.extract_sections()
                }
                
            except Exception as e:
                st.error(f"Error reading email: {e}")
            
            selected_email_file.seek(0)
    
    with col2:
        st.markdown("### Translation Base")
        selected_sheet = st.selectbox(
            "Select sheet to preview",
            sheet_names,
            key="sheet_select"
        )
        
        if selected_sheet:
            try:
                df = excel_reader.read_sheet(selected_sheet)
                st.markdown(f"**Sheet:** {selected_sheet}")
                st.markdown(f"**Columns:** {', '.join(df.columns.tolist())}")
                st.markdown(f"**Total rows:** {len(df)}")
                
                st.markdown("### Data Preview")
                st.dataframe(df, use_container_width=True)
                
                st.session_state.excel_data = {
                    'sheet_name': selected_sheet,
                    'dataframe': df,
                    'columns': df.columns.tolist()
                }
            except Exception as e:
                st.error(f"Error reading sheet: {e}")

# ============================================================================
# TAB 2: SECTION COMPARISON WITH MANUAL MAPPING
# ============================================================================

with tab2:
    st.markdown('<p class="subheader">Step 2: Map & Compare Email Sections</p>', unsafe_allow_html=True)
    
    if st.session_state.selected_email_content is None or st.session_state.excel_data is None:
        st.warning("⚠️ Please select an email and translation sheet in the 'Email & Translation Preview' tab first")
    else:
        email_data = st.session_state.selected_email_content
        excel_data = st.session_state.excel_data
        df = excel_data['dataframe']
        
        st.markdown(f"**Email:** {email_data['file_name']}")
        st.markdown(f"**Translation Sheet:** {excel_data['sheet_name']}")
        st.divider()
        
        # Show email sections
        st.markdown("### Available Email Sections")
        available_sections = list(email_data['sections'].keys())
        st.info(f"Sections found: {', '.join(available_sections)}")
        
        # Manual section mapping
        st.markdown("### Manual Section Mapping")
        st.markdown("Select which sections to compare from the email:")
        
        # Create checkboxes for each section
        sections_to_compare = {}
        num_cols = 3
        cols = st.columns(num_cols)
        
        for idx, section in enumerate(available_sections):
            with cols[idx % num_cols]:
                checked = st.checkbox(f"✓ {section}", value=True, key=f"section_{section}")
                sections_to_compare[section] = checked
        
        st.divider()
        
        # Column mapping
        st.markdown("### Map Excel Columns to Section")
        st.markdown("For each section selected above, specify which Excel columns contain the expected content:")
        
        column_mapping = {}
        selected_sections = [s for s, checked in sections_to_compare.items() if checked]
        
        for section in selected_sections:
            col1, col2, col3 = st.columns([1, 2, 2])
            
            with col1:
                st.write(f"**{section}**")
            
            with col2:
                # Select which column contains this section's data
                expected_col = st.selectbox(
                    f"Expected content column for '{section}'",
                    options=excel_data['columns'],
                    key=f"expected_col_{section}"
                )
            
            with col3:
                # Optional: filter by specific row/criteria
                filter_info = st.text_input(
                    f"Filter (optional, e.g., Brand='The Standard')",
                    key=f"filter_{section}",
                    placeholder="Leave empty for all rows"
                )
            
            column_mapping[section] = {
                'expected_column': expected_col,
                'filter': filter_info
            }
        
        st.divider()
        
        # Run comparison
        if st.button("🚀 Compare Selected Sections", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                comparator = SectionComparator(similarity_threshold=similarity_threshold)
                all_results = []
                
                total_sections = len(column_mapping)
                
                for idx, (section, mapping) in enumerate(column_mapping.items()):
                    status_text.text(f"Comparing: {section}...")
                    
                    expected_col = mapping['expected_column']
                    actual_content = email_data['sections'].get(section, "")
                    
                    # Get expected content from Excel
                    if expected_col in df.columns:
                        # For now, take first row (you can add filtering logic here)
                        expected_content = str(df[expected_col].iloc[0]) if len(df) > 0 else ""
                        
                        result = comparator.compare(
                            expected=expected_content,
                            actual=actual_content,
                            section_name=section,
                            language="en",
                            brand="selected",
                            reservation_type="selected",
                            file_name=email_data['file_name']
                        )
                        all_results.append(result)
                    
                    progress_bar.progress((idx + 1) / total_sections)
                
                st.session_state.comparison_results = all_results
                status_text.success("✓ Comparison complete!")
                
                # Show results
                st.markdown("---")
                st.markdown("### Comparison Results")
                
                passed = sum(1 for r in all_results if r.status == "PASS")
                failed = sum(1 for r in all_results if r.status == "FAIL")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total", len(all_results))
                with col2:
                    st.metric("✓ Passed", passed)
                with col3:
                    st.metric("✗ Failed", failed)
                
                st.divider()
                
                # Detailed results
                st.markdown("### Section-by-Section Results")
                
                for result in all_results:
                    status_icon = "✓" if result.status == "PASS" else "✗"
                    status_color = "pass" if result.status == "PASS" else "fail"
                    
                    with st.expander(
                        f"{status_icon} {result.section_name} | "
                        f"Similarity: {result.similarity * 100:.1f}%",
                        expanded=result.status != "PASS"
                    ):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**Expected (from Excel):**")
                            st.code(result.expected, language="text")
                        
                        with col2:
                            st.markdown("**Actual (from Email):**")
                            st.code(result.actual, language="text")
                        
                        st.markdown(f"**Similarity Score:** {result.similarity * 100:.1f}%")
                        st.markdown(f"**Status:** <span class='{status_color}'>{result.status}</span>", unsafe_allow_html=True)
            
            except Exception as e:
                st.error(f"Comparison error: {e}")
                import traceback
                st.error(traceback.format_exc())

# ============================================================================
# TAB 3: RESULTS & EXPORT
# ============================================================================

with tab3:
    st.markdown('<p class="subheader">Test Results & Export</p>', unsafe_allow_html=True)
    
    if not st.session_state.comparison_results:
        st.info("Run comparison in the 'Compare Sections' tab first")
    else:
        reporter = QAReportGenerator()
        all_results = st.session_state.comparison_results
        
        passed = sum(1 for r in all_results if r.status == "PASS")
        failed = sum(1 for r in all_results if r.status == "FAIL")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total", len(all_results))
        with col2:
            st.metric("✓ Passed", passed)
        with col3:
            st.metric("✗ Failed", failed)
        with col4:
            pass_rate = (passed / len(all_results) * 100) if all_results else 0
            st.metric("Pass Rate", f"{pass_rate:.1f}%")
        
        st.markdown("---")
        
        # Export options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            report_data = {
                'total': len(all_results),
                'passed': passed,
                'failed': failed,
                'pass_rate': f"{(passed / len(all_results) * 100) if all_results else 0:.1f}%",
                'results': [
                    {
                        'section': r.section_name,
                        'language': r.language,
                        'brand': r.brand,
                        'reservation_type': r.reservation_type,
                        'status': r.status,
                        'similarity': f"{r.similarity * 100:.1f}%",
                        'expected': r.expected,
                        'actual': r.actual
                    }
                    for r in all_results
                ]
            }
            json_data = json.dumps(report_data, indent=2)
            st.download_button(
                label="📥 Download JSON Report",
                data=json_data,
                file_name="qa_report.json",
                mime="application/json"
            )
        
        with col2:
            csv_data = pd.DataFrame([
                {
                    'Section': result.section_name,
                    'Language': result.language,
                    'Status': result.status,
                    'Similarity': f"{result.similarity * 100:.1f}%"
                }
                for result in all_results
            ]).to_csv(index=False)
            
            st.download_button(
                label="📥 Download CSV Report",
                data=csv_data,
                file_name="qa_report.csv",
                mime="text/csv"
            )
        
        with col3:
            if st.button("🔄 Clear Results", use_container_width=True):
                st.session_state.comparison_results = []
                st.rerun()
        
        st.markdown("---")
        
        # All results table
        st.markdown("### All Test Results")
        results_df = pd.DataFrame([
            {
                'Section': r.section_name,
                'Language': r.language,
                'Status': r.status,
                'Similarity': f"{r.similarity * 100:.1f}%",
                'Expected': r.expected[:50] + "..." if len(r.expected) > 50 else r.expected,
                'Actual': r.actual[:50] + "..." if len(r.actual) > 50 else r.actual,
            }
            for r in all_results
        ])
        st.dataframe(results_df, use_container_width=True)

# Cleanup
try:
    os.unlink(excel_path)
except:
    pass

st.markdown("---")
st.markdown("### About")
st.markdown("""
**Email Translation QA Tool** helps you validate multilingual email templates by:
1. **Uploading EML files** - Your email templates
2. **Uploading Excel translations** - Your expected translation base
3. **Manually selecting sections** - Choose which parts to compare
4. **Mapping columns** - Link Excel columns to email sections
5. **Viewing results** - See similarity scores and export reports

Supports all 9 brands and 6 reservation types!
""")
