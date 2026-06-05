"""
Email Translation QA Tool - Streamlit UI (Complete Redesign)
Combined mapping, email section selection, Excel drag-and-drop, and inline results
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
    .section-selector {
        border: 2px solid #007bff;
        padding: 0.5em;
        border-radius: 0.5em;
        background-color: #e7f3ff;
        cursor: pointer;
        margin: 0.5em 0;
        transition: all 0.3s;
    }
    .section-selector:hover {
        background-color: #cce5ff;
        border-color: #0056b3;
    }
    .section-selector.selected {
        background-color: #0056b3;
        color: white;
        border-color: #004085;
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
    .comparison-result {
        padding: 1em;
        border-radius: 0.5em;
        margin: 0.5em 0;
        font-weight: bold;
    }
    .result-pass {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .result-fail {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="header">📧 Email Translation QA Tool</p>', unsafe_allow_html=True)
st.markdown("Select email sections, map to Excel data, and view results inline")

# Initialize session state
if 'uploaded_emails' not in st.session_state:
    st.session_state.uploaded_emails = []
if 'uploaded_excel' not in st.session_state:
    st.session_state.uploaded_excel = None
if 'test_results' not in st.session_state:
    st.session_state.test_results = []
if 'test_counter' not in st.session_state:
    st.session_state.test_counter = 0
if 'selected_email_section' not in st.session_state:
    st.session_state.selected_email_section = None
if 'selected_excel_cell' not in st.session_state:
    st.session_state.selected_excel_cell = None
if 'comparison_df' not in st.session_state:
    st.session_state.comparison_df = None

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
# MAIN TAB - COMBINED MAPPING & COMPARISON
# ============================================================================

st.markdown('<p class="subheader">Email Section Selection & Excel Mapping</p>', unsafe_allow_html=True)

# Top row - Email and Excel selection
col_email_select, col_excel_select = st.columns([1, 1])

with col_email_select:
    st.markdown("### 📧 Select Email File")
    email_names = [f.name for f in st.session_state.uploaded_emails]
    selected_email_idx = st.selectbox(
        "Choose email",
        range(len(email_names)),
        format_func=lambda i: email_names[i],
        key="email_select_main"
    )
    
    selected_email_file = st.session_state.uploaded_emails[selected_email_idx]
    email_content = selected_email_file.read()
    
    try:
        viewer = EmailViewer(file_content=email_content)
        parser = EMLParser(file_content=email_content)
        email_sections = parser.extract_sections()
        
        st.session_state.selected_email_content = {
            'file_name': selected_email_file.name,
            'parser': parser,
            'sections': email_sections,
            'viewer': viewer
        }
    except Exception as e:
        st.error(f"Error reading email: {e}")
    
    selected_email_file.seek(0)

with col_excel_select:
    st.markdown("### 📋 Select Excel Sheet")
    selected_sheet = st.selectbox(
        "Choose sheet",
        sheet_names,
        key="sheet_select_main"
    )
    
    try:
        df = excel_reader.read_sheet(selected_sheet)
        st.session_state.excel_data = {
            'sheet_name': selected_sheet,
            'dataframe': df,
            'columns': df.columns.tolist()
        }
        st.markdown(f"**Rows:** {len(df)} | **Columns:** {len(df.columns)}")
    except Exception as e:
        st.error(f"Error reading sheet: {e}")

st.divider()

# Main comparison area
col1, col2 = st.columns([1, 1])

# ============================================================================
# LEFT COLUMN - EMAIL VIEWER WITH SECTION SELECTION
# ============================================================================

with col1:
    st.markdown("### 📧 Email Viewer - Click to Select Sections")
    
    if st.session_state.selected_email_content:
        email_data = st.session_state.selected_email_content
        
        # Display rendered email
        email_html = email_data['viewer'].get_full_html()
        st.components.v1.html(email_html, height=500, scrolling=True)
        
        st.markdown("---")
        st.markdown("### Available Sections to Select")
        st.markdown("Click on a section to mark it as **Actual** for comparison:")
        
        available_sections = list(email_data['sections'].keys())
        
        for section in available_sections:
            section_content = email_data['sections'][section]
            preview = section_content[:100] + "..." if len(section_content) > 100 else section_content
            
            # Button to select this section
            if st.button(
                f"✓ {section} ({len(section_content)} chars)",
                key=f"select_section_{section}",
                use_container_width=True
            ):
                st.session_state.selected_email_section = {
                    'name': section,
                    'content': section_content
                }
                st.success(f"✓ Selected '{section}' as Actual")
        
        if st.session_state.selected_email_section:
            st.markdown("---")
            st.markdown(f"### ✓ Currently Selected Section: **{st.session_state.selected_email_section['name']}**")
            st.markdown("**Preview:**")
            st.markdown('<div class="email-preview">' + st.session_state.selected_email_section['content'][:500].replace("<", "&lt;").replace(">", "&gt;") + '</div>', unsafe_allow_html=True)

# ============================================================================
# RIGHT COLUMN - EXCEL DATA WITH CELL SELECTION
# ============================================================================

with col2:
    st.markdown("### 📋 Excel Data - Click Cells to Select as Expected")
    st.markdown("Select a cell to mark it as **Expected** for comparison:")
    
    if st.session_state.excel_data:
        excel_data = st.session_state.excel_data
        df = excel_data['dataframe']
        
        # Create interactive Excel view
        col_select, row_select = st.columns([1, 1])
        
        with col_select:
            selected_col = st.selectbox(
                "Select Column",
                options=excel_data['columns'],
                key="excel_col_select"
            )
        
        with row_select:
            selected_row = st.selectbox(
                "Select Row",
                options=range(len(df)),
                format_func=lambda i: f"Row {i+1}",
                key="excel_row_select"
            )
        
        if selected_col and selected_row is not None:
            excel_cell_content = str(df[selected_col].iloc[selected_row])
            
            if st.button(
                f"✓ Select {selected_col} - Row {selected_row+1}",
                use_container_width=True,
                key="confirm_excel_cell"
            ):
                st.session_state.selected_excel_cell = {
                    'column': selected_col,
                    'row': selected_row + 1,
                    'content': excel_cell_content
                }
                st.success(f"✓ Selected '{selected_col}' (Row {selected_row+1}) as Expected")
            
            st.markdown("**Preview:**")
            st.markdown('<div class="email-preview">' + excel_cell_content[:500].replace("<", "&lt;").replace(">", "&gt;") + '</div>', unsafe_allow_html=True)
        
        if st.session_state.selected_excel_cell:
            st.markdown("---")
            st.markdown(f"### ✓ Currently Selected Cell: **{st.session_state.selected_excel_cell['column']} (Row {st.session_state.selected_excel_cell['row']})**")
        
        st.markdown("---")
        st.markdown("### Full Excel Data Preview")
        st.dataframe(df, use_container_width=True, height=300)

st.divider()

# ============================================================================
# COMPARISON & RESULTS SECTION
# ============================================================================

st.markdown("### 🔍 Comparison & Test Creation")

if st.session_state.selected_email_section and st.session_state.selected_excel_cell:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        test_name = st.text_input(
            "Test Name/Label",
            value=f"{st.session_state.selected_email_section['name']} → {st.session_state.selected_excel_cell['column']}",
            help="Give this comparison a meaningful name"
        )
        
        test_tags = st.multiselect(
            "Tags (for filtering)",
            options=[
                "Confirmation", "Check In", "Check Out", "Reservation", "Modification", "Reminder",
                "The Standard", "Breathless", "Standard X", "Me and All", "Andaz", "Thompson", "Dream",
                "Hero Section", "Reservation Module", "Contact Module", "WOH Module", "App Module", "Footer"
            ],
            help="Add tags to organize tests"
        )
    
    with col2:
        st.write("")
        run_comparison = st.button("🚀 Create Test & Compare", use_container_width=True, key="create_test")
    
    if run_comparison:
        try:
            comparator = SectionComparator(similarity_threshold=similarity_threshold)
            
            result = comparator.compare(
                expected=st.session_state.selected_excel_cell['content'],
                actual=st.session_state.selected_email_section['content'],
                section_name=st.session_state.selected_email_section['name'],
                language="en",
                brand="mapped",
                reservation_type="mapped",
                file_name=st.session_state.selected_email_content['file_name']
            )
            
            # Store test result
            test_result = {
                'id': st.session_state.test_counter,
                'timestamp': datetime.now().isoformat(),
                'test_name': test_name,
                'tags': test_tags,
                'email_file': st.session_state.selected_email_content['file_name'],
                'actual_section': st.session_state.selected_email_section['name'],
                'expected_column': st.session_state.selected_excel_cell['column'],
                'expected_row': st.session_state.selected_excel_cell['row'],
                'result': result
            }
            
            st.session_state.test_results.append(test_result)
            st.session_state.test_counter += 1
            
            st.success("✓ Test created successfully!")
            
            # Display results
            st.markdown("---")
            st.markdown("### 📊 Comparison Results")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("#### 📧 Actual (Email Section)")
                st.markdown(f"**Section:** {st.session_state.selected_email_section['name']}")
                st.markdown('<div class="email-preview">' + st.session_state.selected_email_section['content'].replace("<", "&lt;").replace(">", "&gt;") + '</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown("#### 📋 Expected (Excel Cell)")
                st.markdown(f"**Column:** {st.session_state.selected_excel_cell['column']} | **Row:** {st.session_state.selected_excel_cell['row']}")
                st.markdown('<div class="email-preview">' + st.session_state.selected_excel_cell['content'].replace("<", "&lt;").replace(">", "&gt;") + '</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Results metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                status_text = "✓ PASS" if result.status == "PASS" else "✗ FAIL"
                st.metric("Status", status_text)
            
            with col2:
                st.metric("Similarity", f"{result.similarity * 100:.1f}%")
            
            with col3:
                st.metric("Test ID", test_result['id'])
            
            with col4:
                if test_tags:
                    st.write("**Tags:**")
                    for tag in test_tags[:2]:
                        st.markdown(f'<span class="tag-badge">{tag}</span>', unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Error creating test: {e}")
            import traceback
            st.error(traceback.format_exc())
else:
    st.info("👆 Select an email section and an Excel cell to create a comparison")

st.divider()

# ============================================================================
# TEST DASHBOARD - INLINE RESULTS IN EXCEL
# ============================================================================

st.markdown("### 📊 Test Dashboard - Results")

if not st.session_state.test_results:
    st.info("💡 Create comparisons above to see results here")
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
    
    # Create results dataframe for display
    results_data = []
    for test in filtered_tests:
        result = test['result']
        results_data.append({
            'Test ID': test['id'],
            'Test Name': test['test_name'],
            'Email File': test['email_file'],
            'Actual Section': test['actual_section'],
            'Expected Column': test['expected_column'],
            'Expected Row': test['expected_row'],
            'Status': result.status,
            'Similarity': f"{result.similarity * 100:.1f}%",
            'Tags': ', '.join(test['tags']) if test['tags'] else 'None'
        })
    
    results_df = pd.DataFrame(results_data)
    
    st.markdown("### Results Table with Inline Status")
    st.dataframe(results_df, use_container_width=True)
    
    st.divider()
    
    # Detailed view for each test
    st.markdown("### Detailed Test Results")
    
    for test in filtered_tests:
        result = test['result']
        status_icon = "✓" if result.status == "PASS" else "✗"
        status_color = "result-pass" if result.status == "PASS" else "result-fail"
        
        with st.expander(
            f"{status_icon} {test['test_name']} | "
            f"Similarity: {result.similarity * 100:.1f}%",
            expanded=False
        ):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📧 Actual Content (Email)")
                st.markdown(f"**Section:** {test['actual_section']}")
                st.markdown('<div class="email-preview">' + result.actual[:800].replace("<", "&lt;").replace(">", "&gt;") + '</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown("#### 📋 Expected Content (Excel)")
                st.markdown(f"**Column:** {test['expected_column']} (Row {test['expected_row']})")
                st.markdown('<div class="email-preview">' + result.expected[:800].replace("<", "&lt;").replace(">", "&gt;") + '</div>', unsafe_allow_html=True)
            
            st.markdown(f'<div class="comparison-result {status_color}">Status: {result.status} | Similarity: {result.similarity * 100:.1f}%</div>', unsafe_allow_html=True)
    
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
                    'actual_section': t['actual_section'],
                    'expected_column': t['expected_column'],
                    'expected_row': t['expected_row'],
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
        csv_str = results_df.to_csv(index=False)
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
**Email Translation QA Tool** - Complete Redesign:
1. **Email Viewer** - See rendered email with clickable sections
2. **Section Selection** - Click any section to mark as "Actual"
3. **Excel Mapping** - Select column and row to mark as "Expected"
4. **Create Test** - Compare selected sections with custom labels and tags
5. **Dashboard** - View all tests in a table with inline results and detailed comparisons
6. **Export** - Download results as JSON or CSV

All in one unified interface for efficient QA testing!
""")
