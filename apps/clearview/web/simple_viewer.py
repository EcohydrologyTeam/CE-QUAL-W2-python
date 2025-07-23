#!/usr/bin/env python3
"""
Simple ClearView Data Viewer - Minimal Working Version
Bypasses complex tab system to ensure data is displayed
"""

import pandas as pd
import panel as pn
import io
import os

# Enable Panel extensions
pn.extension('tabulator')

class SimpleClearView:
    def __init__(self):
        self.df = None
        self.filename = None
        
    def create_app(self):
        """Create a simple single-page app that definitely works"""
        
        # File upload widget
        self.file_input = pn.widgets.FileInput(
            accept='.csv,.npt,.opt,.xlsx,.xls',
            name="📁 Upload Data File"
        )
        
        # Process button
        self.process_btn = pn.widgets.Button(
            name="🔄 Load Data", 
            button_type='primary'
        )
        
        # Status display
        self.status_text = pn.pane.Markdown("**Status:** Ready to load data")
        
        # Data display area
        self.data_display = pn.pane.Markdown("## No data loaded yet\nUpload a file and click 'Load Data'")
        
        # Set up event handlers
        self.process_btn.on_click(self.load_data)
        
        # Create layout
        controls = pn.Column(
            "# 🌊 ClearView - Simple Data Viewer",
            "---",
            self.file_input,
            self.process_btn,
            self.status_text,
            width=300,
            margin=(10, 10)
        )
        
        main_area = pn.Column(
            self.data_display,
            sizing_mode='stretch_width',
            margin=(10, 10)
        )
        
        app = pn.Row(
            controls,
            main_area,
            sizing_mode='stretch_width'
        )
        
        return app
        
    def load_data(self, event):
        """Load and display data"""
        try:
            self.status_text.object = "**Status:** 🔄 Loading data..."
            
            if self.file_input.value is None:
                self.status_text.object = "**Status:** ❌ Please select a file first"
                return
                
            # Load the data
            file_content = io.BytesIO(self.file_input.value)
            self.filename = self.file_input.filename
            
            if self.filename.lower().endswith('.csv'):
                self.df = pd.read_csv(file_content)
            elif self.filename.lower().endswith(('.xlsx', '.xls')):
                self.df = pd.read_excel(file_content)
            else:
                self.status_text.object = "**Status:** ❌ Unsupported file format"
                return
                
            # Display the data
            self.display_data()
            
        except Exception as e:
            self.status_text.object = f"**Status:** ❌ Error: {str(e)}"
            
    def display_data(self):
        """Display the loaded data"""
        try:
            # Create data summary
            summary = f"""
# 📊 Data Loaded Successfully!

**File:** {self.filename}  
**Rows:** {len(self.df):,}  
**Columns:** {len(self.df.columns)}  

## 📋 Column Names
{', '.join(self.df.columns.tolist())}

---

## 🔢 Data Preview (First 10 rows)
"""
            
            # Create data table
            data_table = pn.widgets.Tabulator(
                self.df.head(10),
                pagination='local',
                page_size=10,
                width=800,
                height=300,
                show_index=True
            )
            
            # Create statistics table
            stats_summary = "## 📈 Basic Statistics\n"
            if len(self.df.select_dtypes(include=['number']).columns) > 0:
                stats_df = self.df.describe()
                stats_table = pn.widgets.Tabulator(
                    stats_df,
                    width=600,
                    height=200
                )
                
                # Update the display
                self.data_display.object = pn.Column(
                    pn.pane.Markdown(summary),
                    data_table,
                    pn.pane.Markdown(stats_summary),
                    stats_table
                )
            else:
                self.data_display.object = pn.Column(
                    pn.pane.Markdown(summary),
                    data_table,
                    pn.pane.Markdown("*No numeric columns found for statistics*")
                )
            
            self.status_text.object = f"**Status:** ✅ Data loaded successfully!"
            
        except Exception as e:
            self.status_text.object = f"**Status:** ❌ Display error: {str(e)}"

if __name__ == "__main__":
    # Create and serve the app
    viewer = SimpleClearView()
    app = viewer.create_app()
    
    # Serve the app
    app.servable()
    app.show(port=5008, title="ClearView Simple Data Viewer")