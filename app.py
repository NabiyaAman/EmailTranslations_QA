"""
Main Streamlit application for Email Translations QA tool.
"""
import streamlit as st
import tempfile
import os
from io import BytesIO

from src.eml_parser import EMLParser
from src.excel_reader import ExcelReader
from src.comparator import EmailComparator
from src.test_reporter import TestReporter

st.set_page_config(page_title="Email Translations QA", layout="wide")

st.title("📧 Email Translations QA Tool")
st.markdown("""
Compare EML email files against Excel translation sheets to expedite QA testing.
Test full emails or specific sections across multiple languages.
""")

# Sidebar configuration
st.sidebar.header("⚙️ Configuration")
similarity_threshold = st.sidebar.slider(
    "Similarity Threshold",
    min_value=0.0,
    max_value=1.0,
    value=0.85,
    step=0.05,
    help="Minimum similarity score to consider content matching (0.0-1.0)"
)

# Main tabs
tab1, tab2, tab3 = st.tabs(["Full Email Comparison", "Section Comparison", "Batch Testing"])

with tab1:
    st.header("Full Email Comparison")
    st.write("Upload an EML file and Excel sheet to compare the entire email content.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Upload EML File")
        eml_file = st.file_uploader("Choose EML file", type=['eml'], key='tab1_eml')
    
    with col2:
        st.subheader("Upload Excel File")
        excel_file = st.file_uploader("Choose Excel file", type=['xlsx', 'xls'], key='tab1_excel')
    
    if eml_file and excel_file:
        try:
            # Parse EML
            eml_content = eml_file.read()
            parser = EMLParser(file_content=eml_content)
            email_data = parser.get_all_content()
            
            # Read Excel
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                tmp.write(excel_file.read())
                tmp_path = tmp.name
            
            reader = ExcelReader(tmp_path)
            sheet_names = reader.get_sheet_names()
            
            selected_sheet = st.selectbox("Select sheet for comparison", sheet_names)
            
            if selected_sheet:
                section_col, language_col = st.columns(2)
                
                with section_col:
                    section_column = st.text_input("Section column name", value="section")
                
                with language_col:
                    language_columns = st.multiselect(
                        "Language columns",
                        options=[col for col in reader.read_sheet(selected_sheet).columns if col != section_column]
                    )
                
                if st.button("Run Comparison", key='tab1_compare'):
                    try:
                        section_data = reader.get_section_data(
                            selected_sheet,
                            section_column=section_column,
                            language_columns=language_columns if language_columns else None
                        )
                        
                        # Extract sections from email
                        email_sections = parser.extract_sections()
                        
                        # Compare
                        comparator = EmailComparator(similarity_threshold=similarity_threshold)
                        results = comparator.compare_sections(section_data.get('subject', {}), {'subject': email_data['headers']['subject']})
                        
                        reporter = TestReporter(test_name="Full Email Comparison")
                        report = reporter.generate_detailed_report(results)
                        
                        # Display results
                        st.success("Comparison completed!")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Sections", report['total_sections'])
                        with col2:
                            st.metric("Passed", report['passed'], delta=f"{report['pass_rate']}")
                        with col3:
                            st.metric("Failed", report['failed'])
                        with col4:
                            st.metric("Status", report['status'])
                        
                        st.subheader("Detailed Results")
                        for detail in report['details']:
                            with st.expander(f"{detail['section']} - {detail['status']}"):
                                st.write(f"Similarity: {detail['similarity']}")
                                st.write(f"Expected: {detail['expected']}")
                                st.write(f"Actual: {detail['actual']}")
                                st.write(f"Differences: {detail['differences_count']}")
                        
                        # Export options
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Export as JSON"):
                                json_str = str(report).replace("'", '"')
                                st.download_button(
                                    label="Download JSON",
                                    data=json_str,
                                    file_name="comparison_report.json",
                                    mime="application/json"
                                )
                    
                    except Exception as e:
                        st.error(f"Error during comparison: {str(e)}")
            
            # Cleanup
            os.unlink(tmp_path)
        
        except Exception as e:
            st.error(f"Error processing files: {str(e)}")

