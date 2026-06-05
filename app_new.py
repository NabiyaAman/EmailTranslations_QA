"""
Email Translation QA Tool - Streamlit UI
Multi-language, multi-brand email comparison interface
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
    
    st.divider()
    
    # Brand and Reservation Type filters
    st.markdown("### Filters")
    
    brands = [
        'The Standard', 'Breathless', 'Standard X',
        'Me and All', 'Andaz', 'Thompson', 'Dream'
    ]
    selected_brands = st.multiselect(
        "Filter by Brand",
        brands,
        default=brands
    )
    
    reservation_types = [
        'Confirmation', 'Check In', 'Check Out',
        'Reservation', 'Modification', 'Reminder'
    ]
    selected_types = st.multiselect(
        "Filter by Reservation Type",
        reservation_types,
        default=reservation_types
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
# TAB 1: UPLOAD & PREVIEW
# ============================================================================

tab1, tab2, tab3 = st.tabs(["📤 Upload & Preview", "🔍 Section Comparison", "📊 Results"])

with tab1:
    st.markdown('<p class="subheader">Uploaded Emails & Translation Base Preview</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Uploaded Email Files")
        for idx, email_file in enumerate(st.session_state.uploaded_emails, 1):
            try:
                parser = EMLParser(file_content=email_file.read())
                subject = parser.get_subject()
                
                with st.expander(f"📧 {idx}. {email_file.name}", expanded=False):
                    st.markdown(f"**Subject:** {subject}")
                    
                    sections = parser.extract_sections()
                    st.markdown("**Sections Found:**")
                    for section_name, content in sections.items():
                        preview = content[:100] + "..." if len(content) > 100 else content
                        st.markdown(f"- **{section_name}**: {preview}")
                
                email_file.seek(0)  # Reset file pointer
            except Exception as e:
                st.error(f"Error reading {email_file.name}: {e}")
    
    with col2:
        st.markdown("### Translation Base Preview")
        selected_sheet = st.selectbox("Select sheet to preview", sheet_names)
        
        if selected_sheet:
            try:
                df = excel_reader.read_sheet(selected_sheet)
                st.dataframe(df.head(10), use_container_width=True)
                st.markdown(f"**Total rows:** {len(df)}")
            except Exception as e:
                st.error(f"Error reading sheet: {e}")

# ============================================================================
# TAB 2: SECTION COMPARISON
# ============================================================================

with tab2:
    st.markdown('<p class="subheader">Section-by-Section Comparison</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        selected_sheet = st.selectbox(
            "Select translation sheet",
            sheet_names,
            key="comp_sheet"
        )
    
    with col2:
        run_comparison = st.button("🚀 Run Comparison", use_container_width=True)
    
    if run_comparison:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            comparator = SectionComparator(similarity_threshold=similarity_threshold)
            reporter = QAReportGenerator()
            all_results = []
            
            excel_reader_comp = ExcelTranslationReader(excel_path)
            translations = excel_reader_comp.get_translations_by_brand_and_type(selected_sheet)
            
            total_emails = len(st.session_state.uploaded_emails)
            
            for email_idx, email_file in enumerate(st.session_state.uploaded_emails):
                status_text.text(f"Processing: {email_file.name}...")
                
                try:
                    parser = EMLParser(file_content=email_file.read())
                    email_sections = parser.extract_sections()
                    file_name = email_file.name
                    
                    # For each section, compare against translations
                    for section_name, actual_content in email_sections.items():
                        for brand in selected_brands:
                            for res_type in selected_types:
                                # Create key to look up in translations
                                key = f"{section_name}_{brand}_{res_type}_en"
                                expected_content = translations.get(key, "")
                                
                                if expected_content:
                                    result = comparator.compare(
                                        expected=expected_content,
                                        actual=actual_content,
                                        section_name=section_name,
                                        language="en",
                                        brand=brand,
                                        reservation_type=res_type,
                                        file_name=file_name
                                    )
                                    all_results.append(result)
                    
                    email_file.seek(0)
                
                except Exception as e:
                    st.warning(f"Error processing {email_file.name}: {e}")
                
                progress_bar.progress((email_idx + 1) / total_emails)
            
            st.session_state.comparison_results = all_results
            status_text.success("✓ Comparison complete!")
            
            # Show summary
            report = reporter.generate_detailed_report(all_results)
            
            st.markdown("---")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Total Tests", report['total'])
            with col2:
                st.metric("✓ Passed", report['passed'])
            with col3:
                st.metric("✗ Failed", report['failed'])
            with col4:
                st.metric("⊘ Missing", report['missing'])
            with col5:
                st.metric("Pass Rate", report['pass_rate'])
            
            st.markdown("---")
            
            # Detailed results per file
            st.markdown("### Results by Email File")
            
            for file_report in report['files']:
                with st.expander(
                    f"📧 {file_report['file_name']} - "
                    f"<span class='pass'>{file_report['passed']}</span>/"
                    f"{file_report['total']}",
                    expanded=False
                ):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Passed", file_report['passed'])
                    with col2:
                        st.metric("Failed", file_report['failed'])
                    with col3:
                        st.metric("Pass Rate", file_report['pass_rate'])
                    
                    st.markdown("#### Section Results")
                    for section in file_report['sections']:
                        status_color = "✓ pass" if section['status'] == "PASS" else "✗ fail" if section['status'] == "FAIL" else "⊘ missing"
                        
                        with st.expander(
                            f"{section['section']} | {section['language']} | "
                            f"{section['brand']} | {section['reservation_type']} | "
                            f"{status_color} | {section['similarity']}",
                            expanded=False
                        ):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("**Expected:**")
                                st.code(section['expected_preview'])
                            
                            with col2:
                                st.markdown("**Actual:**")
                                st.code(section['actual_preview'])
        
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
        st.info("Run comparison in the 'Section Comparison' tab first")
    else:
        reporter = QAReportGenerator()
        report = reporter.generate_detailed_report(st.session_state.comparison_results)
        
        # Summary metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total", report['total'])
        with col2:
            st.metric("Passed", report['passed'])
        with col3:
            st.metric("Failed", report['failed'])
        with col4:
            st.metric("Missing", report['missing'])
        with col5:
            st.metric("Pass Rate", report['pass_rate'])
        
        st.markdown("---")
        
        # Export options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            json_data = json.dumps(report, indent=2)
            st.download_button(
                label="📥 Download JSON Report",
                data=json_data,
                file_name="qa_report.json",
                mime="application/json"
            )
        
        with col2:
            csv_data = pd.DataFrame([
                {
                    'File': result.file_name,
                    'Section': result.section_name,
                    'Language': result.language,
                    'Brand': result.brand,
                    'Reservation Type': result.reservation_type,
                    'Status': result.status,
                    'Similarity': f"{result.similarity * 100:.1f}%"
                }
                for result in st.session_state.comparison_results
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
        st.markdown("### Failed Tests Summary")
        
        failed_results = [r for r in st.session_state.comparison_results if r.status != "PASS"]
        
        if failed_results:
            failed_df = pd.DataFrame([
                {
                    'File': r.file_name,
                    'Section': r.section_name,
                    'Brand': r.brand,
                    'Type': r.reservation_type,
                    'Similarity': f"{r.similarity * 100:.1f}%",
                    'Expected': r.expected[:50] + "..." if len(r.expected) > 50 else r.expected,
                    'Actual': r.actual[:50] + "..." if len(r.actual) > 50 else r.actual,
                }
                for r in failed_results
            ])
            st.dataframe(failed_df, use_container_width=True)
        else:
            st.success("🎉 All tests passed!")

# Cleanup
try:
    os.unlink(excel_path)
except:
    pass

st.markdown("---")
st.markdown("### About")
st.markdown("""
**Email Translation QA Tool** helps you validate multilingual email templates across:
- **9 Brands**: The Standard, Breathless, Standard X, Me and All, Andaz, Thompson, Dream
- **6 Reservation Types**: Confirmation, Check In, Check Out, Reservation, Modification, Reminder
- **Key Sections**: Hero Section, Reservation Module, Contact Module, WOH Module, App Module, Footer
- **10+ Languages**: Compare translations effortlessly

Upload your emails and translation base to get started!
""")
