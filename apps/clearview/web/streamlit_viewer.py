#!/usr/bin/env python3
"""
Alternative Streamlit-based data viewer for CE-QUAL-W2 data
Use this if Panel continues to have issues
"""

import streamlit as st
import pandas as pd
import io

st.set_page_config(
    page_title="ClearView Data Viewer",
    page_icon="🌊",
    layout="wide"
)

def main():
    st.title("🌊 ClearView - CE-QUAL-W2 Data Viewer")
    st.markdown("---")
    
    # File upload
    uploaded_file = st.file_uploader(
        "📁 Upload your data file",
        type=['csv', 'xlsx', 'xls'],
        help="Supported formats: CSV, Excel"
    )
    
    if uploaded_file is not None:
        try:
            # Load data
            if uploaded_file.name.lower().endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # Display file info
            st.success(f"✅ File loaded successfully!")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📄 Filename", uploaded_file.name)
            with col2:
                st.metric("📊 Rows", f"{len(df):,}")
            with col3:
                st.metric("📋 Columns", len(df.columns))
            
            # Tabs for different views
            tab1, tab2, tab3 = st.tabs(["📊 Data", "📈 Statistics", "🔍 Info"])
            
            with tab1:
                st.subheader("Data Preview")
                st.dataframe(df, use_container_width=True)
                
                # Download button
                csv = df.to_csv(index=False)
                st.download_button(
                    label="💾 Download as CSV",
                    data=csv,
                    file_name=f"{uploaded_file.name}_processed.csv",
                    mime="text/csv"
                )
            
            with tab2:
                st.subheader("Statistical Summary")
                
                # Numeric columns only
                numeric_df = df.select_dtypes(include=['number'])
                if len(numeric_df.columns) > 0:
                    st.dataframe(numeric_df.describe(), use_container_width=True)
                    
                    # Basic plots
                    st.subheader("Quick Visualizations")
                    
                    if len(numeric_df.columns) > 0:
                        selected_col = st.selectbox("Select column to plot:", numeric_df.columns)
                        if selected_col:
                            st.line_chart(numeric_df[selected_col])
                else:
                    st.warning("No numeric columns found for statistics")
            
            with tab3:
                st.subheader("Column Information")
                
                col_info = []
                for col in df.columns:
                    col_info.append({
                        'Column': col,
                        'Type': str(df[col].dtype),
                        'Non-null': df[col].count(),
                        'Null': df[col].isnull().sum(),
                        'Unique': df[col].nunique()
                    })
                
                info_df = pd.DataFrame(col_info)
                st.dataframe(info_df, use_container_width=True)
                
        except Exception as e:
            st.error(f"❌ Error loading file: {str(e)}")
    
    else:
        st.info("👆 Please upload a file to get started")
        
        # Instructions
        st.markdown("""
        ### 📋 Instructions
        
        1. **Upload** your CE-QUAL-W2 data file (CSV or Excel)
        2. **View** your data in the Data tab
        3. **Analyze** statistics in the Statistics tab
        4. **Explore** column information in the Info tab
        5. **Download** processed data as needed
        
        ### 🔧 Supported Formats
        - CSV files (.csv)
        - Excel files (.xlsx, .xls)
        
        ### 💡 Tips
        - Large files may take a moment to load
        - Use the search and filter options in the data table
        - Statistics are calculated for numeric columns only
        """)

if __name__ == "__main__":
    main()