# Built-in modules
import csv
import glob
import os
import sqlite3
import threading
import io
import warnings

# Third-party modules
from collections import OrderedDict

# Third-party modules
import pandas as pd
import seaborn as sns
import holoviews as hv
import panel as pn
from bokeh.models import CheckboxGroup, TextInput
from bokeh.models.widgets.tables import NumberFormatter, BooleanFormatter
from openpyxl import Workbook
from openpyxl.styles import Border, Side
# PyQt6 not needed for web application
# Add src to path for importing cequalw2
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))
import cequalw2 as w2
import datetime

hv.extension('bokeh')

css = """
.bk.bk-tab.bk-active {
  background-color: #00aedb;
  color: black;
  font-size: 14px;
  width: 100px;
  text-align: center;
  padding: 5px;
  margin: 1px;
}

.bk.bk-tab:not(bk-active) {
  background-color: gold;
  color: black;
  font-size: 14px;
  width: 100px;
  text-align: center;
  padding: 5px;
  margin: 1px;
}

.hv-Tabulator {
    height: 600px; /* Set a fixed height for the table */
    overflow-y: auto; /* Enable vertical scrolling */
}
"""

pn.extension('tabulator', raw_css=[css])


def write_dataframe_to_excel(df, filename, index=True, sheet_name='Sheet1'):
    # Create an Excel writer using openpyxl
    writer = pd.ExcelWriter(filename, engine='openpyxl')

    # Write the DataFrame to the Excel file
    df.to_excel(writer, index=index, sheet_name=sheet_name)

    # Access the workbook and sheet
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]

    # Remove the default borders around cells
    no_border = Border()

    # Remove borders for row headers
    for cell in worksheet['1']:
        cell.border = no_border

    # Remove borders for column headers
    for cell in worksheet['A']:
        cell.border = no_border

    # Auto-size column widths
    for column in worksheet.columns:
        max_length = 0
        column = [cell for cell in column]
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 2)
        worksheet.column_dimensions[column[0].column_letter].width = adjusted_width

    # Save the workbook
    writer.save()