with tab2:
    st.header("Section Comparison")
    st.write("Compare specific email sections (subject, body, signature, etc.) against expected values.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Upload EML File")
        eml_file_tab2 = st.file_uploader("Choose EML file", type=['eml'], key='tab2_eml')
    
    with col2:
        st.subheader("Manual Section Data")
        section_name = st.text_input("Section name", value="subject")
        expected_text = st.text_area("Expected content")
    
    if eml_file_tab2 and expected_text:
        try:
            eml_content = eml_file_tab2.read()
            parser = EMLParser(file_content=eml_content)
            email_sections = parser.extract_sections()
            
            if st.button("Compare Section", key='tab2_compare'):
                actual_text = email_sections.get(section_name, "")
                
                comparator = EmailComparator(similarity_threshold=similarity_threshold)
                result = comparator.compare_texts(expected_text, actual_text, section_name)
                
                reporter = TestReporter(test_name=f"Section Comparison: {section_name}")
                report = reporter.generate_summary([result])
                
                st.success("Comparison completed!")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Status", report['status'])
                with col2:
                    st.metric("Similarity", f"{result.similarity * 100:.2f}%")
                with col3:
                    st.metric("Differences", len(result.differences))
                
                st.subheader("Content Comparison")
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Expected:**")
                    st.text(expected_text)
                with col2:
                    st.write("**Actual:**")
                    st.text(actual_text)
                
                if result.differences:
                    st.subheader("Differences Found")
                    for diff in result.differences:
                        st.code(diff)
        
        except Exception as e:
            st.error(f"Error: {str(e)}")

with tab3:
    st.header("Batch Testing")
    st.write("Test multiple EML files against an Excel sheet in one go.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Upload EML Files")
        eml_files = st.file_uploader("Choose EML files", type=['eml'], accept_multiple_files=True, key='tab3_eml')
    
    with col2:
        st.subheader("Upload Excel File")
        excel_file_tab3 = st.file_uploader("Choose Excel file", type=['xlsx', 'xls'], key='tab3_excel')
    
    if eml_files and excel_file_tab3:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                tmp.write(excel_file_tab3.read())
                tmp_path = tmp.name
            
            reader = ExcelReader(tmp_path)
            sheet_names = reader.get_sheet_names()
            selected_sheet = st.selectbox("Select sheet", sheet_names, key='tab3_sheet')
            
            if st.button("Run Batch Test", key='tab3_compare'):
                progress_bar = st.progress(0)
                results_summary = []
                
                for idx, eml_file in enumerate(eml_files):
                    try:
                        eml_content = eml_file.read()
                        parser = EMLParser(file_content=eml_content)
                        email_sections = parser.extract_sections()
                        
                        section_data = reader.get_section_data(selected_sheet)
                        comparator = EmailComparator(similarity_threshold=similarity_threshold)
                        results = comparator.compare_sections(section_data, email_sections)
                        
                        reporter = TestReporter(test_name=eml_file.name)
                        report = reporter.generate_summary(results)
                        results_summary.append(report)
                        
                        progress_bar.progress((idx + 1) / len(eml_files))
                    
                    except Exception as e:
                        st.warning(f"Error processing {eml_file.name}: {str(e)}")
                
                st.success("Batch testing completed!")
                
                # Summary table
                import pandas as pd
                summary_df = pd.DataFrame([
                    {
                        'File': r['test_name'],
                        'Total': r['total_sections'],
                        'Passed': r['passed'],
                        'Failed': r['failed'],
                        'Pass Rate': r['pass_rate'],
                        'Status': r['status']
                    }
                    for r in results_summary
                ])
                
                st.dataframe(summary_df, use_container_width=True)
            
            os.unlink(tmp_path)
        
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("Created with ❤️ for efficient multilingual email QA testing")
