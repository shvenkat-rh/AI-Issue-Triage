"""Streamlit app for Gemini Issue Analyzer."""

import streamlit as st
import json
from datetime import datetime
from gemini_analyzer import GeminiIssueAnalyzer
from models import IssueType, Severity


def format_code_location(location):
    """Format code location for display."""
    parts = []
    if location.file_path:
        parts.append(f"**File:** `{location.file_path}`")
    if location.line_number:
        parts.append(f"**Line:** {location.line_number}")
    if location.class_name:
        parts.append(f"**Class:** `{location.class_name}`")
    if location.function_name:
        parts.append(f"**Function:** `{location.function_name}`")
    return " | ".join(parts) if parts else "Location not specified"


def display_analysis_results(analysis):
    """Display the analysis results in a structured format."""
    
    # Header with issue type and severity
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.header(f"{analysis.title}")
    
    with col2:
        # Issue type badge
        st.markdown(f"**Type:** {analysis.issue_type.value.title()}")
    
    with col3:
        # Severity badge
        st.markdown(f"**Severity:** {analysis.severity.value.title()}")
    
    # Confidence score
    st.progress(analysis.confidence_score, text=f"Confidence Score: {analysis.confidence_score:.1%}")
    
    # Analysis Summary
    st.subheader("Analysis Summary")
    st.write(analysis.analysis_summary)
    
    # Root Cause Analysis
    st.subheader("Root Cause Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Primary Cause:**")
        st.info(analysis.root_cause_analysis.primary_cause)
        
        if analysis.root_cause_analysis.contributing_factors:
            st.markdown("**Contributing Factors:**")
            for factor in analysis.root_cause_analysis.contributing_factors:
                st.markdown(f"• {factor}")
    
    with col2:
        if analysis.root_cause_analysis.affected_components:
            st.markdown("**Affected Components:**")
            for component in analysis.root_cause_analysis.affected_components:
                st.markdown(f"• `{component}`")
        
        if analysis.root_cause_analysis.related_code_locations:
            st.markdown("**Related Code Locations:**")
            for location in analysis.root_cause_analysis.related_code_locations:
                st.markdown(f"• {format_code_location(location)}")
    
    # Proposed Solutions
    st.subheader("Proposed Solutions")
    
    for i, solution in enumerate(analysis.proposed_solutions, 1):
        with st.expander(f"Solution {i}: {solution.description}", expanded=i == 1):
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**Description:**")
                st.write(solution.description)
                
                st.markdown("**Rationale:**")
                st.write(solution.rationale)
            
            with col2:
                st.markdown("**Location:**")
                st.markdown(format_code_location(solution.location))
            
            st.markdown("**Proposed Code Changes:**")
            st.code(solution.code_changes, language="python")


def export_analysis(analysis):
    """Export analysis to JSON format."""
    return json.dumps(analysis.model_dump(), indent=2, default=str)


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Gemini Issue Analyzer",
        page_icon="G",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("Gemini Issue Analyzer")
    st.markdown("*AI-powered issue analysis for your codebase using Google Gemini*")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # API Key input
        api_key = st.text_input(
            "Gemini API Key",
            type="password",
            help="Enter your Google Gemini API key. Get one from https://makersuite.google.com/app/apikey"
        )
        
        if not api_key:
            st.warning("Please enter your Gemini API key to continue.")
            st.stop()
        
        st.divider()
        
        # Source path configuration
        st.header("Source Configuration")
        
        source_path = st.text_input(
            "Source of Truth Path",
            value="repomix-output.txt",
            help="Path to your codebase file (default: repomix-output.txt)"
        )
        
        custom_prompt_path = st.text_input(
            "Custom Prompt Path (Optional)",
            value="",
            help="Path to custom prompt template file (leave empty for default prompt)"
        )
        
        # File info
        try:
            with open(source_path, "r") as f:
                content = f.read()
                lines = len(content.split('\n'))
                chars = len(content)
            
            st.metric("Total Lines", f"{lines:,}")
            st.metric("Total Characters", f"{chars:,}")
            st.success("Codebase loaded successfully")
        except FileNotFoundError:
            st.error(f"Source file '{source_path}' not found!")
            st.info("Make sure the file path is correct and the file exists.")
            st.stop()
        except Exception as e:
            st.error(f"Error reading source file: {str(e)}")
            st.stop()
    
    # Main interface
    st.header("Issue Details")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        title = st.text_input(
            "Issue Title",
            placeholder="Enter a descriptive title for the issue",
            help="Provide a clear, concise title that summarizes the issue"
        )
    
    with col2:
        analysis_mode = st.selectbox(
            "Analysis Mode",
            ["Comprehensive", "Quick", "Deep Dive"],
            help="Choose the depth of analysis"
        )
    
    issue_description = st.text_area(
        "Issue Description",
        height=200,
        placeholder="Describe the issue in detail. Include:\n• What is the expected behavior?\n• What actually happens?\n• Steps to reproduce\n• Any error messages\n• Environment details",
        help="Provide as much context as possible for better analysis"
    )
    
    # Analysis button
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        analyze_button = st.button(
            "Analyze Issue",
            type="primary",
            disabled=not (title and issue_description),
            use_container_width=True
        )
    
    with col2:
        if st.button("Clear Form", use_container_width=True):
            st.rerun()
    
    # Perform analysis
    if analyze_button and title and issue_description:
        with st.spinner("Analyzing issue with Gemini AI..."):
            try:
                analyzer = GeminiIssueAnalyzer(
                    api_key=api_key, 
                    source_path=source_path,
                    custom_prompt_path=custom_prompt_path if custom_prompt_path.strip() else None
                )
                analysis = analyzer.analyze_issue(title, issue_description)
                
                # Store in session state
                st.session_state.analysis = analysis
                st.session_state.analysis_timestamp = datetime.now()
                
                st.success("Analysis completed!")
                
            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")
                st.stop()
    
    # Display results if available
    if hasattr(st.session_state, 'analysis'):
        st.divider()
        display_analysis_results(st.session_state.analysis)
        
        # Export options
        st.divider()
        st.header("Export Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Copy to Clipboard", use_container_width=True):
                st.write("Copy the JSON below:")
                st.code(export_analysis(st.session_state.analysis), language="json")
        
        with col2:
            json_data = export_analysis(st.session_state.analysis)
            st.download_button(
                "Download JSON",
                data=json_data,
                file_name=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col3:
            if st.button("New Analysis", use_container_width=True):
                del st.session_state.analysis
                del st.session_state.analysis_timestamp
                st.rerun()
    
    # Footer
    st.divider()
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <p>Powered by Google Gemini AI • Built with Streamlit</p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