class ClearView:
    def __init__(self):
        self.original_data_path = None
        self.processed_data_path = None
        self.stats_data_path = None
        self.table_name = 'data'

        # Set default number of rows to skip when reading input files
        self.skiprows = 3

        # Specify background color
        # self.background_color = '#f5fff5'
        self.background_color = '#fafafa'

        # Specify the app dimensions
        self.app_width = 1200
        self.app_height = 700

        # Start Year for CE-QUAL-W2 plots
        self.start_year = datetime.datetime.today().year

        # Set theme
        pn.widgets.Tabulator.theme = 'default'

        # Bokeh themes for plots
        self.bokeh_themes = ['default', 'caliber', 'dark_minimal', 'light_minimal', 'night_sky', 'contrast']

        # Set the selected theme
        self.selected_theme = 'night_sky'

        # Set the desired theme
        hv.renderer('bokeh').theme = self.selected_theme

        # Specify special column formatting
        self.float_format = NumberFormatter(format='0.00', text_align='right')

    def create_data_dropdown_widget(self):
        ''' Create a dropdown widget for selecting data columns '''
        self.data_dropdown = pn.widgets.Select(options=list(self.curves.keys()), name='Variable to Plot', width=200)
        
    def create_smart_plot_widget(self):
        '''Create web-native smart column picker for intelligent plot selection'''
        # Get numeric columns for plotting
        numeric_columns = list(self.df.select_dtypes(include=['number']).columns)
        
        # Create search input for filtering columns
        self.column_search = pn.widgets.TextInput(
            placeholder="Search columns...",
            name="Filter Columns",
            width=300
        )
        
        # Create multi-choice widget for column selection
        self.column_selector = pn.widgets.MultiChoice(
            options=numeric_columns,
            value=self._suggest_default_columns(numeric_columns),
            name="Select Columns to Plot",
            width=400,
            height=200
        )
        
        # Create action buttons
        self.select_all_btn = pn.widgets.Button(
            name="Select All", button_type="default", width=100
        )
        self.select_none_btn = pn.widgets.Button(
            name="Select None", button_type="default", width=100
        )
        self.suggest_btn = pn.widgets.Button(
            name="Smart Suggest", button_type="primary", width=120
        )
        
        # Create plot options checkboxes
        self.auto_scale_cb = pn.widgets.Checkbox(
            name="Auto-scale Y axes", value=True
        )
        self.show_grid_cb = pn.widgets.Checkbox(
            name="Show grid", value=True
        )
        self.shared_x_cb = pn.widgets.Checkbox(
            name="Shared X-axis", value=True
        )
        
        # Create plot button
        self.create_plot_btn = pn.widgets.Button(
            name="Create Plot", button_type="success", width=200
        )
        
        # Set up event handlers
        self.column_search.param.watch(self._filter_columns, 'value')
        self.select_all_btn.on_click(self._select_all_columns)
        self.select_none_btn.on_click(self._select_no_columns)
        self.suggest_btn.on_click(self._suggest_columns)
        self.create_plot_btn.on_click(self._create_smart_plot)
        
        # Create preview label
        self._update_plot_preview()
        self.column_selector.param.watch(self._update_plot_preview, 'value')
        
    def _suggest_default_columns(self, numeric_columns):
        '''Intelligent column suggestion based on water quality parameter priorities'''
        priority_terms = ['temp', 'temperature', 'ph', 'do', 'dissolved', 'oxygen', 
                         'turbidity', 'flow', 'depth', 'nitrate', 'phosphate', 't2', 'elws']
        
        suggested_columns = []
        max_suggestions = 4
        
        # First pass: exact matches with priority terms
        for col in numeric_columns:
            if len(suggested_columns) >= max_suggestions:
                break
            col_lower = col.lower()
            for term in priority_terms:
                if term in col_lower:
                    suggested_columns.append(col)
                    break
        
        # Second pass: if we don't have enough suggestions, add first few numeric columns
        if len(suggested_columns) < 3:
            for col in numeric_columns[:5]:
                if col not in suggested_columns:
                    suggested_columns.append(col)
                    if len(suggested_columns) >= max_suggestions:
                        break
        
        return suggested_columns[:max_suggestions]
    
    def _filter_columns(self, event):
        '''Filter column options based on search text'''
        search_text = event.new.lower()
        numeric_columns = list(self.df.select_dtypes(include=['number']).columns)
        
        if not search_text:
            filtered_options = numeric_columns
        else:
            filtered_options = [col for col in numeric_columns if search_text in col.lower()]
        
        # Update column selector options while preserving current selection
        current_selection = self.column_selector.value
        self.column_selector.options = filtered_options
        # Keep only valid selections
        valid_selection = [col for col in current_selection if col in filtered_options]
        self.column_selector.value = valid_selection
    
    def _select_all_columns(self, event):
        '''Select all available columns'''
        self.column_selector.value = self.column_selector.options
    
    def _select_no_columns(self, event):
        '''Clear all column selections'''
        self.column_selector.value = []
    
    def _suggest_columns(self, event):
        '''Apply smart column suggestions'''
        numeric_columns = list(self.df.select_dtypes(include=['number']).columns)
        suggested = self._suggest_default_columns(numeric_columns)
        self.column_selector.value = suggested
    
    def _update_plot_preview(self, event=None):
        '''Update plot preview information'''
        selected_count = len(self.column_selector.value) if hasattr(self, 'column_selector') else 0
        
        if selected_count == 0:
            preview_text = "No columns selected"
        else:
            estimated_height = max(selected_count * 2.5, 6)
            preview_text = (f"Preview: {selected_count} subplot{'s' if selected_count != 1 else ''}, "
                          f"estimated height: {estimated_height:.1f} inches")
        
        # Update preview in the UI
        if hasattr(self, 'plot_preview_label'):
            self.plot_preview_label.object = f"**{preview_text}**"
    
    def _create_smart_plot(self, event):
        '''Create intelligent multi-plot using selected columns with comprehensive error handling'''
        try:
            # Validation checks
            if not hasattr(self, 'column_selector') or not self.column_selector.value:
                self._show_status("No columns selected for plotting", "warning")
                return
                
            if not hasattr(self, 'df') or self.df is None or self.df.empty:
                self._show_status("No data available for plotting", "error")
                return
                
            selected_columns = self.column_selector.value
            
            # Validate selected columns exist in dataframe
            missing_columns = [col for col in selected_columns if col not in self.df.columns]
            if missing_columns:
                self._show_status(f"Columns not found in data: {missing_columns}", "error")
                return
                
            # Check for sufficient data
            if len(self.df) < 2:
                self._show_status("Insufficient data points for plotting (minimum 2 required)", "warning")
                return
                
            self._show_status(f"Creating smart plot with {len(selected_columns)} columns...", "info")
            
            # Create filtered dataframe with error handling
            try:
                plot_data = self.df[selected_columns].copy()
                
                # Remove any infinite values
                plot_data = plot_data.replace([float('inf'), float('-inf')], float('nan'))
                
                # Check if all data is NaN
                if plot_data.isnull().all().all():
                    self._show_status("Selected columns contain no valid data", "warning")
                    return
                    
            except Exception as e:
                self._show_status(f"Error preparing plot data: {str(e)}", "error")
                return
            
            # Create HoloViews plots with error handling
            plots = []
            failed_columns = []
            
            for col in selected_columns:
                try:
                    # Check if column has any valid data
                    if plot_data[col].isnull().all():
                        failed_columns.append(f"{col} (no valid data)")
                        continue
                        
                    # Create curve for this column
                    col_data = plot_data[col].dropna()
                    if len(col_data) == 0:
                        failed_columns.append(f"{col} (no data after cleaning)")
                        continue
                        
                    curve = hv.Curve(col_data, label=col)
                    
                    # Apply plot options with validation
                    opts = {
                        'width': max(self.app_width - 100, 400),
                        'height': 200,
                        'responsive': True,
                        'tools': ['hover', 'pan', 'wheel_zoom', 'box_zoom', 'reset'],
                        'toolbar': 'above',
                        'title': col
                    }
                    
                    if hasattr(self, 'show_grid_cb') and self.show_grid_cb.value:
                        opts['show_grid'] = True
                        
                    curve = curve.opts(**opts)
                    plots.append(curve)
                    
                except Exception as e:
                    failed_columns.append(f"{col} (error: {str(e)[:50]})")
                    continue
            
            # Report any failed columns
            if failed_columns:
                self._show_status(f"Failed to plot columns: {', '.join(failed_columns)}", "warning")
                
            if not plots:
                self._show_status("No valid plots could be created from selected columns", "error")
                return
            
            # Combine plots into layout with error handling
            try:
                if len(plots) == 1:
                    combined_plot = plots[0]
                else:
                    # Stack plots vertically
                    combined_plot = plots[0]
                    for plot in plots[1:]:
                        combined_plot = (combined_plot + plot).cols(1)
                
                # Update the main plot display
                if hasattr(self, 'smart_plot_panel'):
                    self.smart_plot_panel.object = combined_plot
                else:
                    # Create new plot panel if it doesn't exist
                    self.smart_plot_panel = pn.pane.HoloViews(combined_plot)
                    
                success_count = len(plots)
                total_count = len(selected_columns)
                self._show_status(f"Smart plot created successfully: {success_count}/{total_count} subplots", "success")
                
            except Exception as e:
                self._show_status(f"Error combining plots: {str(e)}", "error")
                return
            
        except Exception as e:
            self._show_status(f"Unexpected error creating smart plot: {str(e)}", "error")
            import traceback
            traceback.print_exc()

    def create_analysis_dropdown_widget(self):
        ''' Create a dropdown widget for selecting analysis and processing methods '''
        self.analysis_dropdown = pn.widgets.Select(options=list(self.time_series_methods.keys()), name='Analysis Method', width=200)

    def create_plot(self):
        ''' Create a holoviews plot of the data '''
        # Always use fallback approach to avoid DatetimeTickFormatter issues
        self._show_status("Creating plots for data visualization...", "info")
        self.curves = {}
        self.tooltips = {}
        
        # Get numeric columns for plotting
        numeric_cols = self.df.select_dtypes(include=['number']).columns
        
        if len(numeric_cols) == 0:
            self._show_status("No numeric columns found for plotting", "warning")
            # Create a dummy plot
            dummy_data = pd.Series([1, 2, 3], index=pd.date_range('2023-01-01', periods=3))
            self.curves = {'No Data': hv.Curve(dummy_data)}
            self.tooltips = {'No Data': None}
            return
        
        # Create plots for each numeric column
        plot_count = 0
        for col in numeric_cols:
            try:
                # Create simple curve without complex formatters
                curve_data = self.df[col].dropna()
                if len(curve_data) > 0:
                    # Create the curve
                    curve = hv.Curve(curve_data, label=col).opts(
                        width=self.app_width, 
                        height=300,
                        tools=['hover', 'pan', 'wheel_zoom', 'reset', 'save'],
                        title=col,
                        xlabel='Date',
                        ylabel=col,
                        toolbar='above',
                        responsive=True,
                        active_tools=['pan', 'wheel_zoom']
                    )
                    
                    self.curves[col] = curve
                    self.tooltips[col] = None  # Simple tooltip
                    plot_count += 1
                    
            except Exception as col_error:
                self._show_status(f"Skipping column {col}: {str(col_error)[:50]}", "warning")
                continue
                
        if plot_count > 0:
            self._show_status(f"Created {plot_count} plots successfully", "info")
        else:
            self._show_status("No valid plots could be created", "warning")
            # Create a dummy plot
            dummy_data = pd.Series([1, 2, 3], index=pd.date_range('2023-01-01', periods=3))
            self.curves = {'No Data': hv.Curve(dummy_data)}
            self.tooltips = {'No Data': None}

    # def create_theme_dropdown_widget(self):
    #     ''' Create a dropdown widget for selecting the theme '''
    #     self.theme_dropdown = pn.widgets.Select(options=self.bokeh_themes, width=200)

    # def recreate_plot(self, event):
    #     ''' Create a holoviews plot of the data '''
    #     # Get and set the selected theme
    #     self.selected_theme = self.theme_dropdown.value
    #     hv.renderer('bokeh').theme = self.selected_theme
    #     # Create a new plot
    #     self.curves, self.tooltips = w2.hv_plot(self.df, width=self.app_width, height=self.app_height)
    #     # Get the currently selected column
    #     selected_column = self.data_dropdown.value
    #     index = self.df.columns.tolist().index(self.data_dropdown.value)
    #     # Update the plot
    #     curve = self.curves[selected_column]
    #     tip = self.tooltips[selected_column]
    #     curve.opts(tools=[tip])
    #     print('Setting plot object in recreate')
    #     self.plot.object = curve

    def create_plot_widget(self):
        ''' Create plot widget with error handling '''
        try:
            # Get the first available column if no selection yet
            if not hasattr(self, 'data_dropdown') or not self.data_dropdown.value:
                if self.curves:
                    selected_column = list(self.curves.keys())[0]
                else:
                    self._show_status("No plot data available", "warning")
                    return
            else:
                selected_column = self.data_dropdown.value
            
            # Check if the selected column exists
            if selected_column not in self.curves:
                # Try to use the first available column
                if self.curves:
                    selected_column = list(self.curves.keys())[0]
                    self.data_dropdown.value = selected_column
                else:
                    self._show_status("No curves available for plotting", "warning")
                    return

            # Create the plot pane with error handling
            try:
                curve = self.curves[selected_column]
                # Try to create the pane
                self.plot = pn.pane.HoloViews(curve)
                
                # Add tooltip if available
                if hasattr(self, 'tooltips') and selected_column in self.tooltips and self.tooltips[selected_column]:
                    try:
                        self.plot.object.opts(tools=[self.tooltips[selected_column]])
                    except:
                        # Skip tooltip if it causes issues
                        pass
                        
            except Exception as e:
                # If HoloViews pane creation fails, create a simple matplotlib fallback
                self._show_status(f"Creating matplotlib fallback for plot: {str(e)[:50]}", "warning")
                import matplotlib.pyplot as plt
                fig, ax = plt.subplots(figsize=(10, 6))
                
                # Plot the data
                if selected_column in self.df.columns:
                    self.df[selected_column].plot(ax=ax)
                    ax.set_title(selected_column)
                    ax.set_xlabel('Date')
                    ax.set_ylabel(selected_column)
                    ax.grid(True)
                    
                self.plot = pn.pane.Matplotlib(fig, tight=True)
            
            # Set up watchers only if components exist
            if hasattr(self, 'data_dropdown'):
                self.data_dropdown.param.watch(self.update_plot, 'value')
            if hasattr(self, 'analysis_dropdown'):
                self.analysis_dropdown.param.watch(self.update_processed_data_table, 'value')
                
        except Exception as e:
            self._show_status(f"Error in create_plot_widget: {str(e)}", "error")
            # Create a placeholder
            self.plot = pn.pane.HTML("<p>Error creating plot widget</p>")

    def update_data_tab(self):
        ''' Create the Data tab '''
        if hasattr(self, 'data_tab'):
            self.data_tab.clear()
            if hasattr(self, 'data_table') and self.data_table is not None:
                self.data_tab.append(self.data_table)
                self._show_status("Data table added to tab", "info")
            else:
                self.data_tab.append("No data table available")
                self._show_status("No data table to display", "warning")
            if hasattr(self, 'save_original_data_button'):
                self.data_tab.append(self.save_original_data_button)

    def update_stats_tab(self):
        ''' Create the Stats tab '''
        if hasattr(self, 'stats_tab'):
            self.stats_tab.clear()
            if hasattr(self, 'stats_table'):
                self.stats_tab.append(self.stats_table)
            if hasattr(self, 'save_stats_button'):
                self.stats_tab.append(self.save_stats_button)

    def update_plot_tab(self):
        ''' Create the Plot tab '''
        if hasattr(self, 'plot_tab'):
            self.plot_tab.clear()
            
            # Check if we have the basic plot components
            if hasattr(self, 'data_dropdown') and hasattr(self, 'plot'):
                # Original single-variable plot section
                original_plot_section = pn.Column(
                    "## Single Variable Plot",
                    self.data_dropdown,
                    self.plot,
                    name="Single Plot"
                )
                self._show_status("Single variable plot section created", "info")
            else:
                original_plot_section = pn.Column(
                    "## Single Variable Plot",
                    "No plot data available",
                    name="Single Plot"
                )
                self._show_status("No plot components available", "warning")
            
            # Smart multi-plot section (only if we have data)
            if hasattr(self, 'df') and self.df is not None:
                try:
                    # Create smart plot widgets if they don't exist
                    if not hasattr(self, 'column_selector'):
                        self.create_smart_plot_widget()
                    
                    # Create plot preview label
                    if not hasattr(self, 'plot_preview_label'):
                        self.plot_preview_label = pn.pane.Markdown("**No columns selected**")
                    
                    # Create smart plot panel if it doesn't exist
                    if not hasattr(self, 'smart_plot_panel'):
                        self.smart_plot_panel = pn.pane.HTML("<p style='text-align: center; color: #666;'>Select columns and click 'Create Plot' to generate visualization</p>")
                    
                    # Action buttons layout
                    button_row = pn.Row(
                        self.select_all_btn,
                        self.select_none_btn, 
                        self.suggest_btn,
                        self.create_plot_btn
                    )
                    
                    # Plot options layout
                    options_row = pn.Row(
                        self.auto_scale_cb,
                        self.show_grid_cb,
                        self.shared_x_cb
                    )
                    
                    smart_plot_section = pn.Column(
                        "## Smart Multi-Plot",
                        "*Intelligently select and visualize multiple water quality parameters*",
                        self.column_search,
                        self.column_selector,
                        button_row,
                        "**Plot Options:**",
                        options_row,
                        self.plot_preview_label,
                        "---",
                        self.smart_plot_panel,
                        name="Smart Plot"
                    )
                    
                    # Combine both sections in tabs
                    plot_tabs = pn.Tabs(
                        ("Single Variable", original_plot_section),
                        ("Smart Multi-Plot", smart_plot_section),
                        dynamic=True
                    )
                    
                    self.plot_tab.append(plot_tabs)
                    self._show_status("Plot tab updated with smart plot functionality", "info")
                    
                except Exception as e:
                    self._show_status(f"Error creating smart plot section: {str(e)}", "warning")
                    self.plot_tab.append(original_plot_section)
            else:
                # If no data loaded, just show the original plot section
                self.plot_tab.append(original_plot_section)
                self._show_status("Plot tab updated with basic plot only", "info")

    def update_methods_tab(self):
        ''' Create Methods tab '''
        if hasattr(self, 'methods_tab'):
            self.methods_tab.clear()
            if hasattr(self, 'analysis_dropdown'):
                self.methods_tab.append(self.analysis_dropdown)
            if hasattr(self, 'processed_data_table') and self.processed_data_table is not None:
                self.methods_tab.append(self.processed_data_table)
                self._show_status("Methods tab updated with processed data", "info")
            else:
                self.methods_tab.append("No processed data available")
            if hasattr(self, 'save_processed_data_button'):
                self.methods_tab.append(self.save_processed_data_button)

    def create_data_table(self):
        ''' Create the data table using a Tabulator widget with error handling '''
        try:
            if self.df is None or self.df.empty:
                self._show_status("No data available for table creation", "warning")
                return
                
            # Limit display for very large datasets
            display_df = self.df.copy()
            if len(display_df) > 10000:
                display_df = display_df.iloc[:10000]  # Show first 10,000 rows
                self._show_status(f"Table limited to first 10,000 rows (total: {len(self.df):,} rows)", "info")
            
            # Specify column formatters with validation
            numeric_cols = display_df.select_dtypes(include=['number']).columns
            self.bokeh_formatters = {col: self.float_format for col in numeric_cols}
            header_align = {col: 'center' for col in display_df.columns}

            # Create the data table using a Tabulator widget
            self.data_table = pn.widgets.Tabulator(
                display_df,
                formatters=self.bokeh_formatters,
                frozen_columns=['Date'] if 'Date' in display_df.columns else [],
                show_index=True,
                header_align=header_align,
                text_align={},
                titles={},
                width=min(self.app_width, 1200),  # Limit width for readability
                height=min(self.app_height, 600),  # Limit height
                pagination='local' if len(display_df) > 100 else None,
                page_size=100 if len(display_df) > 100 else len(display_df)
            )
            
        except Exception as e:
            self._show_status(f"Error creating data table: {str(e)}", "error")
            # Create fallback simple display
            self.data_table = pn.pane.HTML(f"<p>Error displaying data table: {str(e)}</p>")

    def create_stats_table(self):
        ''' Create the stats table using a Tabulator widget '''

        # Compute summary statistics
        self.df_stats = self.df.describe()
        self.df_stats.index.name = 'Statistic'

        # Specify column formatters
        text_align = {}
        titles = {}
        header_align = {col: 'center' for col in self.df_stats.columns}

        # Create the stats table using a Tabulator widget
        self.stats_table = pn.widgets.Tabulator(
            self.df_stats,
            formatters=self.bokeh_formatters,
            frozen_columns=['Statistic'],
            show_index=True,
            header_align=header_align,
            width=self.app_width,
            height=250
        )

    def create_processed_data_table(self):
        ''' Create the processed data table using a Tabulator widget '''

        # Set the default processed data table
        self.df_processed = self.time_series_methods['Hourly Mean'](self.df)

        # Specify column formatters
        text_align = {}
        titles = {}
        header_align = {col: 'center' for col in self.df_processed.columns}

        # Create the processed data table using a Tabulator widget
        self.processed_data_table = pn.widgets.Tabulator(
            self.df_processed,
            formatters=self.bokeh_formatters,
            frozen_columns=['Date'],
            show_index=True,
            header_align=header_align,
            width=self.app_width,
            height=self.app_height
        )

    # Define a callback function to update the plot when the data dropdown value changes
    def update_plot(self, event):
        '''Update plot with comprehensive error handling'''
        try:
            if not hasattr(self, 'data_dropdown') or not self.data_dropdown.value:
                self._show_status("No column selected for plotting", "warning")
                return
                
            if not hasattr(self, 'df') or self.df is None or self.df.empty:
                self._show_status("No data available for plotting", "error")
                return
                
            selected_column = self.data_dropdown.value
            
            # Validate column exists
            if selected_column not in self.df.columns:
                self._show_status(f"Column '{selected_column}' not found in data", "error")
                return
                
            if not hasattr(self, 'curves') or selected_column not in self.curves:
                self._show_status(f"Plot data not available for column '{selected_column}'", "error")
                return
                
            # Update the plot
            curve = self.curves[selected_column]
            
            if hasattr(self, 'tooltips') and selected_column in self.tooltips:
                tip = self.tooltips[selected_column]
                curve.opts(tools=[tip])
                
            if hasattr(self, 'plot'):
                self.plot.object = curve
                self._show_status(f"Plot updated for column: {selected_column}", "info")
            else:
                self._show_status("Plot widget not available", "error")
                
        except Exception as e:
            self._show_status(f"Error updating plot: {str(e)}", "error")
            import traceback
            traceback.print_exc()

    # Define a callback function to update the processed data table when the analysis dropdown value changes
    def update_processed_data_table(self, event):
        selected_analysis = self.analysis_dropdown.value
        self.df_processed = self.time_series_methods[selected_analysis](self.df)
        self.processed_data_table.value = self.df_processed

    def parse_year_csv(self, w2_control_file_path):
        """
        Parses the year from a CSV file and sets it as the year attribute.

        This method reads a CSV file specified by `w2_control_file_path` and searches for a row where the first column (index 0)
        contains the value 'TMSTRT'. The year value is extracted from the subsequent row in the third column (index 2) and set
        as the year attribute of the class. Additionally, the extracted year is displayed in a QLineEdit widget with the object name
        'start_year_input'.

        Args:
            w2_control_file_path (str): The file path to the CSV file.
        """
        rows = []
        with open(w2_control_file_path, 'r') as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                rows.append(row)
        for i, row in enumerate(rows):
            if row[0].upper() == 'TMSTRT':
                self.start_year = int(rows[i + 1][2])

    def parse_year_npt(self, w2_control_file_path):
        """
        Parses the year from an NPT file and sets it as the year attribute.

        This method reads an NPT file specified by `w2_control_file_path` and searches for a line that starts with 'TMSTR' or 'TIME'.
        The subsequent line is then extracted, and the year value is obtained by removing the first 24 characters from the line
        and stripping any leading or trailing whitespace. The extracted year is then converted to an integer and set as the year
        attribute of the class. Additionally, the extracted year is displayed in a QLineEdit widget with the object name
        'start_year_input'.

        Args:
            w2_control_file_path (str): The file path to the NPT file.
        """
        with open(w2_control_file_path, 'r') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            line = line.strip().upper()
            if line.startswith('TMSTR') or line.startswith('TIME'):
                data_line = lines[i + 1]
                year_str = data_line[24:].strip()
                self.start_year = int(year_str)
                self.start_year_input.setText(str(self.start_year))

    def get_model_year(self):
        """
        Retrieves the model year from the CE-QUAL-W2 control file.

        This method locates the CE-QUAL-W2 control file in the specified directory by searching for specific filenames:
        - 'w2_con.csv'
        - '../w2_con.csv'
        - 'w2_con.npt'
        - '../w2_con.npt'

        Once the control file is found, its path and file type are stored in variables. The method then determines the file type
        (either CSV or NPT) and calls the appropriate parsing method (`parse_year_csv` or `parse_year_npt`) to extract the model year.
        The extracted year is then set as the year attribute of the class.

        Note:
            If no control file is found, a message is printed to indicate the absence of the file.
        """
        control_file_paths = [
            os.path.join(self.directory, 'w2_con.csv'),
            os.path.join(self.directory, '../w2_con.csv'),
            os.path.join(self.directory, 'w2_con.npt'),
            os.path.join(self.directory, '../w2_con.npt')
        ]

        w2_control_file_path = None
        w2_file_type = None

        for path in control_file_paths:
            if glob.glob(path):
                w2_control_file_path = path
                _, extension = os.path.splitext(path)
                w2_file_type = extension[1:].upper()
                break

        if w2_control_file_path is None:
            print('No control file found!')
            return

        print('w2_control_file_path =', w2_control_file_path)

        if w2_file_type == 'CSV':
            self.parse_year_csv(w2_control_file_path)
        elif w2_file_type == 'NPT':
            self.parse_year_npt(w2_control_file_path)

    def update_year(self, text):
        """
        Updates the year attribute based on the provided text.

        This method attempts to convert the `text` parameter to an integer and assigns it to the year attribute (`self.start_year`).
        If the conversion fails due to a `ValueError`, the year attribute is set to the default year value (`self.DEFAULT_YEAR`).

        Args:
            text (str): The text representing the new year value.
        """
        try:
            self.start_year = int(text)
        except ValueError:
            self.start_year = self.DEFAULT_YEAR

    def update_filename(self, text):
        """
        Updates the filename attribute with the provided text.

        This method sets the filename attribute (`self.filename`) to the given text value.

        Args:
            text (str): The new filename.
        """
        self.filename = text

    def _test_button_click(self, event):
        '''Test button to verify button clicks are working'''
        print("🔥 TEST BUTTON CLICKED! Button events are working.")
        self._show_status("🔥 Test button clicked - button events are working!", "success")
        
    def _handle_button_click(self, event):
        '''Alternative button click handler using param.watch'''
        print("🔥 DEBUG: Button click detected via param.watch!")
        self._show_status("🔥 Button click detected via param.watch!", "info")
        # Call the main processing function
        self.open_file(event)
        
    def _simple_process_file(self, event):
        '''Simple file processing with forced UI refresh'''
        try:
            print("🔥 SIMPLE PROCESS: Starting...")
            self._show_status("🔥 Simple Process: Starting file processing...", "info")
            
            if not hasattr(self, 'file_input') or self.file_input.value is None:
                self._show_status("❌ No file selected", "error")
                return
                
            # Simple CSV loading
            import io
            file_content = io.BytesIO(self.file_input.value)
            self.df = pd.read_csv(file_content)
            
            print(f"🔥 SIMPLE PROCESS: Loaded {len(self.df)} rows, {len(self.df.columns)} columns")
            self._show_status(f"✅ Loaded {len(self.df)} rows × {len(self.df.columns)} columns", "success")
            
            # Instead of updating existing tabs, create completely new content
            self._create_new_tabs_with_data()
                    
        except Exception as e:
            print(f"🔥 SIMPLE PROCESS ERROR: {e}")
            self._show_status(f"❌ Simple process failed: {str(e)}", "error")
            import traceback
            traceback.print_exc()
            
    def _create_new_tabs_with_data(self):
        '''Create completely new tabs with data to force refresh'''
        try:
            print("🔥 CREATING NEW TABS...")
            
            # Create a new data display
            data_content = pn.Column(
                "# Data Successfully Loaded!",
                f"**File:** {getattr(self, 'filename', 'uploaded file')}",
                f"**Rows:** {len(self.df):,}",
                f"**Columns:** {len(self.df.columns)}",
                "---",
                pn.widgets.Tabulator(
                    self.df.head(100),  # Show first 100 rows only
                    pagination='local', 
                    page_size=25,
                    width=800,
                    height=400
                )
            )
            
            # Create simple stats
            stats_df = self.df.describe()
            stats_content = pn.Column(
                "# Statistics",
                pn.widgets.Tabulator(stats_df, width=600, height=300)
            )
            
            # Force complete tab replacement
            if hasattr(self, 'tabs'):
                # Get current tabs
                old_tabs = self.tabs
                
                # Create completely new tabs
                new_tabs = pn.Tabs(
                    ('📊 Data', data_content),
                    ('📈 Stats', stats_content), 
                    ('🔧 Original Plot', self.plot_tab),
                    ('⚙️ Original Methods', self.methods_tab),
                    ('ℹ️ About', self.about_tab),
                    active=0  # Start on Data tab
                )
                
                # Replace tabs in main layout
                if hasattr(self, 'main'):
                    # Find and replace tabs in main
                    for i, obj in enumerate(self.main.objects):
                        if obj == old_tabs:
                            self.main.objects[i] = new_tabs
                            self.tabs = new_tabs
                            break
                            
            print("🔥 NEW TABS CREATED AND DISPLAYED!")
            self._show_status("✅ New tabs created with data! Check the 📊 Data tab.", "success")
            
        except Exception as e:
            print(f"🔥 NEW TABS ERROR: {e}")
            import traceback
            traceback.print_exc()
            
    def _auto_process_file(self, event):
        '''Automatically process file when uploaded (if toggle is enabled)'''
        try:
            print("🔥 AUTO-PROCESS: File input changed!")
            
            # Check if auto-processing is enabled
            if not hasattr(self, 'auto_process_toggle') or not self.auto_process_toggle.value:
                print("🔥 AUTO-PROCESS: Auto-processing disabled")
                return
                
            # Check if we have a file
            if event.new is None:
                print("🔥 AUTO-PROCESS: No file uploaded")
                return
                
            print(f"🔥 AUTO-PROCESS: Processing file: {getattr(self.file_input, 'filename', 'unknown')}")
            self._show_status("🔄 Auto-processing uploaded file...", "info")
            
            # Use the simple processing approach
            self._simple_process_file(event)
            
        except Exception as e:
            print(f"🔥 AUTO-PROCESS ERROR: {e}")
            self._show_status(f"❌ Auto-processing failed: {str(e)}", "error")
        
    def open_file_holoviews(self, event):
        pass


    def open_file(self, event):
        '''Open a file for viewing and analysis - WEB VERSION with enhanced pipeline'''
        print("🔥 DEBUG: Process File button clicked!")
        self._show_status("🔥 DEBUG: Process File button clicked!", "info")
        
        if not hasattr(self, 'file_input'):
            self._show_status("❌ File input widget not found", "error")
            return
            
        if self.file_input.value is None:
            self._show_status("Please select a file to upload first", "warning")
            return
            
        print(f"🔥 DEBUG: File input has value, filename: {getattr(self.file_input, 'filename', 'unknown')}")
            
        # Start processing pipeline
        self._show_status("Processing uploaded file...", "info")
        
        try:
            # Initialize processing
            result = self._initialize_file_processing()
            if not result['success']:
                self._show_status(result['message'], "error")
                return
                
            # Load and validate data
            result = self._load_and_validate_data()
            if not result['success']:
                self._show_status(result['message'], "error")
                return
                
            # Create visualization components
            result = self._create_visualization_components()
            if not result['success']:
                self._show_status(result['message'], "error")
                return
                
            # Update user interface
            result = self._update_user_interface()
            if not result['success']:
                self._show_status(result['message'], "error")
                return
                
            # Cleanup and finalize
            self._cleanup_processing()
            
            self._show_status(f"Successfully loaded {self.filename} ({len(self.df)} rows × {len(self.df.columns)} columns)", "success")
            
            # Force tab refresh by triggering a change event
            if hasattr(self, 'tabs'):
                try:
                    # Trigger refresh of the tabs
                    current_active = self.tabs.active
                    self.tabs.active = 0  # Switch to Data tab
                    self._show_status("✓ All data processing complete! Check the Data, Plot, Stats, and Methods tabs.", "success")
                except:
                    pass
            
        except Exception as e:
            self._show_status(f"Failed to process {self.filename}: {str(e)}", "error")
            import traceback
            traceback.print_exc()
            self._cleanup_processing()
            
    def _show_status(self, message, level="info"):
        '''Display status message to user'''
        prefix = {
            "info": "ℹ️",
            "success": "✅", 
            "warning": "⚠️",
            "error": "❌"
        }.get(level, "ℹ️")
        print(f"{prefix} {message}")
        
    def _initialize_file_processing(self):
        '''Initialize file processing and determine file type'''
        try:
            self.filename = self.file_input.filename
            self.file_content = io.BytesIO(self.file_input.value)
            self.file_size = len(self.file_input.value)
            basefilename, extension = os.path.splitext(self.filename)
            
            # Validate file size (100MB limit)
            if self.file_size > 100 * 1024 * 1024:
                return {'success': False, 'message': 'File too large (max 100MB)'}
                
            # Determine file type
            extension = extension.lower()
            if extension in ['.npt', '.opt']:
                self.file_type = 'ASCII_FIXED'
            elif extension == '.csv':
                self.file_type = 'CSV'
            elif extension == '.db':
                self.file_type = 'SQLITE'
            elif extension in ['.xlsx', '.xls']:
                self.file_type = 'EXCEL'
            elif extension in ['.h5', '.hdf5']:
                self.file_type = 'HDF5'
            elif extension == '.nc':
                self.file_type = 'NETCDF'
            else:
                return {'success': False, 'message': f'Unsupported file format: {extension}'}
                
            self._show_status(f"Processing {self.file_type} file: {self.filename} ({self.file_size/1024/1024:.1f} MB)", "info")
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'message': f'Initialization failed: {str(e)}'}
            
    def _load_and_validate_data(self):
        '''Load data using appropriate method based on file type'''
        try:
            # Get processing parameters (with fallback if widgets not created yet)
            if hasattr(self, 'w2_find_start_year_checkbox') and self.w2_find_start_year_checkbox.value:
                self._extract_start_year()
            else:
                # Use default start year if widget not available
                if hasattr(self, 'start_year_input'):
                    self.start_year = int(self.start_year_input.value)
                else:
                    self.start_year = datetime.datetime.today().year
                
            if hasattr(self, 'skiprows_input'):
                self.skiprows = int(self.skiprows_input.value)
            else:
                self.skiprows = 3  # Default value
            
            # Load data based on file type
            if self.file_type == 'CSV':
                self.df = self._load_csv_data()
            elif self.file_type in ['ASCII_FIXED']:
                self.df = self._load_ascii_data()
            elif self.file_type == 'EXCEL':
                self.df = self._load_excel_data()
            elif self.file_type == 'SQLITE':
                self.df = self._load_sqlite_data()
            elif self.file_type == 'HDF5':
                self.df = self._load_hdf5_data()
            elif self.file_type == 'NETCDF':
                self.df = self._load_netcdf_data()
            else:
                return {'success': False, 'message': f'No loader for {self.file_type}'}
                
            # Validate loaded data
            if self.df is None or self.df.empty:
                return {'success': False, 'message': 'No data loaded from file'}
                
            # Ensure proper datetime index
            self._ensure_datetime_index()
            
            # Basic data validation
            validation_result = self._validate_data()
            if not validation_result['success']:
                self._show_status(f"Data validation warning: {validation_result['message']}", "warning")
                
            self._show_status(f"Data loaded: {len(self.df)} rows × {len(self.df.columns)} columns", "info")
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'message': f'Data loading failed: {str(e)}'}
            
    def _load_csv_data(self):
        '''Load CSV data with fallback handling'''
        try:
            # First, try standard pandas CSV loading
            self.file_content.seek(0)
            # For web uploads, usually don't skip rows since file format is cleaner
            skip_rows = 0 if hasattr(self, 'file_input') else self.skiprows
            df = pd.read_csv(self.file_content, skiprows=skip_rows)
            self._show_status("Standard CSV parsing succeeded", "info")
            return df
        except Exception as e:
            self._show_status(f"Standard CSV parsing failed: {e}", "warning")
            
            try:
                # Fallback: Try with different parameters
                self.file_content.seek(0)
                # Try with different separators and encoding
                for sep in [',', '\t', ';', ' ']:
                    try:
                        self.file_content.seek(0)
                        df = pd.read_csv(self.file_content, sep=sep, skiprows=self.skiprows, encoding='utf-8')
                        if len(df.columns) > 1:  # Successful if we got multiple columns
                            self._show_status(f"Fallback CSV parsing succeeded with separator '{sep}'", "info")
                            return df
                    except:
                        continue
                        
                # Last resort: read as text and parse manually
                self.file_content.seek(0)
                lines = self.file_content.read().decode('utf-8').split('\n')
                data_lines = lines[self.skiprows:]
                # Simple parsing assuming comma separation
                data = []
                for line in data_lines[:1000]:  # Limit to first 1000 rows for safety
                    if line.strip():
                        parts = line.split(',')
                        if len(parts) > 1:
                            data.append(parts)
                            
                if data:
                    df = pd.DataFrame(data[1:], columns=data[0])
                    # Try to convert numeric columns
                    for col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='ignore')
                    self._show_status("Manual CSV parsing succeeded", "info")
                    return df
                    
            except Exception as e2:
                raise Exception(f"All CSV parsing methods failed. Last error: {e2}")
                
    def _load_excel_data(self):
        '''Load Excel data'''
        self.file_content.seek(0)
        df = pd.read_excel(self.file_content, skiprows=self.skiprows)
        return df
        
    def _load_ascii_data(self):
        '''Load ASCII fixed-width data (NPT/OPT files)'''
        # Save temporarily for w2 module processing
        temp_path = f"/tmp/{self.filename}"
        with open(temp_path, 'wb') as f:
            f.write(self.file_input.value)
        try:
            data_columns = w2.get_data_columns_fixed_width(temp_path)
            df = w2.read(temp_path, self.start_year, data_columns, skiprows=self.skiprows)
            return df
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    def _load_sqlite_data(self):
        '''Load SQLite database'''
        temp_path = f"/tmp/{self.filename}"
        with open(temp_path, 'wb') as f:
            f.write(self.file_input.value)
        try:
            df = w2.read_sqlite(temp_path)
            return df
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    def _load_hdf5_data(self):
        '''Load HDF5 data'''
        self.file_content.seek(0)
        df = pd.read_hdf(self.file_content)
        return df
        
    def _load_netcdf_data(self):
        '''Load NetCDF data'''
        import xarray as xr
        temp_path = f"/tmp/{self.filename}"
        with open(temp_path, 'wb') as f:
            f.write(self.file_input.value)
        try:
            ds = xr.open_dataset(temp_path)
            df = ds.to_dataframe()
            return df
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    def _ensure_datetime_index(self):
        '''Ensure the dataframe has a proper datetime index'''
        if 'Date' in self.df.columns:
            try:
                self.df['Date'] = pd.to_datetime(self.df['Date'])
                self.df.set_index('Date', inplace=True)
            except:
                pass
        elif not isinstance(self.df.index, pd.DatetimeIndex):
            # Create datetime index based on start year
            start_date = pd.Timestamp(year=self.start_year, month=1, day=1)
            date_range = pd.date_range(start=start_date, periods=len(self.df), freq='D')
            self.df.index = date_range
            self.df.index.name = 'Date'
            
    def _validate_data(self):
        '''Perform basic data validation'''
        issues = []
        
        # Check for numeric data
        numeric_cols = self.df.select_dtypes(include=['number']).columns
        if len(numeric_cols) == 0:
            issues.append("No numeric columns found")
            
        # Check for missing data
        missing_pct = (self.df.isnull().sum().sum() / (len(self.df) * len(self.df.columns))) * 100
        if missing_pct > 50:
            issues.append(f"High missing data percentage: {missing_pct:.1f}%")
            
        # Check data range
        if len(self.df) < 2:
            issues.append("Insufficient data points for analysis")
            
        if issues:
            return {'success': False, 'message': '; '.join(issues)}
        return {'success': True}
        
    def _extract_start_year(self):
        '''Extract start year from CE-QUAL-W2 control files'''
        try:
            # Check if a control file was uploaded
            if hasattr(self, 'control_file_input') and self.control_file_input.value is not None:
                self._show_status("Using uploaded control file for start year detection", "info")
                
                # Save control file temporarily
                control_filename = self.control_file_input.filename
                temp_control_path = f"/tmp/{control_filename}"
                with open(temp_control_path, 'wb') as f:
                    f.write(self.control_file_input.value)
                
                # Extract year from control file
                try:
                    if control_filename.lower().endswith('.csv'):
                        self._extract_year_from_csv(temp_control_path)
                    elif control_filename.lower().endswith('.npt'):
                        self._extract_year_from_npt(temp_control_path)
                    
                    self._show_status(f"Start year extracted from control file: {self.start_year}", "success")
                    if hasattr(self, 'start_year_input'):
                        self.start_year_input.value = str(self.start_year)
                        
                except Exception as e:
                    self._show_status(f"Error reading control file: {str(e)}", "warning")
                    self.start_year = datetime.datetime.today().year
                
                # Clean up
                if os.path.exists(temp_control_path):
                    os.remove(temp_control_path)
                    
            else:
                # No control file uploaded, use default
                self._show_status("No control file uploaded, using current year", "info")
                self.start_year = datetime.datetime.today().year
                
        except Exception as e:
            self._show_status(f"Error in start year extraction: {str(e)}", "warning")
            self.start_year = datetime.datetime.today().year
            
    def _extract_year_from_csv(self, file_path):
        '''Extract year from CSV control file'''
        with open(file_path, 'r') as f:
            csv_reader = csv.reader(f)
            rows = list(csv_reader)
            
        for i, row in enumerate(rows):
            if len(row) > 0 and row[0].upper().strip() == 'TMSTRT':
                if i + 1 < len(rows) and len(rows[i + 1]) > 2:
                    self.start_year = int(rows[i + 1][2])
                    return
                    
        # Fallback
        self.start_year = datetime.datetime.today().year
        
    def _extract_year_from_npt(self, file_path):
        '''Extract year from NPT control file'''
        with open(file_path, 'r') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            line_upper = line.strip().upper()
            if line_upper.startswith('TMSTR') or line_upper.startswith('TIME'):
                if i + 1 < len(lines):
                    data_line = lines[i + 1]
                    year_str = data_line[24:].strip()
                    self.start_year = int(year_str)
                    return
                    
        # Fallback
        self.start_year = datetime.datetime.today().year
                
    def _create_visualization_components(self):
        '''Create visualization components'''
        try:
            # Create plot components with error handling
            try:
                self.create_plot()
            except Exception as plot_error:
                self._show_status(f"Plot creation had issues: {str(plot_error)[:100]}", "warning")
                # Continue anyway as create_plot has its own fallback
            
            self.set_time_series_methods()
            self.create_data_dropdown_widget()
            self.create_analysis_dropdown_widget()
            
            # Create widgets with individual error handling
            components = [
                ('plot_widget', self.create_plot_widget),
                ('data_table', self.create_data_table),
                ('stats_table', self.create_stats_table),
                ('processed_data_table', self.create_processed_data_table)
            ]
            
            for name, create_func in components:
                try:
                    create_func()
                except Exception as e:
                    self._show_status(f"Error creating {name}: {str(e)[:50]}", "warning")
                    continue
            
            return {'success': True}
        except Exception as e:
            return {'success': False, 'message': f'Visualization creation failed: {str(e)}'}
            
    def _update_user_interface(self):
        '''Update the user interface with new data'''
        try:
            # Only update UI if tabs are available (app has been initialized)
            if hasattr(self, 'data_tab'):
                self.update_data_tab()
            if hasattr(self, 'stats_tab'):
                self.update_stats_tab()
            if hasattr(self, 'plot_tab'):
                self.update_plot_tab()
            if hasattr(self, 'methods_tab'):
                self.update_methods_tab()
            return {'success': True}
        except Exception as e:
            return {'success': False, 'message': f'UI update failed: {str(e)}'}
            
    def _cleanup_processing(self):
        '''Clean up temporary resources'''
        # Clean up any temporary files
        if hasattr(self, 'temp_files'):
            for temp_file in self.temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass

    def set_time_series_methods(self):
        # Specify the time series math and stats methods
        self.time_series_methods = OrderedDict()
        # Compute hourly mean, interpolating to fill missing values
        self.time_series_methods['Hourly Mean'] = lambda df: df.resample('H').mean().interpolate()
        self.time_series_methods['Hourly Max'] = lambda df: df.resample('H').max().interpolate()
        self.time_series_methods['Hourly Min'] = lambda df: df.resample('H').min().interpolate()
        self.time_series_methods['Daily Mean'] = lambda df: df.resample('D').mean().interpolate()
        self.time_series_methods['Daily Max'] = lambda df: df.resample('D').max().interpolate()
        self.time_series_methods['Daily Min'] = lambda df: df.resample('D').min().interpolate()
        self.time_series_methods['Weekly Mean'] = lambda df: df.resample('W').mean().interpolate()
        self.time_series_methods['Weekly Max'] = lambda df: df.resample('W').max().interpolate()
        self.time_series_methods['Weekly Min'] = lambda df: df.resample('W').min().interpolate()
        self.time_series_methods['Monthly Mean'] = lambda df: df.resample('M').mean().interpolate()
        self.time_series_methods['Monthly Max'] = lambda df: df.resample('M').max().interpolate()
        self.time_series_methods['Monthly Min'] = lambda df: df.resample('M').min().interpolate()
        self.time_series_methods['Annual Mean'] = lambda df: df.resample('Y').mean().interpolate()
        self.time_series_methods['Annual Max'] = lambda df: df.resample('Y').max().interpolate()
        self.time_series_methods['Annual Min'] = lambda df: df.resample('Y').min().interpolate()
        self.time_series_methods['Decadal Mean'] = lambda df: df.resample('10Y').mean().interpolate()
        self.time_series_methods['Decadal Max'] = lambda df: df.resample('10Y').max().interpolate()
        self.time_series_methods['Decadal Min'] = lambda df: df.resample('10Y').min().interpolate()
        self.time_series_methods['Cumulative Sum'] = lambda df: df.cumsum()
        self.time_series_methods['Cumulative Max'] = lambda df: df.cummax()
        self.time_series_methods['Cumulative Min'] = lambda df: df.cummin()

    def save_to_sqlite(self, df: pd.DataFrame, database_path: str):
        """
        Saves the data to an SQLite database.

        This method saves the data stored in the `data` attribute to an SQLite database file specified by the `original_data_path` attribute.
        The table name is set as the `filename` attribute.
        If the database file already exists, the table with the same name is replaced.
        The data is saved with the index included as a column.

        Note:
            - The `data` attribute must be set with the data before calling this method.
            - The `original_data_path` attribute must be properly set with the path to the SQLite database file.
        """
        self.table_name, _ = os.path.splitext(self.filename)
        con = sqlite3.connect(database_path)
        df.to_sql(self.table_name, con, if_exists='replace', index=True)
        con.close()

    def save_data(self, event):
        """
        Saves the data to a downloadable file.
        WEB VERSION: Implements web-native download functionality.
        """
        try:
            if not hasattr(self, 'df') or self.df is None or self.df.empty:
                self._show_status("No data available to save", "warning")
                return
                
            # Create download options
            self._show_status("Preparing data for download...", "info")
            
            # Save as CSV for web download
            csv_buffer = io.StringIO()
            self.df.to_csv(csv_buffer, index=True)
            csv_content = csv_buffer.getvalue()
            
            # Create download button
            filename = f"{os.path.splitext(self.filename)[0]}_data.csv"
            download_button = pn.widgets.FileDownload(
                file=csv_content,
                filename=filename,
                button_type='success'
            )
            
            # Display download options in a temporary panel
            download_panel = pn.Column(
                "## Download Data",
                f"**Original file:** {self.filename}",
                f"**Rows:** {len(self.df):,}",
                f"**Columns:** {len(self.df.columns)}",
                "**Format:** CSV with timestamps",
                download_button,
                width=400
            )
            
            # Add to data tab temporarily
            self.data_tab.append(download_panel)
            self._show_status(f"Download ready: {filename}", "success")
            
        except Exception as e:
            self._show_status(f"Error preparing download: {str(e)}", "error")
        default_filename = self.file_path + '.xlsx'
        options = qtw.QFileDialog.Options()
        # options |= qtw.QFileDialog.DontUseNativeDialog
        returned_path, _ = qtw.QFileDialog.getSaveFileName(
            self.save_original_data_dialog_app.activeModalWidget(),
            'Save As', default_filename, 'Excel Files (*.xlsx);; SQLite Files (*.db)', options=options)
        if not returned_path:
            return

        self.original_data_path = returned_path

        if self.original_data_path and self.df is not None:
            if self.original_data_path.endswith('.xlsx'):
                # self.df.to_excel(self.original_data_path, index=True)
                write_dataframe_to_excel(self.df, self.original_data_path, index=True, sheet_name='Original Data')
            if self.original_data_path.endswith('.db'):
                self.save_to_sqlite(self.df, self.original_data_path)

    def save_processed_data(self, event):
        """WEB VERSION: Implements web-native download for processed data."""
        try:
            if not hasattr(self, 'df_processed') or self.df_processed is None or self.df_processed.empty:
                self._show_status("No processed data available to save", "warning")
                return
                
            self._show_status("Preparing processed data for download...", "info")
            
            # Save as CSV for web download
            csv_buffer = io.StringIO()
            self.df_processed.to_csv(csv_buffer, index=True)
            csv_content = csv_buffer.getvalue()
            
            # Create download button
            method_name = self.analysis_dropdown.value if hasattr(self, 'analysis_dropdown') else "processed"
            filename = f"{os.path.splitext(self.filename)[0]}_{method_name.lower().replace(' ', '_')}.csv"
            
            download_button = pn.widgets.FileDownload(
                file=csv_content,
                filename=filename,
                button_type='success'
            )
            
            # Display download options
            download_panel = pn.Column(
                "## Download Processed Data",
                f"**Processing method:** {method_name}",
                f"**Rows:** {len(self.df_processed):,}",
                f"**Columns:** {len(self.df_processed.columns)}",
                download_button,
                width=400
            )
            
            self.methods_tab.append(download_panel)
            self._show_status(f"Processed data download ready: {filename}", "success")
            
        except Exception as e:
            self._show_status(f"Error preparing processed data download: {str(e)}", "error")
        """
        Saves the processed data to a selected file as an SQLite database.

        This method allows the user to select a file path to save the data as an SQLite database.
        If a valid file path is selected and the `data` attribute is not `None`, the following steps are performed:
        1. The `original_data_path` attribute is set to the selected file path.
        2. The `save_to_sqlite` method is called to save the data to the SQLite database file.
        3. The statistics table is updated after saving the data.

        Note:
            - The `data` attribute must be set with the data before calling this method.
        """
        default_filename = self.file_path + '_processed.xlsx'
        options = qtw.QFileDialog.Options()
        # options |= qtw.QFileDialog.DontUseNativeDialog
        returned_path, _ = qtw.QFileDialog.getSaveFileName(
            self.save_processed_data_dialog_app.activeModalWidget(),
            'Save As', default_filename, 'Excel Files (*.xlsx);; SQLite Files (*.db)', options=options)
        if not returned_path:
            return

        self.processed_data_path = returned_path

        if self.processed_data_path and self.df_processed is not None:
            if self.processed_data_path.endswith('.xlsx'):
                # self.df_processed.to_excel(self.processed_data_path, index=True)
                write_dataframe_to_excel(self.df_processed, self.processed_data_path,
                                         index=True, sheet_name='Processed Data')
            if self.processed_data_path.endswith('.db'):
                self.save_to_sqlite(self.df_processed, self.processed_data_path)

    def save_stats(self, event):
        """WEB VERSION: Implements web-native download for statistics.""" 
        try:
            if not hasattr(self, 'df_stats') or self.df_stats is None or self.df_stats.empty:
                self._show_status("No statistics available to save", "warning")
                return
                
            self._show_status("Preparing statistics for download...", "info")
            
            # Save as CSV for web download
            csv_buffer = io.StringIO()
            self.df_stats.to_csv(csv_buffer, index=True)
            csv_content = csv_buffer.getvalue()
            
            # Create download button
            filename = f"{os.path.splitext(self.filename)[0]}_statistics.csv"
            
            download_button = pn.widgets.FileDownload(
                file=csv_content,
                filename=filename,
                button_type='success'
            )
            
            # Display download options
            download_panel = pn.Column(
                "## Download Statistics",
                f"**Statistics for:** {self.filename}",
                f"**Metrics:** {len(self.df_stats)} statistical measures",
                f"**Variables:** {len(self.df_stats.columns)} columns",
                download_button,
                width=400
            )
            
            self.stats_tab.append(download_panel)
            self._show_status(f"Statistics download ready: {filename}", "success")
            
        except Exception as e:
            self._show_status(f"Error preparing statistics download: {str(e)}", "error")
        """
        Saves statistics to an SQLite database file.

        Prompts the user to select a file path for saving the statistics and
        saves the statistics to the chosen file path.

        :return: None
        """

        default_filename = self.file_path + '_stats.xlsx'
        options = qtw.QFileDialog.Options()
        returned_path, _ = qtw.QFileDialog.getSaveFileName(self.save_stats_dialog_app.activeModalWidget(
        ), 'Save As', default_filename, 'Excel Files (*.xlsx);; SQLite Files (*.db)', options=options)
        if not returned_path:
            return

        self.stats_data_path = returned_path

        if self.stats_data_path and self.df_stats is not None:
            if self.stats_data_path.endswith('.xlsx'):
                # self.df_stats.to_excel(self.stats_data_path, index=True)
                write_dataframe_to_excel(self.df_stats, self.stats_data_path, index=True, sheet_name='Summary Stats')
            if self.stats_data_path.endswith('.db'):
                self.save_to_sqlite(self.df_stats, self.stats_data_path)

    def create_empty_tab(self):
        # Create informative empty tab
        empty_content = pn.pane.Markdown("""
        ## No Data Loaded
        
        Please upload a data file using the sidebar to see content in this tab.
        
        **Supported formats:**
        - CSV files (.csv)
        - CE-QUAL-W2 NPT files (.npt)
        - CE-QUAL-W2 OPT files (.opt)
        - Excel files (.xlsx, .xls)
        - SQLite databases (.db)
        - HDF5 files (.h5)
        - NetCDF files (.nc)
        """)
        
        tab = pn.Column(
            empty_content,
            sizing_mode='stretch_both',
            margin=(20, 20, 20, 20),
            css_classes=['panel-widget-box'],
            scroll=True,
            styles={'background': self.background_color}
        )
        return tab

    def create_empty_tabs(self):
        # Create empty tabs
        self.data_tab = self.create_empty_tab()
        self.stats_tab = self.create_empty_tab()
        self.plot_tab = self.create_empty_tab()
        self.methods_tab = self.create_empty_tab()
        self.about_tab = self.create_empty_tab()

        # Text for About tab
        about_text = """
        ClearView is a tool for viewing and analyzing water quality and environmental time series data. Designed to work with model input and output data, sensor data, and laboratory measurements, ClearView seamlessly reads and writes multiple data formats, providing compatibility and flexibility with a variety of new and legacy models, sensors, analysis tools, and workflows.

        The user interface of ClearView is designed with simplicity and usability in mind. Its plotting component allows you to generate informative plots, enabling the identification of trends, patterns, and anomalies within your time series data. ClearView provides a tabular display, facilitating easy access and interpretation. ClearView's summary statistics provides a concise summary of your data. This feature allows you to evaluate key statistical measures, facilitating data-driven analysis and decision-making.

        ClearView streamlines data analysis and time series processing. Leveraging advanced algorithms and statistical techniques, this tool enables exploring data and calculating relevant metrics to derive valuable insights, such as identifying pollution sources, detecting changes in water quality over time, and deriving a deeper understanding of environmental data.

        The aim of ClearView is to streamline workflows and enhance productivity. By integrating data visualization, analysis, and statistical summaries, ClearView enables making informed decisions and effectively communicating findings.

        <hr>

        <b>Author:</b>

        Todd E. Steissberg, PhD, PE<br>
        Ecohydrology Team<br>
        Environmental Laboratory<br>
        U.S. Army Engineer Research and Development Center (ERDC)<br>
        Email: Todd.E.Steissberg@usace.army.mil

        <b>Version:</b> 2.0 (Web Edition)

        <b>Date:</b> July 2025
        """

        about_panel = pn.layout.WidgetBox(
            about_text,
            sizing_mode='stretch_width',
            max_width=700,
        )

        self.about_tab.append(about_panel)
        
    def update_date_system(self, event):
        '''Enable/disable the text input field based on dropdown selection'''
        if self.date_system_dropdown.value == 'Day of Year':
            self.date_system = 'Day of Year'
            self.start_year_input.disabled = False
            self.w2_find_start_year_checkbox.disabled = False
        elif self.date_system_dropdown.value == 'Standard Calendar':
            self.date_system = 'Standard Calendar'
            self.start_year_input.disabled = True
            self.w2_find_start_year_checkbox.disabled = True
        else:
            raise ValueError('Unrecognized option in the date system dropdown list.')

    def create_sidebar(self):
        sidebar_text = """
        <h2><font color="dodgerblue">ClearView</font>
        <h3><font color="#7eab55">Environmental Visualization & Analysis</font></h3>
        <hr>
        """

        # create an html tag with dodgerblue color and bold text
        # pn.pane.HTML('<font color="dodgerblue"><b>Upload a File:</b></font>')

        # Create file input widget for web-native file upload
        self.file_input = pn.widgets.FileInput(
            accept='.csv,.npt,.opt,.xlsx,.xls,.db,.h5,.nc',
            multiple=False,
            name="Upload Data File"
        )
        
        # Optional control file input for CE-QUAL-W2 start year detection
        self.control_file_input = pn.widgets.FileInput(
            accept='.csv,.npt',
            multiple=False,
            name="Upload Control File (Optional)",
            height=50
        )
        
        # Create button to process uploaded file with alternative event binding
        self.file_button = pn.widgets.Button(name='Process File', button_type='primary')
        
        # Try multiple event binding approaches
        self.file_button.on_click(self.open_file)  # Standard approach
        self.file_button.param.watch(self._handle_button_click, 'clicks')  # Alternative approach
        
        print(f"🔥 DEBUG: Created Process File button: {self.file_button}")
        print(f"🔥 DEBUG: Button click handlers set")
        self.save_original_data_button = pn.widgets.Button(name='Save Original Data', button_type='primary')
        self.save_original_data_button.on_click(self.save_data)
        self.save_stats_button = pn.widgets.Button(name='Save Stats', button_type='primary')
        self.save_stats_button.on_click(self.save_stats)
        self.save_processed_data_button = pn.widgets.Button(name='Save Processed Data', button_type='primary')
        self.save_processed_data_button.on_click(self.save_processed_data)

        self.w2_find_start_year_checkbox = pn.widgets.Checkbox(name='Use W2 control file to set Start Year', value=True)
        self.date_system_dropdown = pn.widgets.Select(options=['Day of Year', 'Standard Calendar'], name='Date System', width=200)
        self.start_year_input = TextInput(value=str(self.start_year), title='Start Year', disabled=False)
        self.date_system_dropdown.param.watch(self.update_date_system, 'value')
        self.skiprows_input = TextInput(value=str(self.skiprows), title='Number of Rows to Skip in ASCII Files')

        # Create HoloViews Div elements for the text labels
        w2_find_start_year_checkbox_label = "<span style='color: black; font-size: 14px; font-weight: normal'>CE-QUAL-W2 Options:</span>"
        browse_button_label = "<span style='color: black; font-size: 14px; font-weight: normal'>Open a File:</span>"

        # Create two sub-panels for the sidebar
        w2_subpanel = pn.layout.WidgetBox(
            w2_find_start_year_checkbox_label,
            self.w2_find_start_year_checkbox,
            self.start_year_input,
            self.skiprows_input,
            sizing_mode='stretch_width',
            max_width=300,
        )

        # Add a test button to verify button clicks work at all
        self.test_button = pn.widgets.Button(name='🔥 Test Click', button_type='success', width=120)
        self.test_button.on_click(self._test_button_click)
        
        # Add a simple file processing test button
        self.simple_process_button = pn.widgets.Button(name='Simple Process', button_type='warning', width=120)
        self.simple_process_button.on_click(self._simple_process_file)
        
        # Create a trigger widget that automatically processes when file is uploaded
        self.auto_process_toggle = pn.widgets.Toggle(
            name='Auto-Process on Upload', 
            value=True, 
            button_type='success'
        )
        
        # Watch the file input for changes
        self.file_input.param.watch(self._auto_process_file, 'value')
        
        browse_subpanel = pn.layout.WidgetBox(
            browse_button_label,
            self.file_input,
            self.auto_process_toggle,
            "**Optional: Upload w2_con.csv/npt for start year detection**",
            self.control_file_input,
            "---",
            "**Manual Controls (if auto-process fails):**",
            pn.Row(self.file_button, self.simple_process_button),
            pn.Row(self.test_button),
            sizing_mode='stretch_width',
            max_width=300,
        )

        # Create sidebar
        self.sidebar = pn.layout.WidgetBox(
            pn.pane.Markdown(
                sidebar_text,
                margin=(0, 10)
            ),
            self.date_system_dropdown,
            w2_subpanel,
            "",
            browse_subpanel,
            max_width=320,
            height=1000,
            sizing_mode='stretch_width',
            scroll=True
        ).servable(area='sidebar')

    def create_app(self):
        # Create the app and add the tabs
        self.create_sidebar()
        self.create_empty_tabs()
        self.tabs = pn.Tabs(
            ('Data', self.data_tab),
            ('Stats', self.stats_tab),
            ('Plot', self.plot_tab),
            ('Methods', self.methods_tab),
            ('About', self.about_tab),
            tabs_location='above',
            # background='blue',
            # sizing_mode='stretch_both',
            margin=(0, 0, 0, 0),
            css_classes=['panel-widget-box'],
        ).servable(title='ClearView Insights')

        # Create Main Layout
        self.main = pn.Row(self.sidebar, self.tabs)

        # Serve the web application
        self.main.show()


# Test the app
if __name__ == '__main__':
    clearview = ClearView()
    clearview.create_app()
