"""
Email Translation QA Tool - Streamlit UI (Advanced with Email Viewer & Mapping)
Multi-language, multi-brand email comparison with side-by-side comparison, test tagging, and email viewer
"""

import streamlit as st
import pandas as pd
import tempfile
import os
from io import StringIO
import json
from datetime import datetime

from src.email_qa import (
    EMLParser, ExcelTranslationReader, SectionComparator, QAReportGenerator
)
from src.email_viewer import EmailViewer

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
        font-size: 0.85em;
    }
    .email-viewer-frame {
        border: 1px solid #ccc;
        border-radius: 0.5em;
        background-color: #f0f0f0;
        padding: 0;
    }
    .side-by-side {
        display: flex;
        gap: 2em;
    }
    .comparison-column {
        flex: 1;
        border: 1px solid #ddd;
        padding: 1em;
        border-radius: 0.5em;
        background-color: #fafafa;
    }
    .tag-badge {
        display: inline-block;
        background-color: #007bff;
        color: white;
        padding: 0.3em 0.6em;
        border-radius: 0.25em;
        font-size: 0.85em;
        margin-right: 0.5em;
        margin-bottom: 0.5em;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="header">📧 Email Translation QA Tool</p>', unsafe_allow_html=True)
st.markdown("Compare multilingual email templates across brands and reservation types with live email preview")

# Initialize session state
if 'uploaded_emails' not in st.session_state:
    st.session_state.uploaded_emails = []
if 'uploaded_excel' not in st.session_state:
    st.session_state.uploaded_excel = None
if 'test_results' not in st.session_state:
    st.session_state.test_results = []
if 'test_counter' not in st.session_state:
    st.session_state.test_counter = 0
if 'section_mappings' not in st.session_state:
    st.session_state.section_mappings = {}

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
# TAB 1: EMAIL VIEWER & EXCEL PREVIEW WITH MAPPING
# ============================================================================

tab1, tab2, tab3 = st.tabs(["📧 Email Viewer & Translation Data", "🔍 Map & Compare", "📊 Test Dashboard"])

with tab1:
    st.markdown('<p class="subheader">Email Viewer & Translation Base Preview</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📧 Email Files")
        email_names = [f.name for f in st.session_state.uploaded_emails]
        selected_email_idx = st.selectbox(
            "Select email to view",
            range(len(email_names)),
            format_func=lambda i: email_names[i],
            key="email_select"
        )
        
        if selected_email_idx is not None:
            selected_email_file = st.session_state.uploaded_emails[selected_email_idx]
            email_content = selected_email_file.read()
            
            try:
                # Use EmailViewer to render email
                viewer = EmailViewer(file_content=email_content)
                parser = EMLParser(file_content=email_content)
                
                subject = parser.get_subject()
                attachments = viewer.get_attachments_info()
                
                st.markdown(f"**File:** {selected_email_file.name}")
                
                if attachments:
                    st.markdown(f"**Attachments:** {len(attachments)} file(s)")
                    for att in attachments:
                        st.write(f"- {att['filename']} ({att['content_type']}, {att['size']} bytes)")
                
                st.markdown("---")
                st.markdown("### Email Rendered View")
                
                # Display HTML email in iframe
                email_html = viewer.get_full_html()
                st.components.v1.html(email_html, height=700, scrolling=True)
                
                st.session_state.selected_email_content = {
                    'file_name': selected_email_file.name,
                    'subject': subject,
                    'parser': parser,
                    'sections': parser.extract_sections(),
                    'viewer': viewer
                }
                
            except Exception as e:
                st.error(f"Error reading email: {e}")
                import traceback
                st.error(traceback.format_exc())
            
            selected_email_file.seek(0)
    
    with col2:
        st.markdown("### 📋 Translation Base")
        selected_sheet = st.selectbox(
            "Select sheet to preview",
            sheet_names,
            key="sheet_select"
        )
        
        if selected_sheet:
            try:
                df = excel_reader.read_sheet(selected_sheet)
                st.markdown(f"**Sheet:** {selected_sheet}")
                st.markdown(f"**Total Columns:** {len(df.columns)}")
                st.markdown(f"**Total Rows:** {len(df)}")
                
                st.markdown("### Data Preview")
                st.dataframe(df, use_container_width=True, height=500)
                
                st.session_state.excel_data = {
                    'sheet_name': selected_sheet,
                    'dataframe': df,
                    'columns': df.columns.tolist()
                }
            except Exception as e:
                st.error(f"Error reading sheet: {e}")

# ============================================================================
# TAB 2: MAP EMAIL SECTIONS TO EXCEL & COMPARE
# ============================================================================

with tab2:
    st.markdown('<p class="subheader">Map Email Sections to Excel Columns/Rows & Compare</p>', unsafe_allow_html=True)
    
    if st.session_state.selected_email_content is None or st.session_state.excel_data is None:
        st.warning("⚠️ Please select an email and translation sheet in the 'Email Viewer & Translation Data' tab first")
    else:
        email_data = st.session_state.selected_email_content
        excel_data = st.session_state.excel_data
        df = excel_data['dataframe']
        
        st.markdown(f"**Email:** {email_data['file_name']}")
        st.markdown(f"**Translation Sheet:** {excel_data['sheet_name']}")
        st.divider()
        
        # ========== STEP 1: SELECT EMAIL SECTION ==========
        st.markdown("### Step 1️⃣: Select Email Section to Map")
        available_sections = list(email_data['sections'].keys())
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            selected_email_section = st.selectbox(
                "Choose section from email",
                available_sections,
                key="email_section_map",
                help="Select which part of the email to compare"
            )
        
        with col2:
            st.write("")
            st.write("")
            st.markdown(f"**Content Length:** {len(email_data['sections'].get(selected_email_section, ''))} chars")
        
        if selected_email_section:
            email_section_content = email_data['sections'].get(selected_email_section, "")
            st.markdown("**Preview:**")
            st.markdown('<div class="email-preview">' + email_section_content[:500].replace("<", "&lt;").replace(">", "&gt;") + '</div>', unsafe_allow_html=True)
        
        st.divider()
        
        # ========== STEP 2: SELECT EXCEL COLUMN & ROW ==========
        st.markdown("### Step 2️⃣: Select Excel Column & Row to Map")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            selected_excel_column = st.selectbox(
                "Choose column from Excel",
                options=excel_data['columns'],
                key="excel_column_map",
                help="Select which Excel column contains the content to compare"
            )
        
        with col2:
            selected_excel_row = st.selectbox(
                "Choose row from Excel",
                options=range(len(df)),
                format_func=lambda i: f"Row {i+1}",
                key="excel_row_map",
                help="Select which row to compare against"
            )
        
        if selected_excel_column and selected_excel_row is not None:
            excel_section_content = str(df[selected_excel_column].iloc[selected_excel_row])
            st.markdown(f"**Content Length:** {len(excel_section_content)} chars")
            st.markdown("**Preview:**")
            st.markdown('<div class="email-preview">' + excel_section_content[:500].replace("<", "&lt;").replace(">", "&gt;") + '</div>', unsafe_allow_html=True)
        
        st.divider()
        
        # ========== STEP 3: TEST CONFIGURATION & LABELS ==========
        st.markdown("### Step 3️⃣: Test Configuration & Labels")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            test_name = st.text_input(
                "Test Name/Label",
                value=f"{selected_email_section} → {selected_excel_column}",
                help="Give this comparison a meaningful name for the dashboard"
            )
            
            test_tags = st.multiselect(
                "Tags (for filtering in dashboard)",
                options=[
                    "Confirmation", "Check In", "Check Out", "Reservation", "Modification", "Reminder",
                    "The Standard", "Breathless", "Standard X", "Me and All", "Andaz", "Thompson", "Dream",
                    "Hero Section", "Reservation Module", "Contact Module", "WOH Module", "App Module", "Footer"
                ],
                help="Add tags to organize tests in the dashboard"
            )
        
        with col2:
            st.write("")
            run_test = st.button("🚀 Create Comparison", use_container_width=True, key="create_comparison")
        
        if run_test:
            try:
                comparator = SectionComparator(similarity_threshold=similarity_threshold)
                
                result = comparator.compare(
                    expected=excel_section_content,
                    actual=email_section_content,
                    section_name=selected_email_section,
                    language="en",
                    brand="mapped",
                    reservation_type="mapped",
                    file_name=email_data['file_name']
                )
                
                # Store test result with tags and mapping info
                test_result = {
                    'id': st.session_state.test_counter,
                    'timestamp': datetime.now().isoformat(),
                    'test_name': test_name,
                    'tags': test_tags,
                    'email_file': email_data['file_name'],
                    'email_section': selected_email_section,
                    'excel_sheet': excel_data['sheet_name'],
                    'excel_column': selected_excel_column,
                    'excel_row': selected_excel_row + 1,
                    'result': result
                }
                
                st.session_state.test_results.append(test_result)
                st.session_state.test_counter += 1
                
                st.success("✓ Comparison created and saved to dashboard!")
                
                # ========== SIDE-BY-SIDE COMPARISON DISPLAY ==========
                st.markdown("---")
                st.markdown("### 📊 Side-by-Side Comparison")
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown(f"#### 📧 Email Section: {selected_email_section}")
                    st.markdown('<div class="email-preview">' + email_section_content.replace("<", "&lt;").replace(">", "&gt;") + '</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"#### 📋 Excel Column: {selected_excel_column} (Row {selected_excel_row + 1})")
                    st.markdown('<div class="email-preview">' + excel_section_content.replace("<", "&lt;").replace(">", "&gt;") + '</div>', unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Results metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    status_text = "✓ PASS" if result.status == "PASS" else "✗ FAIL"
                    st.metric("Status", status_text)
                
                with col2:
                    st.metric("Similarity", f"{result.similarity * 100:.1f}%")
                
                with col3:
                    st.metric("Test Label", test_name[:20] + "..." if len(test_name) > 20 else test_name)
                
                with col4:
                    if test_tags:
                        st.write("**Tags:**")
                        for tag in test_tags:
                            st.markdown(f'<span class="tag-badge">{tag}</span>', unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Error creating comparison: {e}")
                import traceback
                st.error(traceback.format_exc())

# ============================================================================
# TAB 3: TEST DASHBOARD WITH FILTERING
# ============================================================================

with tab3:
    st.markdown('<p class="subheader">Test Dashboard & Results</p>', unsafe_allow_html=True)
    
    if not st.session_state.test_results:
        st.info("💡 Create comparisons in the 'Map & Compare' tab to see results here")
    else:
        # Summary metrics
        total_tests = len(st.session_state.test_results)
        passed_tests = sum(1 for t in st.session_state.test_results if t['result'].status == "PASS")
        failed_tests = sum(1 for t in st.session_state.test_results if t['result'].status == "FAIL")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Tests", total_tests)
        with col2:
            st.metric("✓ Passed", passed_tests)
        with col3:
            st.metric("✗ Failed", failed_tests)
        with col4:
            pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
            st.metric("Pass Rate", f"{pass_rate:.1f}%")
        
        st.divider()
        
        # Filter by tags
        st.markdown("### Filter Results")
        
        all_tags = set()
        for test in st.session_state.test_results:
            all_tags.update(test['tags'])
        
        filter_tags = st.multiselect(
            "Filter by tags",
            sorted(list(all_tags)),
            help="Select tags to filter the results"
        )
        
        # Apply tag filter
        filtered_tests = st.session_state.test_results
        if filter_tags:
            filtered_tests = [
                t for t in st.session_state.test_results
                if any(tag in t['tags'] for tag in filter_tags)
            ]
        
        st.markdown(f"### Showing {len(filtered_tests)} test(s)")
        
        st.divider()
        
        # Display each test result
        for test in filtered_tests:
            result = test['result']
            status_icon = "✓" if result.status == "PASS" else "✗"
            status_color = "pass" if result.status == "PASS" else "fail"
            
            with st.expander(
                f"{status_icon} {test['test_name']} | "
                f"Similarity: {result.similarity * 100:.1f}% | "
                f"📧 {test['email_file']}",
                expanded=False
            ):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown("**Test Details:**")
                    st.write(f"- **Test ID:** {test['id']}")
                    st.write(f"- **Timestamp:** {test['timestamp']}")
                    st.write(f"- **Email:** {test['email_file']}")
                    st.write(f"- **Email Section:** {test['email_section']}")
                    st.write(f"- **Excel Sheet:** {test['excel_sheet']}")
                    st.write(f"- **Excel Column:** {test['excel_column']} (Row {test['excel_row']})")
                
                with col2:
                    st.markdown("**Status:**")
                    st.markdown(f'<span class="{status_color}">{result.status}</span>', unsafe_allow_html=True)
                    st.write(f"Similarity: {result.similarity * 100:.1f}%")
                
                with col3:
                    st.markdown("**Tags:**")
                    if test['tags']:
                        for tag in test['tags']:
                            st.markdown(f'<span class="tag-badge">{tag}</span>', unsafe_allow_html=True)
                    else:
                        st.write("No tags")
                
                st.markdown("---")
                
                # Side-by-side view
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Email Section: {test['email_section']}**")
                    st.markdown('<div class="email-preview">' + result.actual[:800].replace("<", "&lt;").replace(">", "&gt;") + '</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"**Excel: {test['excel_column']} (Row {test['excel_row']})**")
                    st.markdown('<div class="email-preview">' + result.expected[:800].replace("<", "&lt;").replace(">", "&gt;") + '</div>', unsafe_allow_html=True)
        
        st.divider()
        
        # Export options
        st.markdown("### Export Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Export as JSON
            export_data = {
                'summary': {
                    'total': total_tests,
                    'passed': passed_tests,
                    'failed': failed_tests,
                    'pass_rate': f"{(passed_tests / total_tests * 100) if total_tests > 0 else 0:.1f}%"
                },
                'tests': [
                    {
                        'id': t['id'],
                        'test_name': t['test_name'],
                        'timestamp': t['timestamp'],
                        'tags': t['tags'],
                        'email_file': t['email_file'],
                        'email_section': t['email_section'],
                        'excel_sheet': t['excel_sheet'],
                        'excel_column': t['excel_column'],
                        'excel_row': t['excel_row'],
                        'status': t['result'].status,
                        'similarity': f"{t['result'].similarity * 100:.1f}%"
                    }
                    for t in filtered_tests
                ]
            }
            json_str = json.dumps(export_data, indent=2)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col2:
            # Export as CSV
            export_df = pd.DataFrame([
                {
                    'Test ID': t['id'],
                    'Test Name': t['test_name'],
                    'Timestamp': t['timestamp'],
                    'Tags': ', '.join(t['tags']),
                    'Email File': t['email_file'],
                    'Email Section': t['email_section'],
                    'Excel Sheet': t['excel_sheet'],
                    'Excel Column': t['excel_column'],
                    'Excel Row': t['excel_row'],
                    'Status': t['result'].status,
                    'Similarity': f"{t['result'].similarity * 100:.1f}%"
                }
                for t in filtered_tests
            ])
            csv_str = export_df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv_str,
                file_name=f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col3:
            if st.button("🔄 Clear All Results", use_container_width=True):
                st.session_state.test_results = []
                st.session_state.test_counter = 0
                st.rerun()

# Cleanup
try:
    os.unlink(excel_path)
except:
    pass

st.markdown("---")
st.markdown("### About")
st.markdown("""
**Email Translation QA Tool** helps you validate multilingual email templates by:
1. **View** - See emails rendered as they appear in email clients
2. **Select** - Preview Excel translation data
3. **Map** - Select specific email sections and map them to Excel columns/rows
4. **Compare** - Create side-by-side comparisons with custom labels and tags
5. **Dashboard** - View all tests with filtering, sorting, and export options

Each comparison creates a test result with custom labels and tags for easy organization and reporting!
""")
