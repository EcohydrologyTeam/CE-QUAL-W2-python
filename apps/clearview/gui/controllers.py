"""
Controller components for ClearView application.
Handles business logic and coordinates between models and views.
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, Dict, Any
import PyQt5.QtWidgets as qtw
import PyQt5.QtCore as qtc

from .models import DataModel
from .views import ClearViewMainWindow


class ClearViewController:
    """Main controller for ClearView application."""
    
    def __init__(self):
        # Create model and view
        self.model = DataModel()
        self.view = ClearViewMainWindow()
        
        # Set up connections
        self._connect_signals()
        
        # Register as observer
        self.model.add_observer(self)
        
        # Load recent files
        self._load_recent_files()
    
    def _connect_signals(self):
        """Connect view signals to controller methods."""
        self.view.file_opened.connect(self.handle_file_open)
        self.view.cell_changed.connect(self.handle_cell_change)
        self.view.year_changed.connect(self.handle_year_change)
        self.view.filename_changed.connect(self.handle_filename_change)
        self.view.plot_requested.connect(self.handle_plot_request)
        self.view.multi_plot_requested.connect(self.handle_multi_plot_request)
        self.view.save_data_requested.connect(self.handle_save_data_request)
        self.view.save_stats_requested.connect(self.handle_save_stats_request)
        self.view.copy_requested.connect(self.handle_copy_request)
        self.view.paste_requested.connect(self.handle_paste_request)
        self.view.validation_requested.connect(self.handle_validation_request)
        self.view.filter_applied.connect(self.handle_filter_applied)
        self.view.duplicates_removal_requested.connect(self.handle_duplicates_removal)
        self.view.missing_data_handling_requested.connect(self.handle_missing_data_handling)
        self.view.custom_plot_requested.connect(self.handle_custom_plot_request)
        self.view.plot_export_requested.connect(self.handle_plot_export_request)
    
    def _load_recent_files(self):
        """Load recent files from settings."""
        # In a full implementation, this would load from QSettings
        # For now, just initialize empty
        self.view.update_recent_files_menu([])
    
    # Signal handlers
    def handle_file_open(self, file_path: str):
        """Handle file open request."""
        self.view.show_status_message(f"Loading {file_path}...")
        
        success = self.model.load_file(file_path)
        if success:
            self.view.show_status_message(f"Loaded {os.path.basename(file_path)}", 3000)
        else:
            self.view.show_status_message("Failed to load file", 3000)
    
    def handle_cell_change(self, row: int, col: int, value: str):
        """Handle table cell change."""
        try:
            # Convert value to appropriate type
            numeric_value = pd.to_numeric(value, errors='coerce')
            if not pd.isna(numeric_value):
                self.model.update_cell_value(row, col, numeric_value)
            else:
                self.model.update_cell_value(row, col, value)
        except Exception as e:
            self.view.show_message(f"Error updating cell: {str(e)}", 'error')
    
    def handle_year_change(self, year_text: str):
        """Handle year input change."""
        try:
            if year_text.strip():
                year = int(year_text)
                self.model.set_year(year)
        except ValueError:
            pass  # Invalid year input, ignore
    
    def handle_filename_change(self, filename: str):
        """Handle filename input change."""
        self.model.set_filename(filename)
    
    def handle_plot_request(self):
        """Handle plot request."""
        if self.model.df is None or self.model.df.empty:
            self.view.show_message("No data to plot", 'warning')
            return
        
        self._create_single_plot()
    
    def handle_multi_plot_request(self):
        """Handle multi-plot request."""
        if self.model.df is None or self.model.df.empty:
            self.view.show_message("No data to plot", 'warning')
            return
        
        self._create_multi_plot()
    
    def handle_save_data_request(self):
        """Handle save data request."""
        if self.model.df is None or self.model.df.empty:
            self.view.show_message("No data to save", 'warning')
            return
        
        self._save_data_dialog()
    
    def handle_save_stats_request(self):
        """Handle save statistics request."""
        if self.model.df is None or self.model.df.empty:
            self.view.show_message("No data for statistics", 'warning')
            return
        
        self._save_stats_dialog()
    
    def handle_copy_request(self):
        """Handle copy request."""
        # Get selected cells from data table
        selected_items = self.view.data_table.selectedItems()
        if not selected_items:
            return
        
        # Create clipboard text
        clipboard_text = self._create_clipboard_text(selected_items)
        clipboard = qtw.QApplication.clipboard()
        clipboard.setText(clipboard_text)
        
        self.view.show_status_message("Data copied to clipboard", 2000)
    
    def handle_paste_request(self):
        """Handle paste request."""
        clipboard = qtw.QApplication.clipboard()
        clipboard_text = clipboard.text()
        
        if not clipboard_text:
            return
        
        current_cell = self.view.data_table.currentItem()
        if current_cell is None:
            return
        
        self._paste_clipboard_data(clipboard_text, current_cell.row(), current_cell.column())
        self.view.show_status_message("Data pasted from clipboard", 2000)
    
    def handle_validation_request(self):
        """Handle data validation request."""
        if self.model.df is None or self.model.df.empty:
            self.view.show_message("No data to validate", 'warning')
            return
        
        # Perform validation
        validation_result = self.model.validate_data()
        
        # Update UI with results
        self.view.update_validation_results(validation_result)
        
        # Get and update column information
        column_info = self.model.get_column_info()
        self.view.update_column_info_table(column_info)
        
        # Show summary message
        status = "VALID" if validation_result.is_valid else "INVALID"
        issue_count = len(validation_result.issues)
        warning_count = len(validation_result.warnings)
        
        summary = f"Validation complete: {status}"
        if issue_count > 0:
            summary += f" ({issue_count} issues"
        if warning_count > 0:
            summary += f", {warning_count} warnings" if issue_count > 0 else f" ({warning_count} warnings"
        if issue_count > 0 or warning_count > 0:
            summary += ")"
        
        self.view.show_status_message(summary, 5000)
    
    def handle_filter_applied(self, filters):
        """Handle filter application request."""
        if self.model.df is None or self.model.df.empty:
            self.view.show_message("No data to filter", 'warning')
            return
        
        try:
            # Apply filters
            filtered_df = self.model.apply_filters(filters)
            
            # Update filtered data preview
            self.view.update_filtered_data_preview(filtered_df)
            
            # Show summary
            original_count = len(self.model.df)
            filtered_count = len(filtered_df)
            self.view.show_status_message(
                f"Filter applied: {filtered_count} of {original_count} rows match", 3000
            )
            
        except Exception as e:
            self.view.show_message(f"Error applying filters: {str(e)}", 'error')
    
    def handle_duplicates_removal(self):
        """Handle duplicate removal request."""
        if self.model.df is None or self.model.df.empty:
            self.view.show_message("No data loaded", 'warning')
            return
        
        initial_count = len(self.model.df)
        success = self.model.remove_duplicates()
        
        if success:
            final_count = len(self.model.df)
            removed_count = initial_count - final_count
            self.view.show_message(f"Removed {removed_count} duplicate rows")
            
            # Update UI
            self.view.update_data_table(self.model.df)
            self._update_statistics()
        else:
            self.view.show_message("No duplicate rows found")
    
    def handle_missing_data_handling(self, method_text: str):
        """Handle missing data handling request."""
        if self.model.df is None or self.model.df.empty:
            self.view.show_message("No data loaded", 'warning')
            return
        
        # Map method text to method names
        method_map = {
            "drop_missing": "drop",
            "fill_missing": "fill", 
            "interpolate": "interpolate"
        }
        
        method = method_map.get(method_text, "drop")
        
        initial_missing = self.model.df.isnull().sum().sum()
        if initial_missing == 0:
            self.view.show_message("No missing data found")
            return
        
        success = self.model.handle_missing_data(method)
        
        if success:
            final_missing = self.model.df.isnull().sum().sum()
            handled_count = initial_missing - final_missing
            self.view.show_message(f"Handled {handled_count} missing values using {method} method")
            
            # Update UI
            self.view.update_data_table(self.model.df)
            self._update_statistics()
        else:
            self.view.show_message(f"Failed to handle missing data with {method} method", 'error')
    
    def handle_custom_plot_request(self, config):
        """Handle custom plot creation request."""
        if self.model.df is None or self.model.df.empty:
            self.view.show_message("No data to plot", 'warning')
            return
        
        try:
            # Create the plot using the model's plotting functionality
            figure, ax = self.model.create_plot(config, self.view.get_figure())
            
            # Update the canvas
            self.view.get_canvas().draw()
            
            # Show success message
            plot_type_name = config.plot_type.value.replace('_', ' ').title()
            columns_text = ', '.join(config.y_columns or [])
            self.view.show_status_message(
                f"Created {plot_type_name} for columns: {columns_text}", 3000
            )
            
        except Exception as e:
            self.view.show_message(f"Error creating plot: {str(e)}", 'error')
    
    def handle_plot_export_request(self, format_type: str):
        """Handle plot export request."""
        # This is handled directly in the view for now
        pass
    
    # Model observer methods
    def on_data_changed(self, event_type: str, **kwargs):
        """Handle data model changes."""
        if event_type == 'data_loaded':
            self._update_ui_after_load()
        elif event_type == 'load_error':
            error = kwargs.get('error', 'Unknown error')
            self.view.show_message(f"Error loading file: {error}", 'error')
        elif event_type == 'data_saved':
            file_path = kwargs.get('file_path', '')
            self.view.show_message(f"Data saved to {os.path.basename(file_path)}")
        elif event_type == 'save_error':
            error = kwargs.get('error', 'Unknown error')
            self.view.show_message(f"Error saving file: {error}", 'error')
        elif event_type == 'cell_updated':
            self._update_statistics()
        elif event_type == 'year_updated':
            year = kwargs.get('year')
            self.view.set_year(year)
        elif event_type == 'filename_updated':
            filename = kwargs.get('filename')
            self.view.set_filename(filename)
    
    # Private helper methods
    def _update_ui_after_load(self):
        """Update UI components after data load."""
        # Update data table
        self.view.update_data_table(self.model.df)
        
        # Update statistics
        self._update_statistics()
        
        # Update year and filename
        self.view.set_year(self.model.model_year)
        self.view.set_filename(self.model.filename)
        
        # Update recent files menu
        self.view.update_recent_files_menu(self.model.recent_files)
        
        # Update filter columns
        if self.model.df is not None:
            columns = list(self.model.df.columns)
            self.view.update_filter_columns(columns)
            
            # Update plot columns
            self.view.update_plot_columns(columns)
            
            # Get and set plot recommendations
            recommendations = self.model.get_plot_recommendations()
            self.view.set_plot_recommendations(recommendations)
    
    def _update_statistics(self):
        """Update statistics table."""
        stats = self.model.get_statistics()
        self.view.update_stats_table(stats)
    
    def _create_single_plot(self):
        """Create a single plot of the data using enhanced plotting."""
        # Get numeric columns
        numeric_cols = list(self.model.df.select_dtypes(include=[np.number]).columns)
        
        if len(numeric_cols) == 0:
            self.view.show_message("No numeric data to plot", 'warning')
            return
        
        # Create a basic line plot configuration
        from models import PlotConfiguration, PlotType
        config = PlotConfiguration(
            plot_type=PlotType.LINE,
            y_columns=[numeric_cols[0]],
            title=f'{numeric_cols[0]} vs Index',
            xlabel='Index',
            ylabel=numeric_cols[0],
            grid=True,
            legend=False
        )
        
        try:
            self.model.create_plot(config, self.view.get_figure())
            self.view.get_canvas().draw()
        except Exception as e:
            self.view.show_message(f"Error creating plot: {str(e)}", 'error')
    
    def _create_multi_plot(self):
        """Create multiple subplots of the data using enhanced plotting."""
        # Get numeric columns
        numeric_cols = list(self.model.df.select_dtypes(include=[np.number]).columns)
        
        if len(numeric_cols) == 0:
            self.view.show_message("No numeric data to plot", 'warning')
            return
        
        # Determine subplot layout
        n_cols = min(len(numeric_cols), 2)
        n_rows = (len(numeric_cols) + n_cols - 1) // n_cols
        
        # Create multiple line plots
        from models import PlotConfiguration, PlotType
        config = PlotConfiguration(
            plot_type=PlotType.LINE,
            y_columns=numeric_cols[:6],  # Limit to 6 columns
            title='Multi-Column Plot',
            xlabel='Index',
            ylabel='Values',
            grid=True,
            legend=True,
            subplot_layout=(n_rows, n_cols)
        )
        
        try:
            self.model.create_plot(config, self.view.get_figure())
            self.view.get_canvas().draw()
        except Exception as e:
            self.view.show_message(f"Error creating multi-plot: {str(e)}", 'error')
    
    def _save_data_dialog(self):
        """Show save data dialog."""
        file_path, selected_filter = qtw.QFileDialog.getSaveFileName(
            self.view,
            "Save Data",
            f"{self.model.filename}_data",
            "SQLite (*.db);;HDF5 (*.h5);;Excel (*.xlsx);;CSV (*.csv)"
        )
        
        if file_path:
            # Determine format from filter
            if 'SQLite' in selected_filter:
                format_type = 'sqlite'
            elif 'HDF5' in selected_filter:
                format_type = 'hdf5'
            elif 'Excel' in selected_filter:
                format_type = 'excel'
            elif 'CSV' in selected_filter:
                format_type = 'csv'
            else:
                # Determine from extension
                ext = os.path.splitext(file_path)[1].lower()
                format_map = {'.db': 'sqlite', '.h5': 'hdf5', '.xlsx': 'excel', '.csv': 'csv'}
                format_type = format_map.get(ext, 'csv')
            
            self.model.save_to_format(file_path, format_type)
    
    def _save_stats_dialog(self):
        """Show save statistics dialog."""
        file_path, _ = qtw.QFileDialog.getSaveFileName(
            self.view,
            "Save Statistics",
            f"{self.model.filename}_stats.csv",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            stats = self.model.get_statistics()
            stats_df = pd.DataFrame(stats).T
            stats_df.to_csv(file_path)
            self.view.show_message(f"Statistics saved to {os.path.basename(file_path)}")
    
    def _create_clipboard_text(self, selected_items) -> str:
        """Create clipboard text from selected table items."""
        # Group items by row
        rows = {}
        for item in selected_items:
            row = item.row()
            col = item.column()
            if row not in rows:
                rows[row] = {}
            rows[row][col] = item.text()
        
        # Create tab-separated text
        lines = []
        for row_num in sorted(rows.keys()):
            row_data = rows[row_num]
            cols = sorted(row_data.keys())
            line = '\\t'.join(row_data[col] for col in cols)
            lines.append(line)
        
        return '\\n'.join(lines)
    
    def _paste_clipboard_data(self, clipboard_text: str, start_row: int, start_col: int):
        """Paste clipboard data into table."""
        lines = clipboard_text.strip().split('\\n')
        
        for row_offset, line in enumerate(lines):
            values = line.split('\\t')
            for col_offset, value in enumerate(values):
                row = start_row + row_offset
                col = start_col + col_offset
                
                # Check bounds
                if (row < self.view.data_table.rowCount() and 
                    col < self.view.data_table.columnCount()):
                    
                    # Update table
                    item = qtw.QTableWidgetItem(value)
                    self.view.data_table.setItem(row, col, item)
                    
                    # Update model
                    try:
                        numeric_value = pd.to_numeric(value, errors='coerce')
                        if not pd.isna(numeric_value):
                            self.model.update_cell_value(row, col, numeric_value)
                        else:
                            self.model.update_cell_value(row, col, value)
                    except Exception:
                        pass  # Ignore conversion errors
    
    def show(self):
        """Show the main window."""
        self.view.show()
    
    def close(self):
        """Close the application."""
        self.view.close()