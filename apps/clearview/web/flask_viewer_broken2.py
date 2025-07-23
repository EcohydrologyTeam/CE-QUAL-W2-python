#!/usr/bin/env python3
"""
Simple Flask-based data viewer for CE-QUAL-W2 data
Guaranteed to work without complex framework issues
"""

from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify, send_file, make_response
import flask
import pandas as pd
import io
import os
import re
import json
import plotly.graph_objs as go
import plotly.utils
import datetime
import numpy as np
from scipy import stats
import sqlite3
import h5py
import netCDF4 as nc
import tempfile
from io import BytesIO
import threading
import time
import random

app = Flask(__name__)
app.secret_key = 'clearview-secret-key'

# Global variable to store data
data_store = {
    'df': None,
    'filename': None,
    'stats': None,
    'validation': None,
    'file_info': None,
    'live_stream': False,
    'stream_thread': None,
    'stream_data': []
}

def detect_file_format_and_encoding(file_content, filename):
    """Detect file format and optimal reading parameters"""
    file_info = {
        'format': 'unknown',
        'encoding': 'utf-8',
        'separator': ',',
        'has_header': True,
        'decimal': '.',
        'ce_qual_w2_type': None
    }
    
    # Reset file position
    file_content.seek(0)
    
    # Try to read first few lines to detect format
    try:
        # Read first 1024 bytes to detect encoding and format
        sample = file_content.read(1024)
        file_content.seek(0)
        
        # Detect encoding
        for encoding in ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']:
            try:
                sample.decode(encoding)
                file_info['encoding'] = encoding
                break
            except UnicodeDecodeError:
                continue
        
        # Convert bytes to string for analysis
        sample_str = sample.decode(file_info['encoding'], errors='ignore')
        first_lines = sample_str.split('\n')[:5]
        
        # Detect separator (comma, semicolon, tab)
        separators = [',', ';', '\t', '|']
        separator_counts = {sep: sum(line.count(sep) for line in first_lines) for sep in separators}
        best_separator = max(separator_counts, key=separator_counts.get)
        if separator_counts[best_separator] > 0:
            file_info['separator'] = best_separator
        
        # Detect decimal separator
        if ',' in sample_str and file_info['separator'] != ',':
            # Check if commas might be decimal separators
            comma_as_decimal = any(re.search(r'\d+,\d+', line) for line in first_lines)
            if comma_as_decimal:
                file_info['decimal'] = ','
        
        # Detect CE-QUAL-W2 file types by looking for characteristic patterns
        sample_lower = sample_str.lower()
        if 'jday' in sample_lower or 'julian' in sample_lower:
            file_info['ce_qual_w2_type'] = 'TSR'  # Time Series
        elif 'segment' in sample_lower and 'layer' in sample_lower:
            file_info['ce_qual_w2_type'] = 'Profile'
        elif 'elws' in sample_lower or 'temperature' in sample_lower:
            file_info['ce_qual_w2_type'] = 'Water_Quality'
        
    except Exception as e:
        print(f"Warning: Format detection failed: {e}")
    
    return file_info

def read_file_with_validation(file_content, filename):
    """Enhanced file reading with format detection and validation"""
    file_info = detect_file_format_and_encoding(file_content, filename)
    
    try:
        # Determine file format from extension and content
        if filename.lower().endswith('.csv'):
            file_info['format'] = 'CSV'
            
            # Try different CSV reading strategies
            reading_params = {
                'sep': file_info['separator'],
                'encoding': file_info['encoding'],
                'decimal': file_info['decimal'],
                'on_bad_lines': 'skip'  # Skip malformed lines
            }
            
            try:
                df = pd.read_csv(file_content, **reading_params)
            except pd.errors.ParserError:
                # Fallback: try with different separator
                file_content.seek(0)
                df = pd.read_csv(file_content, sep=None, engine='python', encoding=file_info['encoding'])
                file_info['separator'] = 'auto-detected'
            except UnicodeDecodeError:
                # Fallback: try different encoding
                file_content.seek(0)
                df = pd.read_csv(file_content, encoding='latin1', sep=file_info['separator'])
                file_info['encoding'] = 'latin1'
                
        elif filename.lower().endswith(('.xlsx', '.xls')):
            file_info['format'] = 'Excel'
            
            try:
                df = pd.read_excel(file_content, engine='openpyxl' if filename.endswith('.xlsx') else 'xlrd')
            except Exception:
                # Try alternative engine
                file_content.seek(0)
                df = pd.read_excel(file_content)
                
        else:
            # Try to auto-detect format
            file_content.seek(0)
            
            # First try as CSV
            try:
                df = pd.read_csv(file_content, sep=None, engine='python', encoding='utf-8')
                file_info['format'] = 'CSV (auto-detected)'
            except Exception:
                # Then try as Excel
                file_content.seek(0)
                try:
                    df = pd.read_excel(file_content)
                    file_info['format'] = 'Excel (auto-detected)'
                except Exception:
                    raise ValueError(f'Unsupported file format for {filename}. Please use CSV or Excel files.')
        
        # Basic data frame validation
        if df.empty:
            raise ValueError('File is empty or contains no readable data')
        
        if len(df.columns) == 0:
            raise ValueError('No columns detected in file')
        
        # Clean up column names
        df.columns = df.columns.astype(str).str.strip()
        
        # Remove completely empty columns
        df = df.dropna(axis=1, how='all')
        
        return df, file_info
        
    except Exception as e:
        # Re-raise with more context
        raise Exception(f'File reading failed: {str(e)}')

def validate_data_quality(df, filename):
    """Comprehensive data quality validation with CE-QUAL-W2 specific checks"""
    validation_results = {
        'warnings': [],
        'info': [],
        'data_quality_score': 100,  # Start with perfect score
        'missing_data_summary': {},
        'suspicious_values': {},
        'ce_qual_w2_validation': {}
    }
    
    try:
        # 1. Missing data analysis
        total_cells = df.size
        missing_cells = df.isnull().sum().sum()
        missing_percentage = (missing_cells / total_cells) * 100
        
        if missing_percentage > 0:
            validation_results['missing_data_summary'] = {
                'total_missing': missing_cells,
                'percentage': missing_percentage,
                'by_column': df.isnull().sum().to_dict()
            }
            
            if missing_percentage > 50:
                validation_results['warnings'].append(f'High missing data: {missing_percentage:.1f}% of values are missing')
                validation_results['data_quality_score'] -= 30
            elif missing_percentage > 20:
                validation_results['warnings'].append(f'Moderate missing data: {missing_percentage:.1f}% of values are missing')
                validation_results['data_quality_score'] -= 15
            elif missing_percentage > 5:
                validation_results['info'].append(f'Some missing data: {missing_percentage:.1f}% of values are missing')
                validation_results['data_quality_score'] -= 5
        
        # 2. Suspicious value detection
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        for col in numeric_cols:
            col_data = df[col].dropna()
            if len(col_data) == 0:
                continue
                
            # Check for extreme outliers (beyond 3 standard deviations)
            if len(col_data) > 10:  # Need sufficient data for statistics
                mean_val = col_data.mean()
                std_val = col_data.std()
                
                if std_val > 0:
                    outliers = col_data[abs((col_data - mean_val) / std_val) > 3]
                    if len(outliers) > 0:
                        validation_results['suspicious_values'][col] = {
                            'outliers_count': len(outliers),
                            'outlier_values': outliers.tolist()[:5]  # Show first 5
                        }
                        
                        if len(outliers) > len(col_data) * 0.1:  # More than 10% outliers
                            validation_results['warnings'].append(f'Many outliers in {col}: {len(outliers)} values')
                            validation_results['data_quality_score'] -= 10
            
            # CE-QUAL-W2 specific value range checks
            validation_results['ce_qual_w2_validation'].update(validate_ce_qual_w2_ranges(col, col_data))
        
        # 3. Time series validation
        time_cols = [col for col in df.columns if any(term in col.lower() for term in ['jday', 'julian', 'date', 'time'])]
        if time_cols:
            validation_results['info'].append(f'Time columns detected: {", ".join(time_cols)}')
            
            # Check for time continuity
            for time_col in time_cols:
                if df[time_col].dtype in ['float64', 'int64']:
                    # Check JDAY continuity
                    time_data = df[time_col].dropna().sort_values()
                    if len(time_data) > 1:
                        time_diff = time_data.diff().dropna()
                        irregular_intervals = time_diff[time_diff > time_diff.median() * 3]
                        
                        if len(irregular_intervals) > 0:
                            validation_results['warnings'].append(f'Irregular time intervals in {time_col}')
                            validation_results['data_quality_score'] -= 5
        
        # 4. Data type consistency checks
        mixed_type_cols = []
        for col in df.columns:
            if df[col].dtype == 'object':
                # Check if column should be numeric
                numeric_attempts = pd.to_numeric(df[col], errors='coerce')
                if not numeric_attempts.isnull().all() and numeric_attempts.isnull().sum() > 0:
                    mixed_type_cols.append(col)
        
        if mixed_type_cols:
            validation_results['warnings'].append(f'Mixed data types in columns: {", ".join(mixed_type_cols)}')
            validation_results['data_quality_score'] -= 10
        
        # 5. File structure validation
        if len(df.columns) < 2:
            validation_results['warnings'].append('Very few columns - check if data loaded correctly')
            validation_results['data_quality_score'] -= 20
        
        if len(df) < 10:
            validation_results['warnings'].append('Very few rows - check if complete dataset loaded')
            validation_results['data_quality_score'] -= 10
        
        # Final quality assessment
        score = validation_results['data_quality_score']
        if score >= 90:
            validation_results['quality_level'] = 'Excellent'
        elif score >= 75:
            validation_results['quality_level'] = 'Good'
        elif score >= 60:
            validation_results['quality_level'] = 'Fair'
        else:
            validation_results['quality_level'] = 'Poor'
            validation_results['warnings'].append('Overall data quality is poor - review warnings above')
        
    except Exception as e:
        validation_results['warnings'].append(f'Validation error: {str(e)}')
    
    return validation_results

def validate_ce_qual_w2_ranges(column_name, data):
    """Validate CE-QUAL-W2 parameter ranges"""
    validation = {}
    col_lower = column_name.lower()
    
    # Common CE-QUAL-W2 parameter ranges
    parameter_ranges = {
        'temperature': (0, 50),     # Celsius
        'temp': (0, 50),
        't(c)': (0, 50),
        'dissolved_oxygen': (0, 20), # mg/L
        'do': (0, 20),
        'ph': (0, 14),
        'turbidity': (0, 1000),     # NTU
        'chlorophyll': (0, 500),    # µg/L
        'chla': (0, 500),
        'conductivity': (0, 2000),  # µS/cm
        'elws': (-100, 1000),       # Elevation (m)
        'depth': (0, 200),          # Depth (m)
        'velocity': (0, 10),        # m/s
        'flow': (0, 10000),         # m³/s
    }
    
    for param, (min_val, max_val) in parameter_ranges.items():
        if param in col_lower:
            out_of_range = data[(data < min_val) | (data > max_val)]
            if len(out_of_range) > 0:
                validation[column_name] = {
                    'parameter': param,
                    'expected_range': f'{min_val}-{max_val}',
                    'out_of_range_count': len(out_of_range),
                    'out_of_range_values': out_of_range.tolist()[:5]
                }
            break
    
    return validation

def _ensure_datetime_index(df, filename):
    """Ensure the dataframe has a proper datetime index"""
    try:
        # First, check if there's already a Date column
        if 'Date' in df.columns:
            try:
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                return df
            except:
                pass
        
        # Check for JDAY column (Julian Day)
        jday_columns = [col for col in df.columns if 'jday' in col.lower() or 'julian' in col.lower()]
        if jday_columns:
            jday_col = jday_columns[0]
            try:
                # Extract start year from filename or use current year
                start_year = _extract_start_year(filename)
                
                # Convert JDAY to datetime
                # JDAY 1.0 = January 1st of the start year
                start_date = datetime.datetime(start_year, 1, 1)
                df['Date'] = pd.to_datetime(start_date) + pd.to_timedelta(df[jday_col] - 1, unit='D')
                df.set_index('Date', inplace=True)
                return df
            except Exception as e:
                print(f"Error converting JDAY: {e}")
        
        # If no datetime info found, create a datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            # Extract start year or use current year
            start_year = _extract_start_year(filename)
            start_date = pd.Timestamp(year=start_year, month=1, day=1)
            date_range = pd.date_range(start=start_date, periods=len(df), freq='D')
            df.index = date_range
            df.index.name = 'Date'
            
        return df
    except Exception as e:
        print(f"Error in _ensure_datetime_index: {e}")
        # Fallback - create simple datetime index with current year
        start_date = pd.Timestamp(year=datetime.datetime.now().year, month=1, day=1)
        date_range = pd.date_range(start=start_date, periods=len(df), freq='D')
        df.index = date_range
        df.index.name = 'Date'
        return df

def _extract_start_year(filename):
    """Extract start year from filename or other sources"""
    # Look for year patterns in filename
    import re
    year_match = re.search(r'(19|20)\d{2}', filename or '')
    if year_match:
        return int(year_match.group())
    
    # Default to current year
    return datetime.datetime.now().year

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ClearView - CE-QUAL-W2 Data Viewer</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { background: #00aedb; color: black; padding: 20px; margin: -20px -20px 20px -20px; border-radius: 8px 8px 0 0; }
        .upload-area { border: 2px dashed #00aedb; padding: 30px; text-align: center; margin: 20px 0; border-radius: 8px; }
        .btn { background: #00aedb; color: black; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; font-weight: bold; }
        .btn:hover { background: gold; }
        .success { background: #d4edda; color: #155724; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .error { background: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat-box { background: #ecf0f1; padding: 15px; border-radius: 4px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
        .stat-label { color: #7f8c8d; font-size: 14px; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #f2f2f2; font-weight: bold; }
        .table-container { max-height: 400px; overflow: auto; border: 1px solid #ddd; }
        .tabs { display: flex; margin: 20px 0 0 0; }
        .tab { background: gold; color: black; padding: 10px 20px; cursor: pointer; border: 1px solid #bdc3c7; margin-right: 2px; font-size: 14px; width: 100px; text-align: center; font-weight: bold; }
        .tab.active { background: #00aedb; color: black; }
        .tab-content { border: 1px solid #bdc3c7; padding: 20px; }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        @keyframes highlight {
            0% { background-color: #f39c12; }
            100% { background-color: transparent; }
        }
        
        .interactive-controls {
            background: #ecf0f1;
            padding: 15px;
            border-radius: 4px;
            margin: 10px 0;
        }
        
        .refresh-indicator {
            color: #27ae60;
            font-size: 12px;
            display: none;
        }
        
        .data-selection {
            background: #e8f5e8;
            border: 1px solid #27ae60;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
            display: none;
        }
        
        .hover-info {
            position: absolute;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
            pointer-events: none;
            z-index: 1000;
        }
        
        .monitoring-dashboard {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 15px;
            border-radius: 4px;
            margin: 10px 0;
            display: none;
        }
        
        .monitor-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin: 10px 0;
        }
        
        .monitor-item {
            display: flex;
            justify-content: space-between;
            padding: 5px;
            background: rgba(255, 255, 255, 0.7);
            border-radius: 3px;
        }
        
        .monitor-label {
            font-weight: bold;
        }
        
        .monitor-value {
            color: #2c3e50;
            font-family: monospace;
        }
        
        .alert {
            background: #f8d7da;
            color: #721c24;
            padding: 8px;
            border-radius: 3px;
            margin: 5px 0;
            font-weight: bold;
        }
    </style>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <script>
        // Global error handler
        window.addEventListener('error', function(e) {
            console.error('JavaScript error:', e.error, e.filename, e.lineno);
        });
        
        // File upload progress handling
        document.addEventListener('DOMContentLoaded', function() {
            const uploadForm = document.getElementById('upload-form');
            const fileInput = document.getElementById('file-input');
            const uploadProgress = document.getElementById('upload-progress');
            const progressStatus = document.getElementById('progress-status');
            const progressBar = document.getElementById('progress-bar');
            
            if (uploadForm) {
                uploadForm.addEventListener('submit', function(e) {
                    const file = fileInput.files[0];
                    if (file) {
                        // Show progress indicator
                        uploadProgress.style.display = 'block';
                        
                        // Simulate progress stages
                        let progress = 0;
                        const stages = [
                            { progress: 20, status: 'Reading file format...' },
                            { progress: 40, status: 'Loading data...' },
                            { progress: 60, status: 'Validating data quality...' },
                            { progress: 80, status: 'Processing datetime indices...' },
                            { progress: 95, status: 'Finalizing...' }
                        ];
                        
                        let stageIndex = 0;
                        const updateProgress = () => {
                            if (stageIndex < stages.length) {
                                const stage = stages[stageIndex];
                                progressBar.style.width = stage.progress + '%';
                                progressStatus.textContent = stage.status;
                                stageIndex++;
                                setTimeout(updateProgress, 200 + Math.random() * 300); // Random timing
                            }
                        };
                        
                        // Start progress simulation
                        updateProgress();
                        
                        // Show file size info
                        const fileSizeMB = (file.size / (1024 * 1024)).toFixed(1);
                        if (fileSizeMB > 10) {
                            progressStatus.textContent += ` (${fileSizeMB}MB - This may take a moment)`;
                        }
                    }
                });
                
                // File input change handler
                fileInput.addEventListener('change', function(e) {
                    const file = e.target.files[0];
                    if (file) {
                        const fileSizeMB = (file.size / (1024 * 1024)).toFixed(1);
                        if (fileSizeMB > 50) {
                            alert(`Warning: Large file (${fileSizeMB}MB). Upload may take several minutes.`);
                        }
                    }
                });
            }
        });
        
        function closeData() {
            if (confirm('Are you sure you want to close this file and clear all data?')) {
                // Send request to clear data
                fetch('/clear_data', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Reload the page to show upload form
                        window.location.reload();
                    } else {
                        alert('Error clearing data');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error clearing data');
                });
            }
        }
        
        function showTab(tabName) {
            console.log('Switching to tab:', tabName);
            
            // Hide all tab contents
            var contents = document.querySelectorAll('.tab-content');
            for (var i = 0; i < contents.length; i++) {
                contents[i].style.display = 'none';
            }
            
            // Remove active class from all tab buttons
            var tabs = document.querySelectorAll('.tab');
            for (var i = 0; i < tabs.length; i++) {
                tabs[i].classList.remove('active');
            }
            
            // Show the selected tab content
            var targetContent = document.getElementById(tabName);
            if (targetContent) {
                targetContent.style.display = 'block';
                console.log('Showed content for:', tabName);
            } else {
                console.error('Content not found for tab:', tabName);
            }
            
            // Add active class to the clicked tab button (use event.target)
            if (event && event.target) {
                event.target.classList.add('active');
                console.log('Activated clicked button');
            } else {
                // Fallback: find button by matching onclick content
                for (var i = 0; i < tabs.length; i++) {
                    var onclick = tabs[i].getAttribute('onclick');
                    if (onclick && onclick.includes("'" + tabName + "'")) {
                        tabs[i].classList.add('active');
                        break;
                    }
                }
            }
            
            console.log('Tab switching completed successfully');
        }
        
        function updatePlot() {
            var xColumn = document.getElementById('x-column').value;
            
            // Get selected Y columns from multi-select dropdown
            var yColumnsSelect = document.getElementById('y-columns');
            var yColumns = [];
            for (var i = 0; i < yColumnsSelect.selectedOptions.length; i++) {
                yColumns.push(yColumnsSelect.selectedOptions[i].value);
            }
            
            if (yColumns.length === 0) {
                document.getElementById('plot-container').innerHTML = 
                    '<p style="text-align: center; color: #e74c3c; padding: 50px;">Please select at least one Y-axis parameter</p>';
                return;
            }
            
            document.getElementById('plot-container').innerHTML = 
                '<p style="text-align: center; color: #3498db; padding: 50px;">Loading plot...</p>';
            
            // Get plot options
            var showMarkers = document.getElementById('show-markers').checked;
            var showGrid = document.getElementById('show-grid').checked;
            var dualYAxis = document.getElementById('dual-yaxis').checked;
            var subplotMode = document.getElementById('subplot-mode').value;
            var colorScheme = document.getElementById('color-scheme').value;
            var lineStyle = document.getElementById('line-style').value;
            
            // Make API call to get multi-column plot data
            fetch('/plot_data_multi', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    x_column: xColumn,
                    y_columns: yColumns,
                    show_markers: showMarkers,
                    show_grid: showGrid,
                    dual_yaxis: dualYAxis,
                    subplot_mode: subplotMode,
                    color_scheme: colorScheme,
                    line_style: lineStyle,
                    filters: window.currentFilters || null
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('plot-container').innerHTML = 
                        '<p style="text-align: center; color: #e74c3c; padding: 50px;">Error: ' + data.error + '</p>';
                    return;
                }
                
                // Create multi-trace Plotly plot
                var plotData = data.traces;
                var layout = data.layout;
                var frames = data.frames || [];
                
                // Apply responsive settings
                layout.autosize = true;
                layout.margin = {t: 50, l: 60, r: dualYAxis ? 60 : 20, b: 60};
                
                // Enhanced interactivity configuration
                var config = {
                    responsive: true,
                    displayModeBar: true,
                    modeBarButtonsToAdd: [
                        {
                            name: 'Filter Data',
                            icon: Plotly.Icons.selectbox,
                            click: function(gd) {
                                showDataFilterDialog();
                            }
                        },
                        {
                            name: 'Reset View',
                            icon: Plotly.Icons.home,
                            click: function(gd) {
                                Plotly.relayout(gd, {
                                    'xaxis.autorange': true,
                                    'yaxis.autorange': true
                                });
                            }
                        }
                    ],
                    toImageButtonOptions: {
                        format: 'png',
                        filename: 'clearview_plot',
                        height: 600,
                        width: 800,
                        scale: 2
                    }
                };
                
                // Create plot with or without animation frames
                if (frames.length > 0) {
                    Plotly.newPlot('plot-container', plotData, layout, config).then(function() {
                        Plotly.addFrames('plot-container', frames);
                    });
                } else {
                    Plotly.newPlot('plot-container', plotData, layout, config);
                }
                
                // Store plot data for export
                window.currentPlotData = plotData;
                window.currentPlotLayout = layout;
                
                // Enable plot interactivity
                addPlotInteractivity();
            })
            .catch(error => {
                document.getElementById('plot-container').innerHTML = 
                    '<p style="text-align: center; color: #e74c3c; padding: 50px;">Error creating plot: ' + error + '</p>';
            });
        }
        
        function exportPlot() {
            if (!window.currentPlotData) {
                alert('No plot data available. Please create a plot first.');
                return;
            }
            document.getElementById('plot-export-options').style.display = 'block';
        }
        
        // Auto-refresh functionality
        let autoRefreshInterval = null;
        
        function toggleAutoRefresh() {
            const checkbox = document.getElementById('auto-refresh');
            const intervalSelect = document.getElementById('refresh-interval');
            
            if (checkbox.checked) {
                const intervalSeconds = parseInt(intervalSelect.value);
                autoRefreshInterval = setInterval(() => {
                    updatePlot();
                    updateDataStats();
                }, intervalSeconds * 1000);
                
                // Add visual indicator
                const indicator = document.getElementById('refresh-indicator');
                if (indicator) {
                    indicator.style.display = 'inline';
                    indicator.style.animation = 'pulse 2s infinite';
                }
            } else {
                if (autoRefreshInterval) {
                    clearInterval(autoRefreshInterval);
                    autoRefreshInterval = null;
                }
                
                // Hide visual indicator
                const indicator = document.getElementById('refresh-indicator');
                if (indicator) {
                    indicator.style.display = 'none';
                }
            }
        }
        
        function updateDataStats() {
            // Refresh data statistics if available
            fetch('/get_stats', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.stats) {
                        // Update stats display without full page reload
                        updateStatsDisplay(data.stats);
                    }
                })
                .catch(error => console.log('Stats update failed:', error));
        }
        
        function updateStatsDisplay(stats) {
            // Update individual stat elements
            const elements = {
                'rows': stats.rows,
                'columns': stats.columns,
                'missing': stats.missing_values,
                'score': stats.quality_score
            };
            
            Object.entries(elements).forEach(([key, value]) => {
                const element = document.getElementById(`stat-${key}`);
                if (element) {
                    element.textContent = value;
                    // Add update animation
                    element.style.animation = 'highlight 1s ease-out';
                    setTimeout(() => element.style.animation = '', 1000);
                }
            });
        }
        
        // Interactive plot controls
        function addPlotInteractivity() {
            const plotDiv = document.getElementById('plot-container');
            if (!plotDiv) return;
            
            // Add zoom reset button
            plotDiv.addEventListener('plotly_relayout', function(eventData) {
                if (eventData['xaxis.autorange'] || eventData['yaxis.autorange']) {
                    // Auto-range was triggered
                    console.log('Plot auto-ranged');
                }
            });
            
            // Add data selection handler
            plotDiv.addEventListener('plotly_selected', function(eventData) {
                if (eventData && eventData.points) {
                    showDataSelection(eventData.points);
                }
            });
            
            // Add hover data display
            plotDiv.addEventListener('plotly_hover', function(eventData) {
                if (eventData.points && eventData.points.length > 0) {
                    updateHoverInfo(eventData.points[0]);
                }
            });
        }
        
        function showDataSelection(points) {
            const selectionDiv = document.getElementById('data-selection');
            if (!selectionDiv) return;
            
            selectionDiv.innerHTML = `
                <h4>Selected Data Points (${points.length})</h4>
                <div class="selection-stats">
                    <p><strong>Range:</strong> ${points.length} points selected</p>
                    <button onclick="exportSelection()" class="btn">Export Selection</button>
                    <button onclick="clearSelection()" class="btn">Clear Selection</button>
                </div>
            `;
            selectionDiv.style.display = 'block';
        }
        
        function updateHoverInfo(point) {
            const hoverDiv = document.getElementById('hover-info');
            if (!hoverDiv) return;
            
            hoverDiv.innerHTML = `
                <strong>${point.data.name}:</strong> ${point.y}<br>
                <strong>Time:</strong> ${point.x}<br>
                <strong>Point:</strong> ${point.pointIndex + 1}
            `;
        }
        
        function clearSelection() {
            Plotly.restyle('plot-container', {'selectedpoints': [null]});
            document.getElementById('data-selection').style.display = 'none';
        }
        
        function exportSelection() {
            // Get selected points and export them
            const plotDiv = document.getElementById('plot-container');
            const selectedData = plotDiv.data.map(trace => {
                if (trace.selectedpoints) {
                    return {
                        name: trace.name,
                        points: trace.selectedpoints.map(idx => ({
                            x: trace.x[idx],
                            y: trace.y[idx]
                        }))
                    };
                }
                return null;
            }).filter(Boolean);
            
            if (selectedData.length === 0) {
                alert('No data points selected');
                return;
            }
            
            // Create CSV from selection
            let csv = 'Parameter,X,Y\n';
            selectedData.forEach(trace => {
                trace.points.forEach(point => {
                    csv += `${trace.name},${point.x},${point.y}\n`;
                });
            });
            
            // Download CSV
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'selected_data.csv';
            a.click();
            window.URL.revokeObjectURL(url);
        }
        
        // Real-time parameter monitoring
        function startParameterMonitoring() {
            const checkbox = document.getElementById('parameter-monitoring');
            const parameterSelect = document.getElementById('monitor-parameter');
            
            if (checkbox.checked) {
                const parameter = parameterSelect.value;
                if (!parameter) {
                    alert('Please select a parameter to monitor');
                    checkbox.checked = false;
                    return;
                }
                
                // Start monitoring
                monitorParameter(parameter);
                
                // Show monitoring dashboard
                document.getElementById('monitoring-dashboard').style.display = 'block';
            } else {
                // Stop monitoring
                if (window.monitoringInterval) {
                    clearInterval(window.monitoringInterval);
                    window.monitoringInterval = null;
                }
                document.getElementById('monitoring-dashboard').style.display = 'none';
            }
        }
        
        function monitorParameter(parameter) {
            window.monitoringInterval = setInterval(() => {
                fetch('/monitor_parameter', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ parameter: parameter })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.stats) {
                        updateMonitoringDisplay(data.stats);
                    }
                })
                .catch(error => console.log('Monitoring update failed:', error));
            }, 5000); // Update every 5 seconds
        }
        
        function updateMonitoringDisplay(stats) {
            const dashboard = document.getElementById('monitoring-dashboard');
            if (!dashboard) return;
            
            const timestamp = new Date().toLocaleTimeString();
            dashboard.innerHTML = `
                <h4>Real-time Parameter Monitoring</h4>
                <div class="monitor-stats">
                    <div class="monitor-item">
                        <span class="monitor-label">Current Value:</span>
                        <span class="monitor-value">${(stats.current_value && stats.current_value.toFixed(3)) || 'N/A'}</span>
                    </div>
                    <div class="monitor-item">
                        <span class="monitor-label">Average:</span>
                        <span class="monitor-value">${(stats.mean && stats.mean.toFixed(3)) || 'N/A'}</span>
                    </div>
                    <div class="monitor-item">
                        <span class="monitor-label">Std Dev:</span>
                        <span class="monitor-value">${(stats.std && stats.std.toFixed(3)) || 'N/A'}</span>
                    </div>
                    <div class="monitor-item">
                        <span class="monitor-label">Last Updated:</span>
                        <span class="monitor-value">${timestamp}</span>
                    </div>
                </div>
                ${stats.alert ? `<div class="alert">${stats.alert}</div>` : ''}
            `;
        }
        
        // Data filtering functionality
        function showDataFilterDialog() {
            const filterHtml = `
                <div id="filter-dialog" style="position: fixed; top: 20%; left: 50%; transform: translateX(-50%); 
                     background: white; border: 2px solid #00aedb; border-radius: 8px; padding: 20px; 
                     box-shadow: 0 4px 20px rgba(0,0,0,0.3); z-index: 10000; min-width: 400px;">
                    <h3 style="margin-top: 0;">🔍 Filter Plot Data</h3>
                    <div style="margin: 15px 0;">
                        <label for="filter-parameter">Parameter to filter:</label>
                        <select id="filter-parameter" style="width: 100%; margin-top: 5px;">
                            <option value="">Select parameter...</option>
                        </select>
                    </div>
                    <div style="margin: 15px 0;">
                        <label for="filter-min">Minimum value:</label>
                        <input type="number" id="filter-min" style="width: 100%; margin-top: 5px;" step="any">
                    </div>
                    <div style="margin: 15px 0;">
                        <label for="filter-max">Maximum value:</label>
                        <input type="number" id="filter-max" style="width: 100%; margin-top: 5px;" step="any">
                    </div>
                    <div style="text-align: center; margin-top: 20px;">
                        <button onclick="applyDataFilter()" class="btn" style="margin-right: 10px;">Apply Filter</button>
                        <button onclick="clearDataFilter()" class="btn" style="background: #6c757d; margin-right: 10px;">Clear Filter</button>
                        <button onclick="closeFilterDialog()" class="btn" style="background: #dc3545;">Cancel</button>
                    </div>
                </div>
                <div id="filter-backdrop" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                     background: rgba(0,0,0,0.5); z-index: 9999;" onclick="closeFilterDialog()"></div>
            `;
            
            document.body.insertAdjacentHTML('beforeend', filterHtml);
            
            // Populate parameter options
            const yColumnsSelect = document.getElementById('y-columns');
            const filterSelect = document.getElementById('filter-parameter');
            for (let i = 0; i < yColumnsSelect.options.length; i++) {
                const option = yColumnsSelect.options[i];
                if (option.selected) {
                    filterSelect.innerHTML += `<option value="${option.value}">${option.value}</option>`;
                }
            }
        }
        
        function closeFilterDialog() {
            const dialog = document.getElementById('filter-dialog');
            const backdrop = document.getElementById('filter-backdrop');
            if (dialog) dialog.remove();
            if (backdrop) backdrop.remove();
        }
        
        function applyDataFilter() {
            const parameter = document.getElementById('filter-parameter').value;
            const minValue = document.getElementById('filter-min').value;
            const maxValue = document.getElementById('filter-max').value;
            
            if (!parameter && !minValue && !maxValue) {
                alert('Please specify at least one filter criterion');
                return;
            }
            
            // Apply filters by adding them to the plot request
            window.currentFilters = {
                parameter: parameter,
                min_value: minValue ? parseFloat(minValue) : null,
                max_value: maxValue ? parseFloat(maxValue) : null
            };
            
            updatePlot();
            closeFilterDialog();
        }
        
        function clearDataFilter() {
            window.currentFilters = null;
            updatePlot();
            closeFilterDialog();
        }
        
        // Live data streaming functionality
        let liveStreamInterval = null;
        
        function toggleLiveStreaming() {
            const checkbox = document.getElementById('live-streaming');
            const parameterSelect = document.getElementById('stream-parameter');
            
            if (checkbox.checked) {
                const parameter = parameterSelect.value;
                if (!parameter) {
                    alert('Please select a parameter for live streaming');
                    checkbox.checked = false;
                    return;
                }
                
                // Start live streaming
                fetch('/start_live_stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        startLiveDataUpdates(parameter);
                        
                        // Show streaming indicator
                        const indicator = document.getElementById('stream-indicator');
                        if (indicator) {
                            indicator.style.display = 'inline';
                            indicator.style.animation = 'pulse 1s infinite';
                        }
                    } else {
                        alert('Failed to start live streaming: ' + data.error);
                        checkbox.checked = false;
                    }
                })
                .catch(error => {
                    console.error('Error starting live stream:', error);
                    alert('Error starting live streaming');
                    checkbox.checked = false;
                });
            } else {
                // Stop live streaming
                fetch('/stop_live_stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                })
                .then(response => response.json())
                .then(data => {
                    if (liveStreamInterval) {
                        clearInterval(liveStreamInterval);
                        liveStreamInterval = null;
                    }
                    
                    // Hide streaming indicator
                    const indicator = document.getElementById('stream-indicator');
                    if (indicator) {
                        indicator.style.display = 'none';
                    }
                    
                    // Hide live streaming dashboard
                    const dashboard = document.getElementById('live-stream-dashboard');
                    if (dashboard) {
                        dashboard.style.display = 'none';
                    }
                });
            }
        }
        
        function startLiveDataUpdates(parameter) {
            // Create live streaming dashboard if it doesn't exist
            const existingDashboard = document.getElementById('live-stream-dashboard');
            if (!existingDashboard) {
                const dashboardHtml = `
                    <div id="live-stream-dashboard" class="monitoring-dashboard" style="background: #e8f5e8; border-color: #28a745;">
                        <h4>📡 Live Data Streaming</h4>
                        <div id="live-stream-content">
                            <!-- Content will be populated by JavaScript -->
                        </div>
                        <div id="live-stream-chart" style="height: 200px; margin-top: 10px;">
                            <!-- Live chart will be rendered here -->
                        </div>
                    </div>
                `;
                document.getElementById('monitoring-dashboard').insertAdjacentHTML('afterend', dashboardHtml);
            }
            
            document.getElementById('live-stream-dashboard').style.display = 'block';
            
            // Poll for live data updates
            liveStreamInterval = setInterval(() => {
                fetch('/get_live_data', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ parameter: parameter })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.data) {
                        updateLiveStreamDisplay(data.data, data.stats, parameter);
                    }
                })
                .catch(error => console.log('Live data update failed:', error));
            }, 2000); // Update every 2 seconds
        }
        
        function updateLiveStreamDisplay(liveData, stats, parameter) {
            const contentDiv = document.getElementById('live-stream-content');
            const chartDiv = document.getElementById('live-stream-chart');
            
            if (!contentDiv || !chartDiv) return;
            
            const timestamp = new Date().toLocaleTimeString();
            
            // Update stats display
            contentDiv.innerHTML = `
                <div class="monitor-stats">
                    <div class="monitor-item">
                        <span class="monitor-label">Parameter:</span>
                        <span class="monitor-value">${parameter}</span>
                    </div>
                    <div class="monitor-item">
                        <span class="monitor-label">Live Value:</span>
                        <span class="monitor-value">${(stats && stats.current && stats.current.toFixed(3)) || 'N/A'}</span>
                    </div>
                    <div class="monitor-item">
                        <span class="monitor-label">Stream Avg:</span>
                        <span class="monitor-value">${(stats && stats.mean && stats.mean.toFixed(3)) || 'N/A'}</span>
                    </div>
                    <div class="monitor-item">
                        <span class="monitor-label">Trend:</span>
                        <span class="monitor-value">${(stats && stats.trend) || 'stable'}</span>
                    </div>
                    <div class="monitor-item">
                        <span class="monitor-label">Points:</span>
                        <span class="monitor-value">${(stats && stats.count) || 0}</span>
                    </div>
                    <div class="monitor-item">
                        <span class="monitor-label">Updated:</span>
                        <span class="monitor-value">${timestamp}</span>
                    </div>
                </div>
            `;
            
            // Update live chart
            if (liveData && liveData.length > 0) {
                const timestamps = liveData.map(d => new Date(d.timestamp));
                const values = liveData.map(d => d.value);
                
                const trace = {
                    x: timestamps,
                    y: values,
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: `Live ${parameter}`,
                    line: { color: '#28a745', width: 2 },
                    marker: { size: 4 }
                };
                
                const layout = {
                    title: { text: `Live ${parameter} Stream`, font: { size: 14 } },
                    xaxis: { title: 'Time', tickformat: '%H:%M:%S' },
                    yaxis: { title: parameter },
                    margin: { t: 40, l: 60, r: 20, b: 40 },
                    showlegend: false,
                    plot_bgcolor: '#f8f9fa'
                };
                
                Plotly.newPlot(chartDiv, [trace], layout, { responsive: true, displayModeBar: false });
            }
        }
        
        // WQI parameter selection toggle
        document.addEventListener('DOMContentLoaded', function() {
            const wqiType = document.getElementById('wqi-type');
            const customParams = document.getElementById('custom-wqi-params');
            
            if (wqiType && customParams) {
                wqiType.addEventListener('change', function() {
                    if (this.value === 'custom') {
                        customParams.style.display = 'block';
                    } else {
                        customParams.style.display = 'none';
                    }
                });
            }
        });
        
        function runCorrelationAnalysis() {
            document.getElementById('analysis-content').innerHTML = '<p style="text-align: center; color: #3498db;">🔄 Calculating correlations...</p>';
            
            const method = document.getElementById('correlation-method').value;
            const threshold = parseFloat(document.getElementById('correlation-threshold').value);
            
            fetch('/analyze/correlation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ method: method, threshold: threshold })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('analysis-content').innerHTML = '<p style="color: #e74c3c;">❌ Error: ' + data.error + '</p>';
                } else {
                    document.getElementById('analysis-content').innerHTML = data.html;
                }
            })
            .catch(error => {
                document.getElementById('analysis-content').innerHTML = '<p style="color: #e74c3c;">❌ Error: ' + error + '</p>';
            });
        }
        
        function runTrendAnalysis() {
            const parameter = document.getElementById('trend-parameter').value;
            const analysisType = document.getElementById('trend-analysis-type').value;
            
            if (!parameter) {
                alert('Please select a parameter for trend analysis');
                return;
            }
            
            document.getElementById('analysis-content').innerHTML = '<p style="text-align: center; color: #3498db;">🔄 Analyzing trends...</p>';
            
            fetch('/analyze/trend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ parameter: parameter, analysis_type: analysisType })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('analysis-content').innerHTML = '<p style="color: #e74c3c;">❌ Error: ' + data.error + '</p>';
                } else {
                    document.getElementById('analysis-content').innerHTML = data.html;
                }
            })
            .catch(error => {
                document.getElementById('analysis-content').innerHTML = '<p style="color: #e74c3c;">❌ Error: ' + error + '</p>';
            });
        }
        
        function calculateWQI() {
            const wqiType = document.getElementById('wqi-type').value;
            let selectedParams = [];
            
            if (wqiType === 'custom') {
                const checkboxes = document.querySelectorAll('input[name="wqi-param"]:checked');
                selectedParams = Array.from(checkboxes).map(cb => cb.value);
                
                if (selectedParams.length === 0) {
                    alert('Please select at least one parameter for custom WQI calculation');
                    return;
                }
            }
            
            document.getElementById('analysis-content').innerHTML = '<p style="text-align: center; color: #3498db;">🔄 Calculating Water Quality Index...</p>';
            
            fetch('/analyze/wqi', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ wqi_type: wqiType, parameters: selectedParams })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('analysis-content').innerHTML = '<p style="color: #e74c3c;">❌ Error: ' + data.error + '</p>';
                } else {
                    document.getElementById('analysis-content').innerHTML = data.html;
                }
            })
            .catch(error => {
                document.getElementById('analysis-content').innerHTML = '<p style="color: #e74c3c;">❌ Error: ' + error + '</p>';
            });
        }
        
        function detectAnomalies() {
            const method = document.getElementById('anomaly-method').value;
            const sensitivity = document.getElementById('anomaly-sensitivity').value;
            
            document.getElementById('analysis-content').innerHTML = '<p style="text-align: center; color: #3498db;">🔄 Detecting anomalies...</p>';
            
            fetch('/analyze/anomalies', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ method: method, sensitivity: sensitivity })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('analysis-content').innerHTML = '<p style="color: #e74c3c;">❌ Error: ' + data.error + '</p>';
                } else {
                    document.getElementById('analysis-content').innerHTML = data.html;
                }
            })
            .catch(error => {
                document.getElementById('analysis-content').innerHTML = '<p style="color: #e74c3c;">❌ Error: ' + error + '</p>';
            });
        }
        
        function downloadPlotImage() {
            var format = document.getElementById('plot-export-format').value;
            
            if (!window.currentPlotData) {
                alert('No plot data available. Please create a plot first.');
                return;
            }
            
            if (format === 'png' || format === 'svg') {
                // Use client-side Plotly export for PNG and SVG
                var plotDiv = document.getElementById('plot-container');
                Plotly.downloadImage(plotDiv, {
                    format: format,
                    filename: 'clearview_plot',
                    height: 600,
                    width: 800,
                    scale: 2
                });
            } else {
                // Use server-side export for PDF and HTML
                var button = event.target;
                var originalText = button.innerText;
                button.innerText = '⏳ Generating...';
                button.disabled = true;
                
                fetch('/export_plot', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        plot_data: window.currentPlotData,
                        plot_layout: window.currentPlotLayout,
                        format: format
                    })
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Export failed');
                    }
                    return response.blob();
                })
                .then(blob => {
                    // Create download link
                    var url = window.URL.createObjectURL(blob);
                    var a = document.createElement('a');
                    a.href = url;
                    a.download = 'clearview_plot.' + format;
                    a.style.display = 'none';
                    
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    
                    window.URL.revokeObjectURL(url);
                })
                .catch(error => {
                    console.error('Export error:', error);
                    alert('Export failed: ' + error.message);
                })
                .finally(() => {
                    button.innerText = originalText;
                    button.disabled = false;
                });
            }
        }
        
        function applyMethod() {
            var column = document.getElementById('method-column').value;
            var method = document.getElementById('method-type').value;
            
            if (!column || !method) {
                document.getElementById('method-result').innerHTML = 
                    '<p style="text-align: center; color: #e74c3c;">Please select both a column and method</p>';
                return;
            }
            
            document.getElementById('method-result').innerHTML = 
                '<p style="text-align: center; color: #3498db;">Processing ' + method + ' for ' + column + '...</p>';
            
            // Make API call to apply statistical method
            fetch('/apply_method', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    column: column,
                    method: method
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('method-result').innerHTML = 
                        '<p style="text-align: center; color: #e74c3c;">Error: ' + data.error + '</p>';
                    return;
                }
                
                // Display results
                var resultHtml = '<h4>Results: ' + data.method_name + ' for ' + data.column + '</h4>';
                resultHtml += '<p><strong>Original Data Points:</strong> ' + data.original_count + '</p>';
                resultHtml += '<p><strong>Result Data Points:</strong> ' + data.result_count + '</p>';
                resultHtml += '<div style="max-height: 300px; overflow: auto; border: 1px solid #ddd; margin: 10px 0;">';
                resultHtml += data.result_table;
                resultHtml += '</div>';
                document.getElementById('method-result').innerHTML = resultHtml;
                document.getElementById('method-export-controls').style.display = 'block';
                
                // Store results for download
                window.methodResults = data;
            })
            .catch(error => {
                document.getElementById('method-result').innerHTML = 
                    '<p style="text-align: center; color: #e74c3c;">Error applying method: ' + error + '</p>';
            });
        }
        
        function downloadData() {
            var format = document.getElementById('data-export-format').value;
            console.log('Downloading data in format:', format);
            
            // Try simple window.open approach first for debugging
            if (format === 'csv') {
                downloadFile('/download/data/' + format, 'data');
            } else {
                // Use form submission for non-CSV to avoid fetch issues
                var form = document.createElement('form');
                form.method = 'POST';
                form.action = '/download/data/' + format;
                form.style.display = 'none';
                
                var input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'data';
                input.value = '{}';
                form.appendChild(input);
                
                document.body.appendChild(form);
                form.submit();
                document.body.removeChild(form);
                
                console.log('Form submitted for', format);
            }
        }
        
        function downloadStats() {
            var format = document.getElementById('stats-export-format').value;
            console.log('Downloading stats in format:', format);
            
            if (format === 'csv') {
                downloadFile('/download/stats/' + format, 'stats');
            } else {
                // Use form submission for non-CSV
                var form = document.createElement('form');
                form.method = 'POST';
                form.action = '/download/stats/' + format;
                form.style.display = 'none';
                
                var input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'data';
                input.value = '{}';
                form.appendChild(input);
                
                document.body.appendChild(form);
                form.submit();
                document.body.removeChild(form);
                
                console.log('Stats form submitted for', format);
            }
        }
        
        function downloadMethodResults() {
            if (!window.methodResults) {
                alert('No method results available');
                return;
            }
            var format = document.getElementById('method-export-format').value;
            console.log('Downloading method results in format:', format);
            downloadFile('/download/method/' + format, window.methodResults.column + '_' + window.methodResults.method);
        }
        
        function downloadFile(url, baseFilename) {
            console.log('downloadFile called with:', url, baseFilename);
            
            // Show loading indicator
            var originalText = event.target.innerText;
            event.target.innerText = '⏳ Preparing...';
            event.target.disabled = true;
            
            console.log('Starting fetch to:', url);
            
            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(window.methodResults || {})
            })
            .then(response => {
                console.log('Response received:', response.status, response.statusText);
                if (!response.ok) {
                    throw new Error('Download failed: ' + response.statusText + ' (' + response.status + ')');
                }
                
                // Determine extension from URL format
                var format = url.split('/').pop();
                var extension = format === 'xlsx' ? '.xlsx' : 
                               format === 'sqlite' ? '.db' : 
                               format === 'hdf5' ? '.h5' : 
                               format === 'netcdf' ? '.nc' : '.csv';
                var filename = baseFilename + extension;
                
                console.log('Converting to blob, filename:', filename);
                return response.blob().then(blob => {
                    console.log('Blob created, size:', blob.size);
                    return {blob: blob, filename: filename};
                });
            })
            .then(({blob, filename}) => {
                console.log('Creating download link for:', filename);
                
                // Create download link
                var blobUrl = window.URL.createObjectURL(blob);
                var a = document.createElement('a');
                a.href = blobUrl;
                a.download = filename;
                a.style.display = 'none';
                
                // Trigger download
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                
                console.log('Download triggered');
                
                // Clean up
                setTimeout(() => {
                    window.URL.revokeObjectURL(blobUrl);
                    console.log('Blob URL cleaned up');
                }, 100);
            })
            .catch(error => {
                console.error('Download error:', error);
                alert('Download failed: ' + error.message);
            })
            .finally(() => {
                // Restore button
                event.target.innerText = originalText;
                event.target.disabled = false;
                console.log('Button restored');
            });
        }
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌊 ClearView - CE-QUAL-W2 Data Viewer</h1>
        </div>
        
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="success">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <!-- File Upload Progress Indicator -->
        <div id="upload-progress" style="display: none; margin: 20px 0; padding: 15px; background: #e3f2fd; border-radius: 8px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div class="spinner" style="width: 20px; height: 20px; border: 2px solid #f3f3f3; border-top: 2px solid #3498db; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                <div>
                    <p style="margin: 0; font-weight: bold;">Processing your file...</p>
                    <p id="progress-status" style="margin: 5px 0 0 0; font-size: 14px; color: #666;">Reading and validating data</p>
                    <div style="width: 300px; height: 6px; background: #ddd; border-radius: 3px; margin-top: 5px;">
                        <div id="progress-bar" style="width: 0%; height: 100%; background: linear-gradient(90deg, #3498db, #2ecc71); border-radius: 3px; transition: width 0.3s;"></div>
                    </div>
                </div>
            </div>
        </div>
        
        {% if data_store.df is none %}
        <div class="upload-area">
            <h3>📁 Upload Your Data File</h3>
            <form id="upload-form" method="POST" enctype="multipart/form-data">
                <input type="file" id="file-input" name="file" accept=".csv,.xlsx,.xls,.npt,.opt" required style="margin: 10px;">
                <br><br>
                <button type="submit" class="btn">🔄 Load Data</button>
            </form>
            <p style="color: #7f8c8d; margin-top: 15px;">
                Supported formats: CSV, Excel (.xlsx, .xls), NPT, OPT
            </p>
        </div>
        {% else %}
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-value">{{ data_store.filename }}</div>
                <div class="stat-label">📄 Filename</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{{ "{:,}".format(data_store.df|length) }}</div>
                <div class="stat-label">📊 Rows</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{{ data_store.df.columns|length }}</div>
                <div class="stat-label">📋 Columns</div>
            </div>
        </div>
        
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <div class="tabs" style="margin: 0;">
                <div class="tab active" onclick="showTab('data-tab')">📊 Data</div>
                <div class="tab" onclick="showTab('stats-tab')">📈 Stats</div>
                <div class="tab" onclick="showTab('plot-tab')">📉 Plot</div>
                <div class="tab" onclick="showTab('analysis-tab')">🔬 Analysis</div>
                <div class="tab" onclick="showTab('methods-tab')">⚗️ Methods</div>
                <div class="tab" onclick="showTab('info-tab')">ℹ️ Info</div>
            </div>
            <button onclick="closeData()" class="btn" style="background: #e74c3c; color: white; margin-left: 20px;">
                ❌ Close File
            </button>
        </div>
        
        <div id="data-tab" class="tab-content">
            <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 20px;">
                <div>
                    <h3>Data Overview</h3>
                    <p><strong>📄 File:</strong> {{ data_store.filename or 'No file loaded' }}</p>
                    {% if data_store.df is not none %}
                    <p><strong>📊 Shape:</strong> {{ "{:,}".format(data_store.df.shape[0]) }} rows × {{ data_store.df.shape[1] }} columns</p>
                    <p><strong>🗂️ Columns:</strong> {{ ', '.join(data_store.df.columns.tolist()[:8]) }}{% if data_store.df.shape[1] > 8 %} ... ({{ data_store.df.shape[1] - 8 }} more){% endif %}</p>
                    {% if data_store.file_info %}
                    <p><strong>📋 Format:</strong> {{ data_store.file_info.format }}
                    {% if data_store.file_info.ce_qual_w2_type %} ({{ data_store.file_info.ce_qual_w2_type }}){% endif %}</p>
                    {% endif %}
                    {% endif %}
                </div>
                
                {% if data_store.validation %}
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid 
                    {% if data_store.validation.quality_level == 'Excellent' %}#28a745
                    {% elif data_store.validation.quality_level == 'Good' %}#17a2b8
                    {% elif data_store.validation.quality_level == 'Fair' %}#ffc107
                    {% else %}#dc3545{% endif %};">
                    <h4 style="margin: 0 0 10px 0;">📊 Data Quality</h4>
                    <p style="margin: 5px 0;"><strong>Score:</strong> {{ data_store.validation.data_quality_score }}/100</p>
                    <p style="margin: 5px 0;"><strong>Level:</strong> 
                        <span style="color: 
                            {% if data_store.validation.quality_level == 'Excellent' %}#28a745
                            {% elif data_store.validation.quality_level == 'Good' %}#17a2b8
                            {% elif data_store.validation.quality_level == 'Fair' %}#ffc107
                            {% else %}#dc3545{% endif %};">
                            {{ data_store.validation.quality_level }}
                        </span>
                    </p>
                    {% if data_store.validation.missing_data_summary %}
                    <p style="margin: 5px 0;"><strong>Missing:</strong> {{ "%.1f"|format(data_store.validation.missing_data_summary.percentage) }}%</p>
                    {% endif %}
                    {% if data_store.validation.warnings|length > 0 %}
                    <details style="margin-top: 10px;">
                        <summary style="cursor: pointer; font-weight: bold;">⚠️ {{ data_store.validation.warnings|length }} Warning(s)</summary>
                        <ul style="margin: 10px 0; padding-left: 20px;">
                            {% for warning in data_store.validation.warnings[:5] %}
                            <li style="margin: 5px 0;">{{ warning }}</li>
                            {% endfor %}
                        </ul>
                    </details>
                    {% endif %}
                </div>
                {% endif %}
            </div>
            
            <h3>Data Preview (First 20 rows)</h3>
            <div style="margin: 10px 0;">
                <label for="data-export-format">Export Format:</label>
                <select id="data-export-format">
                    <option value="csv">CSV</option>
                    <option value="xlsx">Excel (.xlsx)</option>
                    <option value="sqlite">SQLite (.db)</option>
                    <option value="hdf5">HDF5 (.h5)</option>
                    <option value="netcdf">NetCDF (.nc)</option>
                </select>
                <button onclick="downloadData()" class="btn" style="margin-left: 10px;">💾 Download Data</button>
            </div>
            <div class="table-container">
                {{ data_store.df.head(20).to_html(classes='data-table', table_id='data-table')|safe }}
            </div>
        </div>
        
        <div id="stats-tab" class="tab-content" style="display: none;">
            <h3>Statistical Summary</h3>
            {% if data_store.stats is not none %}
                <div style="margin: 10px 0;">
                    <label for="stats-export-format">Export Format:</label>
                    <select id="stats-export-format">
                        <option value="csv">CSV</option>
                        <option value="xlsx">Excel (.xlsx)</option>
                        <option value="sqlite">SQLite (.db)</option>
                        <option value="hdf5">HDF5 (.h5)</option>
                        <option value="netcdf">NetCDF (.nc)</option>
                    </select>
                    <button onclick="downloadStats()" class="btn" style="margin-left: 10px;">💾 Download Statistics</button>
                </div>
                <div class="table-container">
                    {{ data_store.stats.to_html(classes='stats-table')|safe }}
                </div>
            {% else %}
                <p>No numeric columns found for statistical analysis.</p>
            {% endif %}
        </div>
        
        <div id="plot-tab" class="tab-content" style="display: none;">
            <h3>Enhanced Interactive Plotting</h3>
            
            <!-- Plot Configuration Panel -->
            <div style="background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px;">
                <div style="display: grid; grid-template-columns: 1fr 2fr 1fr; gap: 20px; align-items: start;">
                    
                    <!-- X-Axis Selection -->
                    <div>
                        <label for="x-column"><strong>X-axis:</strong></label>
                        <select id="x-column" onchange="updatePlot()">
                            <option value="datetime">📅 Date/Time</option>
                            <option value="">📊 Row Index</option>
                            {% for col in data_store.df.columns %}
                            <option value="{{ col }}">{{ col }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <!-- Y-Axis Multi-Selection -->
                    <div>
                        <label for="y-columns"><strong>Y-axis Parameters:</strong></label>
                        <select id="y-columns" multiple size="6" style="width: 100%; padding: 5px;" onchange="updatePlot()">
                            {% for col in data_store.df.select_dtypes(include=['number']).columns %}
                            <option value="{{ col }}">{{ col }}</option>
                            {% endfor %}
                        </select>
                        <div style="margin-top: 5px; font-size: 12px; color: #666;">
                            Hold Ctrl/Cmd to select multiple parameters
                        </div>
                    </div>
                    
                    <!-- Plot Controls -->
                    <div>
                        <label><strong>Plot Options:</strong></label>
                        <div style="margin: 5px 0;">
                            <input type="checkbox" id="show-markers" checked onchange="updatePlot()">
                            <label for="show-markers" style="margin-left: 5px;">Show Markers</label>
                        </div>
                        <div style="margin: 5px 0;">
                            <input type="checkbox" id="show-grid" checked onchange="updatePlot()">
                            <label for="show-grid" style="margin-left: 5px;">Show Grid</label>
                        </div>
                        <div style="margin: 5px 0;">
                            <input type="checkbox" id="dual-yaxis" onchange="updatePlot()">
                            <label for="dual-yaxis" style="margin-left: 5px;">Dual Y-Axis</label>
                        </div>
                        <div style="margin: 10px 0;">
                            <label for="subplot-mode" style="display: block; margin-bottom: 5px;">📊 Plot Layout:</label>
                            <select id="subplot-mode" onchange="updatePlot()" style="width: 100%;">
                                <option value="single">Single Plot (overlay)</option>
                                <option value="subplots-vertical">Subplots (vertical)</option>
                                <option value="subplots-grid">Subplots (2x2 grid)</option>
                                <option value="subplots-horizontal">Subplots (horizontal)</option>
                                <option value="comparison">Comparison (side-by-side parameters)</option>
                                <option value="animation">Time Series Animation</option>
                            </select>
                        </div>
                        <div style="margin: 10px 0;">
                            <label for="color-scheme" style="display: block; margin-bottom: 5px;">🎨 Color Scheme:</label>
                            <select id="color-scheme" onchange="updatePlot()" style="width: 100%;">
                                <option value="default">Default (Scientific)</option>
                                <option value="viridis">Viridis (Purple-Blue-Green-Yellow)</option>
                                <option value="plasma">Plasma (Purple-Pink-Yellow)</option>
                                <option value="ocean">Ocean (Blue-Teal-Green)</option>
                                <option value="sunset">Sunset (Orange-Red-Purple)</option>
                                <option value="earth">Earth (Brown-Orange-Yellow)</option>
                                <option value="thermal">Thermal (Dark-Red-Orange-Yellow)</option>
                                <option value="colorblind">Colorblind Safe</option>
                                <option value="monochrome">Monochrome (Grayscale)</option>
                            </select>
                        </div>
                        <div style="margin: 10px 0;">
                            <label for="line-style" style="display: block; margin-bottom: 5px;">📈 Line Style:</label>
                            <select id="line-style" onchange="updatePlot()" style="width: 100%;">
                                <option value="solid">Solid Lines</option>
                                <option value="dashed">Dashed Lines</option>
                                <option value="dotted">Dotted Lines</option>
                                <option value="mixed">Mixed Styles</option>
                            </select>
                        </div>
                        <button onclick="updatePlot()" class="btn" style="margin-top: 10px; width: 100%;">📈 Update Plot</button>
                        <button onclick="exportPlot()" class="btn" style="margin-top: 5px; width: 100%; background: #28a745;">💾 Export Plot</button>
                    </div>
                </div>
            </div>
            
            <!-- Interactive Controls -->
            <div class="interactive-controls">
                <h4>🎮 Interactive & Real-time Features</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
                    
                    <!-- Auto-refresh controls -->
                    <div>
                        <label>
                            <input type="checkbox" id="auto-refresh" onchange="toggleAutoRefresh()">
                            🔄 Auto-refresh plots
                            <span id="refresh-indicator" class="refresh-indicator">● Live</span>
                        </label>
                        <select id="refresh-interval" style="width: 100%; margin-top: 5px;">
                            <option value="5">Every 5 seconds</option>
                            <option value="10" selected>Every 10 seconds</option>
                            <option value="30">Every 30 seconds</option>
                            <option value="60">Every minute</option>
                        </select>
                    </div>
                    
                    <!-- Parameter monitoring -->
                    <div>
                        <label>
                            <input type="checkbox" id="parameter-monitoring" onchange="startParameterMonitoring()">
                            📊 Real-time parameter monitoring
                        </label>
                        <select id="monitor-parameter" style="width: 100%; margin-top: 5px;">
                            <option value="">Select parameter...</option>
                            {% for col in data_store.df.select_dtypes(include=['number']).columns %}
                            <option value="{{ col }}">{{ col }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <!-- Live data streaming -->
                    <div>
                        <label>
                            <input type="checkbox" id="live-streaming" onchange="toggleLiveStreaming()">
                            📡 Live data simulation
                            <span id="stream-indicator" class="refresh-indicator" style="display: none;">● Streaming</span>
                        </label>
                        <select id="stream-parameter" style="width: 100%; margin-top: 5px;">
                            <option value="">Select parameter to stream...</option>
                            {% for col in data_store.df.select_dtypes(include=['number']).columns %}
                            <option value="{{ col }}">{{ col }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                </div>
            </div>
            
            <!-- Real-time monitoring dashboard -->
            <div id="monitoring-dashboard" class="monitoring-dashboard">
                <!-- Content will be populated by JavaScript -->
            </div>
            
            <!-- Plot Display Area -->
            <div id="plot-container" style="width: 100%; height: 600px; border: 1px solid #ddd; margin-top: 10px;">
                <p style="text-align: center; color: #7f8c8d; padding: 50px;">Select Y-axis parameters and click "Update Plot" to visualize your data</p>
            </div>
            
            <!-- Data selection controls -->
            <div id="data-selection" class="data-selection">
                <!-- Content populated by JavaScript when data is selected -->
            </div>
            
            <!-- Hover info display -->
            <div id="hover-info" class="hover-info" style="display: none;">
                <!-- Content populated by JavaScript on hover -->
            </div>
            
            <!-- Plot Export Options -->
            <div id="plot-export-options" style="display: none; margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                <label for="plot-export-format">Export Format:</label>
                <select id="plot-export-format">
                    <option value="png">PNG Image</option>
                    <option value="svg">SVG Vector</option>
                    <option value="pdf">PDF Document</option>
                    <option value="html">Interactive HTML</option>
                </select>
                <button onclick="downloadPlotImage()" class="btn" style="margin-left: 10px;">📥 Download</button>
            </div>
        </div>
        
        <div id="analysis-tab" class="tab-content" style="display: none;">
            <h3>Advanced Water Quality Analysis</h3>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px;">
                <!-- Correlation Analysis -->
                <div style="border: 1px solid #ddd; padding: 20px; border-radius: 8px;">
                    <h4>🔗 Parameter Correlations</h4>
                    <p style="color: #666; margin-bottom: 15px;">Discover relationships between water quality parameters</p>
                    
                    <div style="margin: 10px 0;">
                        <label for="correlation-method">Correlation Method:</label>
                        <select id="correlation-method" style="width: 100%; margin-top: 5px;">
                            <option value="pearson">Pearson (linear relationships)</option>
                            <option value="spearman">Spearman (rank-based, non-linear)</option>
                            <option value="kendall">Kendall (robust to outliers)</option>
                        </select>
                    </div>
                    
                    <div style="margin: 10px 0;">
                        <label for="correlation-threshold">Significance Threshold:</label>
                        <select id="correlation-threshold" style="width: 100%; margin-top: 5px;">
                            <option value="0.3">Strong (|r| ≥ 0.3)</option>
                            <option value="0.5" selected>Very Strong (|r| ≥ 0.5)</option>
                            <option value="0.7">Exceptional (|r| ≥ 0.7)</option>
                        </select>
                    </div>
                    
                    <button onclick="runCorrelationAnalysis()" class="btn" style="width: 100%; margin-top: 10px;">
                        📊 Run Correlation Analysis
                    </button>
                </div>
                
                <!-- Trend Analysis -->
                <div style="border: 1px solid #ddd; padding: 20px; border-radius: 8px;">
                    <h4>📈 Trend Detection</h4>
                    <p style="color: #666; margin-bottom: 15px;">Identify temporal patterns and trends in your data</p>
                    
                    <div style="margin: 10px 0;">
                        <label for="trend-parameter">Parameter:</label>
                        <select id="trend-parameter" style="width: 100%; margin-top: 5px;">
                            <option value="">Select parameter...</option>
                            {% for col in data_store.df.select_dtypes(include=['number']).columns %}
                            <option value="{{ col }}">{{ col }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div style="margin: 10px 0;">
                        <label for="trend-analysis-type">Analysis Type:</label>
                        <select id="trend-analysis-type" style="width: 100%; margin-top: 5px;">
                            <option value="seasonal">Seasonal Decomposition</option>
                            <option value="trend">Linear Trend Test</option>
                            <option value="changepoint">Change Point Detection</option>
                            <option value="periodicity">Periodicity Analysis</option>
                        </select>
                    </div>
                    
                    <button onclick="runTrendAnalysis()" class="btn" style="width: 100%; margin-top: 10px;">
                        📈 Analyze Trends
                    </button>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px;">
                <!-- Water Quality Index -->
                <div style="border: 1px solid #ddd; padding: 20px; border-radius: 8px;">
                    <h4>🌊 Water Quality Index</h4>
                    <p style="color: #666; margin-bottom: 15px;">Calculate standardized water quality indices</p>
                    
                    <div style="margin: 10px 0;">
                        <label for="wqi-type">Index Type:</label>
                        <select id="wqi-type" style="width: 100%; margin-top: 5px;">
                            <option value="basic">Basic WQI (DO, pH, Temperature)</option>
                            <option value="comprehensive">Comprehensive WQI</option>
                            <option value="trophic">Trophic State Index</option>
                            <option value="custom">Custom Parameter Set</option>
                        </select>
                    </div>
                    
                    <div id="custom-wqi-params" style="display: none; margin: 10px 0;">
                        <label>Select Parameters:</label>
                        <div style="max-height: 120px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; margin-top: 5px;">
                            {% for col in data_store.df.select_dtypes(include=['number']).columns %}
                            <label style="display: block; margin: 2px 0;">
                                <input type="checkbox" name="wqi-param" value="{{ col }}"> {{ col }}
                            </label>
                            {% endfor %}
                        </div>
                    </div>
                    
                    <button onclick="calculateWQI()" class="btn" style="width: 100%; margin-top: 10px;">
                        🌊 Calculate WQI
                    </button>
                </div>
                
                <!-- Anomaly Detection -->
                <div style="border: 1px solid #ddd; padding: 20px; border-radius: 8px;">
                    <h4>🚨 Anomaly Detection</h4>
                    <p style="color: #666; margin-bottom: 15px;">Identify unusual values and potential data quality issues</p>
                    
                    <div style="margin: 10px 0;">
                        <label for="anomaly-method">Detection Method:</label>
                        <select id="anomaly-method" style="width: 100%; margin-top: 5px;">
                            <option value="zscore">Z-Score (±3σ threshold)</option>
                            <option value="iqr">Interquartile Range (IQR)</option>
                            <option value="isolation">Isolation Forest</option>
                            <option value="seasonal">Seasonal Decomposition</option>
                        </select>
                    </div>
                    
                    <div style="margin: 10px 0;">
                        <label for="anomaly-sensitivity">Sensitivity:</label>
                        <select id="anomaly-sensitivity" style="width: 100%; margin-top: 5px;">
                            <option value="low">Low (fewer anomalies)</option>
                            <option value="medium" selected>Medium (balanced)</option>
                            <option value="high">High (more sensitive)</option>
                        </select>
                    </div>
                    
                    <button onclick="detectAnomalies()" class="btn" style="width: 100%; margin-top: 10px;">
                        🚨 Detect Anomalies
                    </button>
                </div>
            </div>
            
            <!-- Results Display Area -->
            <div id="analysis-results" style="margin-top: 30px;">
                <h4>Analysis Results</h4>
                <div id="analysis-content" style="min-height: 200px; border: 1px solid #ddd; padding: 20px; border-radius: 8px; background: #f9f9f9;">
                    <p style="text-align: center; color: #666; margin-top: 80px;">
                        📊 Select an analysis method above to view results
                    </p>
                </div>
            </div>
        </div>
        
        <div id="methods-tab" class="tab-content" style="display: none;">
            <h3>Time Series Analysis Methods</h3>
            <p style="color: #7f8c8d; margin: 10px 0;">All methods operate on the datetime index automatically</p>
            <div style="margin: 20px 0;">
                <label for="method-column">Select Column:</label>
                <select id="method-column">
                    <option value="">Select column...</option>
                    {% for col in data_store.df.select_dtypes(include=['number']).columns %}
                    <option value="{{ col }}">{{ col }}</option>
                    {% endfor %}
                </select>
                
                <label for="method-type" style="margin-left: 20px;">Select Method:</label>
                <select id="method-type">
                    <option value="">Select method...</option>
                    <optgroup label="Resampling Methods">
                        <option value="hourly_mean">Hourly Mean</option>
                        <option value="hourly_max">Hourly Max</option>
                        <option value="hourly_min">Hourly Min</option>
                        <option value="daily_mean">Daily Mean</option>
                        <option value="daily_max">Daily Max</option>
                        <option value="daily_min">Daily Min</option>
                        <option value="weekly_mean">Weekly Mean</option>
                        <option value="weekly_max">Weekly Max</option>
                        <option value="weekly_min">Weekly Min</option>
                        <option value="monthly_mean">Monthly Mean</option>
                        <option value="monthly_max">Monthly Max</option>
                        <option value="monthly_min">Monthly Min</option>
                        <option value="annual_mean">Annual Mean</option>
                        <option value="annual_max">Annual Max</option>
                        <option value="annual_min">Annual Min</option>
                    </optgroup>
                    <optgroup label="Cumulative Methods">
                        <option value="cumulative_sum">Cumulative Sum</option>
                        <option value="cumulative_max">Cumulative Max</option>
                        <option value="cumulative_min">Cumulative Min</option>
                    </optgroup>
                    <optgroup label="Statistical Methods">
                        <option value="rolling_mean_7">7-Day Rolling Mean</option>
                        <option value="rolling_mean_30">30-Day Rolling Mean</option>
                        <option value="rolling_std_7">7-Day Rolling Std</option>
                        <option value="rolling_std_30">30-Day Rolling Std</option>
                    </optgroup>
                </select>
                
                <button onclick="applyMethod()" class="btn" style="margin-left: 20px;">🔬 Apply Method</button>
            </div>
            
            <div style="margin: 10px 0; display: none;" id="method-export-controls">
                <label for="method-export-format">Export Format:</label>
                <select id="method-export-format">
                    <option value="csv">CSV</option>
                    <option value="xlsx">Excel (.xlsx)</option>
                    <option value="sqlite">SQLite (.db)</option>
                    <option value="hdf5">HDF5 (.h5)</option>
                    <option value="netcdf">NetCDF (.nc)</option>
                </select>
                <button onclick="downloadMethodResults()" class="btn" style="margin-left: 10px;">💾 Download Results</button>
            </div>
            
            <div id="method-result" style="border: 1px solid #ddd; padding: 20px; min-height: 200px;">
                <p style="text-align: center; color: #7f8c8d;">Select a column and method to see results</p>
            </div>
        </div>
        
        <div id="info-tab" class="tab-content" style="display: none;">
            <h3>Column Information</h3>
            <div class="table-container">
                <table>
                    <tr><th>Column Name</th><th>Data Type</th><th>Non-null Count</th><th>Unique Values</th></tr>
                    {% for col in data_store.df.columns %}
                    <tr>
                        <td>{{ col }}</td>
                        <td>{{ data_store.df[col].dtype }}</td>
                        <td>{{ data_store.df[col].count() }}</td>
                        <td>{{ data_store.df[col].nunique() }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
        
        <div style="margin-top: 20px;">
            <a href="{{ url_for('clear_data') }}" class="btn" style="background: #e74c3c;">🗑️ Clear Data</a>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Handle file upload
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('Please select a file')
            return redirect(url_for('index'))
        
        try:
            # Enhanced file processing with comprehensive error handling
            filename = file.filename
            file_size = len(file.read())
            file.seek(0)  # Reset file pointer
            
            # File size validation (limit to 100MB)
            max_size = 100 * 1024 * 1024  # 100MB
            if file_size > max_size:
                flash(f'❌ File too large ({file_size/1024/1024:.1f}MB). Maximum size is {max_size/1024/1024}MB.')
                return redirect(url_for('index'))
            
            # Read file content
            file_content = io.BytesIO(file.read())
            
            # Enhanced file format detection and reading
            df, file_info = read_file_with_validation(file_content, filename)
            
            # Process datetime index from JDAY or other date columns
            df = _ensure_datetime_index(df, filename)
            
            # Comprehensive data validation
            validation_results = validate_data_quality(df, filename)
            
            # Store data globally
            data_store['df'] = df
            data_store['filename'] = filename
            data_store['validation'] = validation_results
            data_store['file_info'] = file_info
            
            # Calculate statistics for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                data_store['stats'] = df[numeric_cols].describe()
            else:
                data_store['stats'] = None
            
            # Create success message with file info and warnings
            success_msg = f'✅ Successfully loaded {filename} ({file_info["format"]}, {file_size/1024:.1f}KB) with {len(df):,} rows and {len(df.columns)} columns!'
            
            # Add validation warnings to flash messages
            if validation_results['warnings']:
                flash(success_msg)
                for warning in validation_results['warnings']:
                    flash(f'⚠️ {warning}', 'warning')
            else:
                flash(success_msg + ' ✨ Data quality: Excellent!')
            
        except Exception as e:
            # Enhanced error reporting
            error_type = type(e).__name__
            error_msg = str(e)
            
            if 'UnicodeDecodeError' in error_type:
                flash(f'❌ File encoding error: Unable to read file. Try saving as UTF-8 encoded CSV.')
            elif 'ParserError' in error_type:
                flash(f'❌ File parsing error: {error_msg}. Check for malformed CSV/Excel structure.')
            elif 'MemoryError' in error_type:
                flash(f'❌ File too large for available memory. Try splitting into smaller files.')
            elif 'PermissionError' in error_type:
                flash(f'❌ File access denied. Check file permissions.')
            else:
                flash(f'❌ Error loading file ({error_type}): {error_msg}')
            
            return redirect(url_for('index'))
    
    return render_template_string(HTML_TEMPLATE, data_store=data_store)

@app.route('/clear_data', methods=['POST'])
def clear_data():
    """Clear all stored data and reset the application"""
    try:
        # Reset all data store values
        data_store['df'] = None
        data_store['filename'] = None
        data_store['stats'] = None
        data_store['validation'] = None
        data_store['file_info'] = None
        
        return jsonify({'success': True, 'message': 'Data cleared successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/plot_data', methods=['POST'])
def plot_data():
    """Generate plot data for the frontend"""
    try:
        if data_store['df'] is None:
            return jsonify({'error': 'No data loaded'})
        
        data = request.get_json()
        x_column = data.get('x_column', '')
        y_column = data.get('y_column', '')
        
        if not y_column:
            return jsonify({'error': 'Y-axis column is required'})
        
        df = data_store['df']
        
        # Prepare plot data
        if x_column == 'datetime':
            # Use the datetime index
            x_data = df.index.strftime('%Y-%m-%d %H:%M:%S').tolist() if isinstance(df.index, pd.DatetimeIndex) else df.index.tolist()
            x_label = 'Date/Time'
        elif x_column and x_column in df.columns:
            x_data = df[x_column].tolist()
            x_label = x_column
        else:
            x_data = list(range(len(df)))
            x_label = 'Row Index'
        
        if y_column not in df.columns:
            return jsonify({'error': f'Column "{y_column}" not found'})
        
        y_data = df[y_column].tolist()
        y_label = y_column
        
        # Create title
        title = f'{y_column} vs {x_label}'
        
        return jsonify({
            'x_data': x_data,
            'y_data': y_data,
            'x_label': x_label,
            'y_label': y_label,
            'y_column': y_column,
            'title': title
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

def get_color_palette(scheme, n_colors):
    """Get color palette based on selected scheme"""
    color_schemes = {
        'default': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'],
        'viridis': ['#440154', '#404688', '#2a788e', '#22a884', '#7ad151', '#fde725'],
        'plasma': ['#0d0887', '#6a00a8', '#b12a90', '#e16462', '#fca636', '#f0f921'],
        'ocean': ['#003f5c', '#2f4b7c', '#665191', '#a05195', '#d45087', '#f95d6a', '#ff7c43', '#ffa600'],
        'sunset': ['#ff6b35', '#f7931e', '#ffd23f', '#06ffa5', '#3282b8', '#0f3460'],
        'earth': ['#8b4513', '#cd853f', '#daa520', '#b8860b', '#228b22', '#32cd32'],
        'thermal': ['#000428', '#004e92', '#009ffd', '#00d2ff', '#ffffff'],
        'colorblind': ['#1b9e77', '#d95f02', '#7570b3', '#e7298a', '#66a61e', '#e6ab02', '#a6761d', '#666666'],
        'monochrome': ['#000000', '#404040', '#808080', '#a0a0a0', '#c0c0c0', '#e0e0e0']
    }
    
    base_colors = color_schemes.get(scheme, color_schemes['default'])
    
    # Extend colors if we need more than available
    if n_colors <= len(base_colors):
        return base_colors[:n_colors]
    else:
        # Repeat colors if we need more
        extended = []
        for i in range(n_colors):
            extended.append(base_colors[i % len(base_colors)])
        return extended

def get_line_patterns(style, n_lines):
    """Get line dash patterns based on selected style"""
    patterns = {
        'solid': ['solid'] * n_lines,
        'dashed': ['dash'] * n_lines,
        'dotted': ['dot'] * n_lines,
        'mixed': ['solid', 'dash', 'dot', 'dashdot', 'longdash', 'longdashdot']
    }
    
    base_patterns = patterns.get(style, patterns['solid'])
    
    if n_lines <= len(base_patterns):
        return base_patterns[:n_lines]
    else:
        extended = []
        for i in range(n_lines):
            extended.append(base_patterns[i % len(base_patterns)])
        return extended

@app.route('/plot_data_multi', methods=['POST'])
def plot_data_multi():
    """Generate multi-column plot data for enhanced visualization with subplot support"""
    try:
        if data_store['df'] is None:
            return jsonify({'error': 'No data loaded'})
        
        data = request.get_json()
        x_column = data.get('x_column', '')
        y_columns = data.get('y_columns', [])
        show_markers = data.get('show_markers', True)
        show_grid = data.get('show_grid', True)
        dual_yaxis = data.get('dual_yaxis', False)
        subplot_mode = data.get('subplot_mode', 'single')
        color_scheme = data.get('color_scheme', 'default')
        line_style = data.get('line_style', 'solid')
        filters = data.get('filters', None)
        
        if not y_columns:
            return jsonify({'error': 'Y-axis columns are required'})
        
        df = data_store['df'].copy()
        
        # Apply filters if provided
        if filters:
            parameter = filters.get('parameter')
            min_value = filters.get('min_value')
            max_value = filters.get('max_value')
            
            if parameter and parameter in df.columns:
                if min_value is not None:
                    df = df[df[parameter] >= min_value]
                if max_value is not None:
                    df = df[df[parameter] <= max_value]
                    
            if len(df) == 0:
                return jsonify({'error': 'No data remaining after applying filters'})
        
        # Prepare X-axis data
        if x_column == 'datetime':
            x_data = df.index.strftime('%Y-%m-%d %H:%M:%S').tolist() if isinstance(df.index, pd.DatetimeIndex) else df.index.tolist()
            x_label = 'Date/Time'
        elif x_column and x_column in df.columns:
            x_data = df[x_column].tolist()
            x_label = x_column
        else:
            x_data = list(range(len(df)))
            x_label = 'Row Index'
        
        # Get color palette based on scheme
        colors = get_color_palette(color_scheme, len(y_columns))
        
        # Get line dash patterns
        line_dashes = get_line_patterns(line_style, len(y_columns))
        
        if subplot_mode == 'single':
            # Single plot mode (original behavior)
            traces = []
            for i, y_col in enumerate(y_columns):
                if y_col not in df.columns:
                    continue
                    
                color = colors[i]
                line_dash = line_dashes[i]
                
                trace = {
                    'x': x_data,
                    'y': df[y_col].tolist(),
                    'type': 'scatter',
                    'mode': 'lines+markers' if show_markers else 'lines',
                    'name': y_col,
                    'line': {'color': color, 'width': 2, 'dash': line_dash},
                    'marker': {'size': 4, 'color': color} if show_markers else {},
                    'yaxis': 'y2' if dual_yaxis and i >= len(y_columns)//2 else 'y'
                }
                traces.append(trace)
            
            # Create layout
            layout = {
                'xaxis': {
                    'title': x_label,
                    'showgrid': show_grid
                },
                'yaxis': {
                    'title': y_columns[0] if len(y_columns) == 1 else 'Primary Parameters',
                    'showgrid': show_grid
                },
                'legend': {
                    'orientation': 'h',
                    'yanchor': 'bottom',
                    'y': 1.02,
                    'xanchor': 'right',
                    'x': 1,
                    'font': {'size': 12}
                },
                'hovermode': 'x unified'
            }
            
            # Add secondary Y-axis if dual axis is enabled
            if dual_yaxis and len(y_columns) > 1:
                layout['yaxis2'] = {
                    'title': 'Secondary Parameters',
                    'overlaying': 'y',
                    'side': 'right',
                    'showgrid': False
                }
        
        else:
            # Subplot modes - create individual subplots with proper domain positioning
            traces = []
            layout = {
                'hovermode': 'closest',
                'showlegend': True,
                'legend': {
                    'orientation': 'h',
                    'yanchor': 'bottom',
                    'y': 1.02,
                    'xanchor': 'right',
                    'x': 1,
                    'font': {'size': 10}
                }
            }
            
            n_plots = len(y_columns)
            
            if subplot_mode == 'subplots-vertical':
                # Stack vertically - each subplot takes full width, divided height
                height_per_plot = 1.0 / n_plots
                for i, y_col in enumerate(y_columns):
                    if y_col not in df.columns:
                        continue
                    
                    color = colors[i]
                    line_dash = line_dashes[i]
                    
                    # Calculate domain positions (from bottom to top)
                    y_bottom = (n_plots - i - 1) * height_per_plot
                    y_top = (n_plots - i) * height_per_plot - 0.05  # Small gap between subplots
                    
                    subplot_num = i + 1
                    xaxis_ref = f'x{subplot_num}' if subplot_num > 1 else 'x'
                    yaxis_ref = f'y{subplot_num}' if subplot_num > 1 else 'y'
                    
                    trace = {
                        'x': x_data,
                        'y': df[y_col].tolist(),
                        'type': 'scatter',
                        'mode': 'lines+markers' if show_markers else 'lines',
                        'name': y_col,
                        'line': {'color': color, 'width': 2, 'dash': line_dash},
                        'marker': {'size': 4, 'color': color} if show_markers else {},
                        'xaxis': xaxis_ref,
                        'yaxis': yaxis_ref
                    }
                    traces.append(trace)
                    
                    # Configure axis layout with domains
                    layout[xaxis_ref] = {
                        'domain': [0.0, 1.0],
                        'title': x_label if i == n_plots - 1 else '',  # Only show x-title on bottom plot
                        'showgrid': show_grid,
                        'anchor': yaxis_ref
                    }
                    layout[yaxis_ref] = {
                        'domain': [y_bottom, y_top],
                        'title': y_col,
                        'showgrid': show_grid,
                        'anchor': xaxis_ref
                    }
                
                layout['height'] = max(400, n_plots * 200)
            
            elif subplot_mode == 'subplots-horizontal':
                # Side by side - each subplot takes full height, divided width
                width_per_plot = 1.0 / n_plots
                for i, y_col in enumerate(y_columns):
                    if y_col not in df.columns:
                        continue
                    
                    color = colors[i]
                    line_dash = line_dashes[i]
                    
                    # Calculate domain positions (left to right)
                    x_left = i * width_per_plot
                    x_right = (i + 1) * width_per_plot - 0.02  # Small gap between subplots
                    
                    subplot_num = i + 1
                    xaxis_ref = f'x{subplot_num}' if subplot_num > 1 else 'x'
                    yaxis_ref = f'y{subplot_num}' if subplot_num > 1 else 'y'
                    
                    trace = {
                        'x': x_data,
                        'y': df[y_col].tolist(),
                        'type': 'scatter',
                        'mode': 'lines+markers' if show_markers else 'lines',
                        'name': y_col,
                        'line': {'color': color, 'width': 2, 'dash': line_dash},
                        'marker': {'size': 4, 'color': color} if show_markers else {},
                        'xaxis': xaxis_ref,
                        'yaxis': yaxis_ref
                    }
                    traces.append(trace)
                    
                    # Configure axis layout with domains
                    layout[xaxis_ref] = {
                        'domain': [x_left, x_right],
                        'title': x_label,
                        'showgrid': show_grid,
                        'anchor': yaxis_ref
                    }
                    layout[yaxis_ref] = {
                        'domain': [0.0, 1.0],
                        'title': y_col,
                        'showgrid': show_grid,
                        'anchor': xaxis_ref
                    }
            
            elif subplot_mode == 'subplots-grid':
                # 2x2 grid layout
                import math
                cols = 2
                rows = math.ceil(n_plots / cols)
                
                for i, y_col in enumerate(y_columns):
                    if y_col not in df.columns:
                        continue
                    
                    color = colors[i]
                    line_dash = line_dashes[i]
                    
                    # Calculate grid position
                    row = i // cols
                    col = i % cols
                    
                    # Calculate domain positions
                    width_per_plot = 1.0 / cols
                    height_per_plot = 1.0 / rows
                    
                    x_left = col * width_per_plot
                    x_right = (col + 1) * width_per_plot - 0.02
                    y_bottom = (rows - row - 1) * height_per_plot
                    y_top = (rows - row) * height_per_plot - 0.05
                    
                    subplot_num = i + 1
                    xaxis_ref = f'x{subplot_num}' if subplot_num > 1 else 'x'
                    yaxis_ref = f'y{subplot_num}' if subplot_num > 1 else 'y'
                    
                    trace = {
                        'x': x_data,
                        'y': df[y_col].tolist(),
                        'type': 'scatter',
                        'mode': 'lines+markers' if show_markers else 'lines',
                        'name': y_col,
                        'line': {'color': color, 'width': 2, 'dash': line_dash},
                        'marker': {'size': 4, 'color': color} if show_markers else {},
                        'xaxis': xaxis_ref,
                        'yaxis': yaxis_ref
                    }
                    traces.append(trace)
                    
                    # Configure axis layout with domains
                    layout[xaxis_ref] = {
                        'domain': [x_left, x_right],
                        'title': x_label if row == rows - 1 else '',  # Only show x-title on bottom row
                        'showgrid': show_grid,
                        'anchor': yaxis_ref
                    }
                    layout[yaxis_ref] = {
                        'domain': [y_bottom, y_top],
                        'title': y_col,
                        'showgrid': show_grid,
                        'anchor': xaxis_ref
                    }
                
                layout['height'] = max(400, rows * 250)
            
            elif subplot_mode == 'comparison':
                # Comparison mode - split parameters into two groups for side-by-side comparison
                # Divide parameters into two groups
                mid_point = len(y_columns) // 2
                group1 = y_columns[:mid_point] if mid_point > 0 else y_columns
                group2 = y_columns[mid_point:] if mid_point > 0 and mid_point < len(y_columns) else []
                
                traces = []
                
                # Create traces for first group (left side)
                for i, y_col in enumerate(group1):
                    if y_col not in df.columns:
                        continue
                    
                    color = colors[i]
                    line_dash = line_dashes[i]
                    
                    trace = {
                        'x': x_data,
                        'y': df[y_col].tolist(),
                        'type': 'scatter',
                        'mode': 'lines+markers' if show_markers else 'lines',
                        'name': f'Group 1: {y_col}',
                        'line': {'color': color, 'width': 2, 'dash': line_dash},
                        'marker': {'size': 4, 'color': color} if show_markers else {},
                        'xaxis': 'x',
                        'yaxis': 'y'
                    }
                    traces.append(trace)
                
                # Create traces for second group (right side) if it exists
                if group2:
                    for i, y_col in enumerate(group2):
                        if y_col not in df.columns:
                            continue
                        
                        color = colors[mid_point + i]
                        line_dash = line_dashes[mid_point + i]
                        
                        trace = {
                            'x': x_data,
                            'y': df[y_col].tolist(),
                            'type': 'scatter',
                            'mode': 'lines+markers' if show_markers else 'lines',
                            'name': f'Group 2: {y_col}',
                            'line': {'color': color, 'width': 2, 'dash': line_dash},
                            'marker': {'size': 4, 'color': color} if show_markers else {},
                            'xaxis': 'x2',
                            'yaxis': 'y2'
                        }
                        traces.append(trace)
                
                # Setup side-by-side layout
                layout = {
                    'xaxis': {
                        'domain': [0.0, 0.48],
                        'title': x_label,
                        'showgrid': show_grid,
                        'anchor': 'y'
                    },
                    'yaxis': {
                        'domain': [0.0, 1.0],
                        'title': 'Group 1 Parameters' if group1 else 'Parameters',
                        'showgrid': show_grid,
                        'anchor': 'x'
                    },
                    'hovermode': 'x unified',
                    'showlegend': True,
                    'legend': {
                        'orientation': 'h',
                        'yanchor': 'bottom',
                        'y': 1.02,
                        'xanchor': 'right',
                        'x': 1,
                        'font': {'size': 10}
                    }
                }
                
                # Add second axis if we have a second group
                if group2:
                    layout['xaxis2'] = {
                        'domain': [0.52, 1.0],
                        'title': x_label,
                        'showgrid': show_grid,
                        'anchor': 'y2'
                    }
                    layout['yaxis2'] = {
                        'domain': [0.0, 1.0],
                        'title': 'Group 2 Parameters',
                        'showgrid': show_grid,
                        'anchor': 'x2'
                    }
            
            elif subplot_mode == 'animation':
                # Animation mode - create time series animation
                traces = []
                
                # Determine time steps for animation (sample every N points to avoid too many frames)
                n_points = len(df)
                max_frames = 50  # Limit to 50 frames for performance
                step_size = max(1, n_points // max_frames)
                time_indices = list(range(0, n_points, step_size))
                
                # Create frames for animation
                frames = []
                for frame_idx, end_idx in enumerate(time_indices):
                    frame_traces = []
                    
                    for i, y_col in enumerate(y_columns):
                        if y_col not in df.columns:
                            continue
                        
                        color = colors[i]
                        line_dash = line_dashes[i]
                        
                        # Get data up to current time point
                        x_subset = x_data[:end_idx+1]
                        y_subset = df[y_col].iloc[:end_idx+1].tolist()
                        
                        trace = {
                            'x': x_subset,
                            'y': y_subset,
                            'type': 'scatter',
                            'mode': 'lines+markers' if show_markers else 'lines',
                            'name': y_col,
                            'line': {'color': color, 'width': 2, 'dash': line_dash},
                            'marker': {'size': 4, 'color': color} if show_markers else {}
                        }
                        frame_traces.append(trace)
                    
                    # Add current time marker
                    if end_idx < len(x_data):
                        current_time_trace = {
                            'x': [x_data[end_idx]],
                            'y': [0],  # Will be positioned at bottom
                            'type': 'scatter',
                            'mode': 'markers',
                            'name': 'Current Time',
                            'marker': {'size': 10, 'color': 'red', 'symbol': 'diamond'},
                            'showlegend': False,
                            'yaxis': 'y2'
                        }
                        frame_traces.append(current_time_trace)
                    
                    frames.append({
                        'name': f'frame_{frame_idx}',
                        'data': frame_traces
                    })
                
                # Create initial traces (empty to start)
                for i, y_col in enumerate(y_columns):
                    if y_col not in df.columns:
                        continue
                    
                    color = colors[i]
                    line_dash = line_dashes[i]
                    
                    trace = {
                        'x': [],
                        'y': [],
                        'type': 'scatter',
                        'mode': 'lines+markers' if show_markers else 'lines',
                        'name': y_col,
                        'line': {'color': color, 'width': 2, 'dash': line_dash},
                        'marker': {'size': 4, 'color': color} if show_markers else {}
                    }
                    traces.append(trace)
                
                # Add time marker trace
                traces.append({
                    'x': [],
                    'y': [],
                    'type': 'scatter',
                    'mode': 'markers',
                    'name': 'Current Time',
                    'marker': {'size': 10, 'color': 'red', 'symbol': 'diamond'},
                    'showlegend': False,
                    'yaxis': 'y2'
                })
                
                # Create layout with animation controls
                layout = {
                    'xaxis': {
                        'title': x_label,
                        'showgrid': show_grid
                    },
                    'yaxis': {
                        'title': 'Parameters',
                        'showgrid': show_grid
                    },
                    'yaxis2': {
                        'title': '',
                        'overlaying': 'y',
                        'side': 'right',
                        'showgrid': False,
                        'showticklabels': False,
                        'range': [0, 1]
                    },
                    'hovermode': 'x unified',
                    'showlegend': True,
                    'legend': {
                        'orientation': 'h',
                        'yanchor': 'bottom',
                        'y': 1.02,
                        'xanchor': 'right',
                        'x': 1,
                        'font': {'size': 10}
                    },
                    'updatemenus': [{
                        'type': 'buttons',
                        'showactive': False,
                        'buttons': [
                            {
                                'label': '▶️ Play',
                                'method': 'animate',
                                'args': [None, {
                                    'frame': {'duration': 200, 'redraw': True},
                                    'fromcurrent': True,
                                    'transition': {'duration': 100}
                                }]
                            },
                            {
                                'label': '⏸️ Pause',
                                'method': 'animate',
                                'args': [[None], {
                                    'frame': {'duration': 0, 'redraw': False},
                                    'mode': 'immediate',
                                    'transition': {'duration': 0}
                                }]
                            }
                        ],
                        'direction': 'left',
                        'pad': {'r': 10, 't': 87},
                        'x': 0.1,
                        'xanchor': 'right',
                        'y': 0,
                        'yanchor': 'top'
                    }],
                    'sliders': [{
                        'active': 0,
                        'yanchor': 'top',
                        'xanchor': 'left',
                        'currentvalue': {
                            'font': {'size': 20},
                            'prefix': 'Time Step: ',
                            'visible': True,
                            'xanchor': 'right'
                        },
                        'transition': {'duration': 100, 'easing': 'cubic-in-out'},
                        'pad': {'b': 10, 't': 50},
                        'len': 0.9,
                        'x': 0.1,
                        'y': 0,
                        'steps': [
                            {
                                'args': [[f'frame_{i}'], {
                                    'frame': {'duration': 100, 'redraw': True},
                                    'mode': 'immediate',
                                    'transition': {'duration': 100}
                                }],
                                'label': str(i),
                                'method': 'animate'
                            } for i in range(len(frames))
                        ]
                    }]
                }
                
                return jsonify({
                    'traces': traces,
                    'layout': layout,
                    'frames': frames
                })
        
        return jsonify({
            'traces': traces,
            'layout': layout
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/export_plot', methods=['POST'])
def export_plot():
    """Export plot to various formats using server-side rendering"""
    try:
        import plotly.graph_objects as go
        import plotly.io as pio
        
        data = request.get_json()
        plot_data = data.get('plot_data', [])
        plot_layout = data.get('plot_layout', {})
        export_format = data.get('format', 'png')
        
        if not plot_data:
            return jsonify({'error': 'No plot data provided'}), 400
        
        # Create Plotly figure from the data
        try:
            fig = go.Figure(data=plot_data, layout=plot_layout)
            
            # Set figure size
            fig.update_layout(
                width=800,
                height=600,
                margin=dict(l=60, r=60, t=50, b=60)
            )
        except Exception as fig_error:
            return jsonify({'error': f'Failed to create figure: {str(fig_error)}'}), 400
        
        if export_format == 'pdf':
            try:
                # Clean up figure for PDF export - remove any problematic properties
                # Make a copy to avoid modifying the original
                export_fig = go.Figure(fig)
                
                # Ensure clean layout for PDF export
                export_fig.update_layout(
                    autosize=False,
                    width=800,
                    height=600
                )
                
                # Export as PDF with explicit engine configuration
                pdf_bytes = pio.to_image(export_fig, format='pdf', width=800, height=600, scale=1, engine='kaleido')
                
                response = flask.make_response(pdf_bytes)
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Content-Disposition'] = 'attachment; filename="clearview_plot.pdf"'
                response.headers['Content-Length'] = len(pdf_bytes)
                return response
            except Exception as pdf_error:
                # If Kaleido fails, try alternative: create PNG then convert via HTML
                try:
                    # Generate HTML with print-optimized styles
                    html_string = pio.to_html(fig, 
                                             include_plotlyjs=True,
                                             config={'displayModeBar': False, 'responsive': False},
                                             div_id='clearview-plot')
                    
                    # Add print-specific CSS
                    print_html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>ClearView Plot</title>
                        <style>
                            @media print {{
                                body {{ margin: 0; }}
                                #clearview-plot {{ width: 100%; height: 100vh; }}
                            }}
                            body {{ font-family: Arial, sans-serif; margin: 0; }}
                        </style>
                    </head>
                    <body>
                        {html_string.split('<body>')[1]}
                    """
                    
                    response = flask.make_response(print_html)
                    response.headers['Content-Type'] = 'text/html'
                    response.headers['Content-Disposition'] = 'attachment; filename="clearview_plot_printable.html"'
                    return response
                    
                except Exception as fallback_error:
                    return jsonify({'error': f'PDF export failed: {str(pdf_error)}. Fallback failed: {str(fallback_error)}'}), 500
            
        elif export_format == 'html':
            # Export as standalone HTML
            html_string = pio.to_html(fig, 
                                     include_plotlyjs=True,
                                     config={'displayModeBar': True, 'responsive': True},
                                     div_id='clearview-plot')
            
            # Add some styling to the HTML
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>ClearView Plot Export</title>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #00aedb; text-align: center; }}
                    .plot-container {{ text-align: center; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <h1>🌊 ClearView - CE-QUAL-W2 Data Analysis</h1>
                <div class="plot-container">
                    {html_string}
                </div>
                <p style="text-align: center; color: #666; font-size: 12px;">
                    Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </body>
            </html>
            """
            
            response = flask.make_response(full_html)
            response.headers['Content-Type'] = 'text/html'
            response.headers['Content-Disposition'] = 'attachment; filename="clearview_plot.html"'
            response.headers['Content-Length'] = len(full_html.encode())
            return response
            
        else:
            return jsonify({'error': f'Unsupported export format: {export_format}'}), 400
            
    except Exception as e:
        print(f"Plot export error: {e}")
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

@app.route('/apply_method', methods=['POST'])
def apply_method():
    """Apply statistical method to data"""
    try:
        if data_store['df'] is None:
            return jsonify({'error': 'No data loaded'})
        
        data = request.get_json()
        column = data.get('column', '')
        method = data.get('method', '')
        
        if not column or not method:
            return jsonify({'error': 'Column and method are required'})
        
        df = data_store['df']
        
        if column not in df.columns:
            return jsonify({'error': f'Column "{column}" not found'})
        
        # Get the column data
        series = df[column]
        
        # Apply the statistical method
        method_name = method.replace('_', ' ').title()
        
        # Ensure we have a datetime index for time-based operations
        if not isinstance(df.index, pd.DatetimeIndex):
            return jsonify({'error': 'Datetime index required but not found'})
        
        if method == 'hourly_mean':
            result = series.resample('h').mean().interpolate()
        elif method == 'hourly_max':
            result = series.resample('h').max().interpolate()
        elif method == 'hourly_min':
            result = series.resample('h').min().interpolate()
        elif method == 'daily_mean':
            result = series.resample('D').mean().interpolate()
        elif method == 'daily_max':
            result = series.resample('D').max().interpolate()
        elif method == 'daily_min':
            result = series.resample('D').min().interpolate()
        elif method == 'weekly_mean':
            result = series.resample('W').mean().interpolate()
        elif method == 'weekly_max':
            result = series.resample('W').max().interpolate()
        elif method == 'weekly_min':
            result = series.resample('W').min().interpolate()
        elif method == 'monthly_mean':
            result = series.resample('M').mean().interpolate()
        elif method == 'monthly_max':
            result = series.resample('M').max().interpolate()
        elif method == 'monthly_min':
            result = series.resample('M').min().interpolate()
        elif method == 'annual_mean':
            result = series.resample('Y').mean().interpolate()
        elif method == 'annual_max':
            result = series.resample('Y').max().interpolate()
        elif method == 'annual_min':
            result = series.resample('Y').min().interpolate()
        elif method == 'cumulative_sum':
            result = series.cumsum()
        elif method == 'cumulative_max':
            result = series.cummax()
        elif method == 'cumulative_min':
            result = series.cummin()
        elif method == 'rolling_mean_7':
            result = series.rolling(window=7).mean()
        elif method == 'rolling_mean_30':
            result = series.rolling(window=30).mean()
        elif method == 'rolling_std_7':
            result = series.rolling(window=7).std()
        elif method == 'rolling_std_30':
            result = series.rolling(window=30).std()
        else:
            return jsonify({'error': f'Unknown method: {method}'})
        
        # Create result DataFrame with datetime index
        result_df = pd.DataFrame({
            'DateTime': result.index.strftime('%Y-%m-%d %H:%M:%S') if isinstance(result.index, pd.DatetimeIndex) else result.index,
            column + '_' + method: result.values
        })
        
        # Generate HTML table for display
        result_table = result_df.head(20).to_html(classes='data-table', index=False)
        
        # Generate CSV data for download
        csv_data = result_df.to_csv(index=False)
        
        return jsonify({
            'method_name': method_name,
            'column': column,
            'method': method,
            'original_count': len(series),
            'result_count': len(result),
            'result_table': result_table,
            'csv_data': csv_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

def export_data_to_format(df, format_type, filename_base):
    """Export DataFrame to various formats"""
    try:
        if format_type == 'csv':
            output = BytesIO()
            df.to_csv(output, index=True)
            output.seek(0)
            return output, 'text/csv', f'{filename_base}.csv'
            
        elif format_type == 'xlsx':
            output = BytesIO()
            print(f"Creating Excel file for {len(df)} rows, {len(df.columns)} columns")
            try:
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Data', index=True)
                output.seek(0)
                print(f"Excel file created, size: {len(output.getvalue())} bytes")
                return output, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', f'{filename_base}.xlsx'
            except Exception as e:
                print(f"Excel creation error: {e}")
                raise
            
        elif format_type == 'sqlite':
            # Create temporary file for SQLite
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
            temp_file.close()
            
            # Create connection and save data
            conn = sqlite3.connect(temp_file.name)
            df.to_sql('data', conn, if_exists='replace', index=True)
            conn.close()
            
            # Read back as bytes
            with open(temp_file.name, 'rb') as f:
                output = BytesIO(f.read())
            os.unlink(temp_file.name)
            
            output.seek(0)
            return output, 'application/x-sqlite3', f'{filename_base}.db'
            
        elif format_type == 'hdf5':
            output = BytesIO()
            # Create temporary file for HDF5
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.h5')
            temp_file.close()
            
            # Save to HDF5
            df.to_hdf(temp_file.name, key='data', mode='w')
            
            # Read back as bytes
            with open(temp_file.name, 'rb') as f:
                output = BytesIO(f.read())
            os.unlink(temp_file.name)
            
            output.seek(0)
            return output, 'application/x-hdf', f'{filename_base}.h5'
            
        elif format_type == 'netcdf':
            # Create temporary file for NetCDF
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.nc')
            temp_file.close()
            
            def clean_var_name(name):
                """Clean variable name for NetCDF compliance"""
                import re
                # Replace spaces and special characters with underscores
                cleaned = re.sub(r'[^\w]', '_', str(name))
                # Ensure it starts with a letter or underscore
                if cleaned and not (cleaned[0].isalpha() or cleaned[0] == '_'):
                    cleaned = 'var_' + cleaned
                # Remove multiple consecutive underscores
                cleaned = re.sub(r'_{2,}', '_', cleaned)
                # Remove trailing underscores
                cleaned = cleaned.rstrip('_')
                # Ensure it's not empty
                if not cleaned:
                    cleaned = 'variable'
                return cleaned
            
            # Convert DataFrame to xarray and save as NetCDF
            try:
                import xarray as xr
                # Convert to xarray Dataset with cleaned column names
                df_copy = df.reset_index()
                # Clean column names and ensure uniqueness
                column_mapping = {}
                used_names = set()
                for col in df_copy.columns:
                    clean_name = clean_var_name(col)
                    # Ensure uniqueness
                    if clean_name in used_names:
                        counter = 1
                        while f"{clean_name}_{counter}" in used_names:
                            counter += 1
                        clean_name = f"{clean_name}_{counter}"
                    used_names.add(clean_name)
                    column_mapping[col] = clean_name
                df_copy = df_copy.rename(columns=column_mapping)
                
                ds = xr.Dataset.from_dataframe(df_copy)
                ds.to_netcdf(temp_file.name)
            except ImportError:
                # Fallback: manual NetCDF creation
                with nc.Dataset(temp_file.name, 'w', format='NETCDF4') as ncf:
                    # Create dimensions
                    time_dim = ncf.createDimension('time', len(df))
                    
                    # Create time variable
                    if isinstance(df.index, pd.DatetimeIndex):
                        time_var = ncf.createVariable('time', 'f8', ('time',))
                        time_var[:] = nc.date2num(df.index.to_pydatetime(), 
                                                  units='days since 1970-01-01 00:00:00')
                        time_var.units = 'days since 1970-01-01 00:00:00'
                        time_var.calendar = 'gregorian'
                    
                    # Create data variables with cleaned names
                    used_names = set()
                    for col in df.columns:
                        if pd.api.types.is_numeric_dtype(df[col]):
                            clean_name = clean_var_name(col)
                            # Ensure uniqueness
                            if clean_name in used_names:
                                counter = 1
                                while f"{clean_name}_{counter}" in used_names:
                                    counter += 1
                                clean_name = f"{clean_name}_{counter}"
                            used_names.add(clean_name)
                            
                            var = ncf.createVariable(clean_name, 'f8', ('time',))
                            var[:] = df[col].values
                            # Add original name as attribute
                            var.original_name = str(col)
            
            # Read back as bytes
            with open(temp_file.name, 'rb') as f:
                output = BytesIO(f.read())
            os.unlink(temp_file.name)
            
            output.seek(0)
            return output, 'application/x-netcdf', f'{filename_base}.nc'
            
        else:
            raise ValueError(f'Unsupported format: {format_type}')
            
    except Exception as e:
        raise Exception(f'Export failed: {str(e)}')

@app.route('/download/data/<format_type>', methods=['POST'])
def download_data(format_type):
    """Download the main dataset"""
    try:
        print(f"Download request received for format: {format_type}")
        if data_store['df'] is None:
            print("No data loaded")
            return jsonify({'error': 'No data loaded'}), 400
            
        df = data_store['df']
        filename = data_store['filename'] or 'data'
        base_name = os.path.splitext(filename)[0]
        print(f"Processing data export: {len(df)} rows, format: {format_type}")
        
        output, mimetype, filename = export_data_to_format(df, format_type, base_name)
        print(f"Export completed, filename: {filename}")
        
        # Use Flask Response with direct byte content
        output.seek(0)
        content = output.read()
        
        response = flask.make_response(content)
        response.headers['Content-Type'] = mimetype
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Content-Length'] = len(content)
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/stats/<format_type>', methods=['POST'])
def download_stats(format_type):
    """Download the statistics"""
    try:
        if data_store['stats'] is None:
            return jsonify({'error': 'No statistics available'}), 400
            
        df = data_store['stats']
        filename = data_store['filename'] or 'data'
        base_name = os.path.splitext(filename)[0] + '_stats'
        
        output, mimetype, filename = export_data_to_format(df, format_type, base_name)
        
        # Use Flask Response with direct byte content
        output.seek(0)
        content = output.read()
        
        response = flask.make_response(content)
        response.headers['Content-Type'] = mimetype
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Content-Length'] = len(content)
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analyze/correlation', methods=['POST'])
def analyze_correlation():
    """Perform correlation analysis between parameters"""
    try:
        if data_store['df'] is None:
            return jsonify({'error': 'No data loaded'})
        
        data = request.get_json()
        method = data.get('method', 'pearson')
        threshold = data.get('threshold', 0.5)
        
        df = data_store['df']
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        if len(numeric_cols) < 2:
            return jsonify({'error': 'Need at least 2 numeric columns for correlation analysis'})
        
        # Calculate correlation matrix
        corr_matrix = df[numeric_cols].corr(method=method)
        
        # Find significant correlations
        significant_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) >= threshold:
                    significant_pairs.append({
                        'param1': corr_matrix.columns[i],
                        'param2': corr_matrix.columns[j],
                        'correlation': corr_val,
                        'strength': 'Strong' if abs(corr_val) >= 0.7 else 'Moderate' if abs(corr_val) >= 0.5 else 'Weak',
                        'direction': 'Positive' if corr_val > 0 else 'Negative'
                    })
        
        # Sort by absolute correlation value
        significant_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)
        
        # Create HTML output
        html_content = f"""
        <h5>🔗 Correlation Analysis Results</h5>
        <p><strong>Method:</strong> {method.title()} | <strong>Threshold:</strong> |r| ≥ {threshold}</p>
        
        <div style="margin: 20px 0;">
            <h6>📊 Correlation Matrix Heatmap</h6>
            <div style="overflow-x: auto; margin: 10px 0;">
                {corr_matrix.round(3).to_html(classes='data-table', escape=False, table_id='correlation-matrix')}
            </div>
        </div>
        
        <div style="margin: 20px 0;">
            <h6>⭐ Significant Correlations ({len(significant_pairs)} found)</h6>
        """
        
        if significant_pairs:
            html_content += """
            <table class="data-table" style="width: 100%; margin-top: 10px;">
                <tr style="background: #f2f2f2;"><th>Parameter 1</th><th>Parameter 2</th><th>Correlation</th><th>Strength</th><th>Interpretation</th></tr>
            """
            for pair in significant_pairs:
                bg_color = '#e8f5e8' if pair['direction'] == 'Positive' else '#ffe8e8'
                interpretation = f"{pair['direction']} {pair['strength'].lower()} relationship"
                html_content += f"""
                <tr style="background: {bg_color};">
                    <td>{pair['param1']}</td>
                    <td>{pair['param2']}</td>
                    <td style="font-weight: bold;">{pair['correlation']:.3f}</td>
                    <td>{pair['strength']}</td>
                    <td>{interpretation}</td>
                </tr>
                """
            html_content += "</table>"
        else:
            html_content += f"<p style='color: #666; font-style: italic;'>No correlations found above threshold {threshold}</p>"
        
        html_content += """
        </div>
        
        <div style="background: #f0f8ff; padding: 15px; border-radius: 8px; margin-top: 20px;">
            <h6>💡 Interpretation Guide</h6>
            <ul style="margin: 10px 0; padding-left: 20px;">
                <li><strong>Strong (|r| ≥ 0.7):</strong> Parameters are closely related</li>
                <li><strong>Moderate (0.5 ≤ |r| < 0.7):</strong> Parameters have noticeable relationship</li>
                <li><strong>Weak (0.3 ≤ |r| < 0.5):</strong> Parameters have some relationship</li>
                <li><strong>Positive:</strong> As one increases, the other tends to increase</li>
                <li><strong>Negative:</strong> As one increases, the other tends to decrease</li>
            </ul>
        </div>
        """
        
        return jsonify({'html': html_content})
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/analyze/trend', methods=['POST'])
def analyze_trend():
    """Perform trend analysis on selected parameter"""
    try:
        if data_store['df'] is None:
            return jsonify({'error': 'No data loaded'})
        
        data = request.get_json()
        parameter = data.get('parameter')
        analysis_type = data.get('analysis_type', 'trend')
        
        if not parameter:
            return jsonify({'error': 'Parameter is required'})
        
        df = data_store['df']
        if parameter not in df.columns:
            return jsonify({'error': f'Parameter {parameter} not found'})
        
        # Ensure datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            return jsonify({'error': 'Datetime index required for trend analysis'})
        
        series = df[parameter].dropna()
        
        html_content = f"""
        <h5>📈 Trend Analysis: {parameter}</h5>
        <p><strong>Analysis Type:</strong> {analysis_type.title().replace('_', ' ')}</p>
        """
        
        if analysis_type == 'trend':
            # Linear trend analysis
            from scipy import stats
            
            # Convert datetime to numeric for regression
            x = np.arange(len(series))
            y = series.values
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            # Calculate trend per year (approximate)
            days_total = (series.index[-1] - series.index[0]).days
            years_total = days_total / 365.25
            trend_per_year = slope * len(series) / years_total if years_total > 0 else 0
            
            significance = 'Significant' if p_value < 0.05 else 'Not Significant'
            trend_direction = 'Increasing' if slope > 0 else 'Decreasing' if slope < 0 else 'No Trend'
            
            html_content += f"""
            <div style="margin: 20px 0;">
                <h6>📊 Linear Trend Results</h6>
                <table class="data-table" style="width: 100%;">
                    <tr><td><strong>Trend Direction</strong></td><td>{trend_direction}</td></tr>
                    <tr><td><strong>Slope</strong></td><td>{slope:.6f} units per time step</td></tr>
                    <tr><td><strong>Trend per Year</strong></td><td>{trend_per_year:.4f} units/year</td></tr>
                    <tr><td><strong>R-squared</strong></td><td>{r_value**2:.4f}</td></tr>
                    <tr><td><strong>P-value</strong></td><td>{p_value:.6f}</td></tr>
                    <tr><td><strong>Statistical Significance</strong></td><td style="font-weight: bold; color: {'green' if p_value < 0.05 else 'orange'};">{significance}</td></tr>
                </table>
            </div>
            """
            
        elif analysis_type == 'seasonal':
            # Seasonal decomposition (simplified)
            monthly_means = series.groupby(series.index.month).mean()
            seasonal_range = monthly_means.max() - monthly_means.min()
            peak_month = monthly_means.idxmax()
            low_month = monthly_means.idxmin()
            
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            
            html_content += f"""
            <div style="margin: 20px 0;">
                <h6>🗓️ Seasonal Patterns</h6>
                <table class="data-table" style="width: 100%;">
                    <tr><td><strong>Seasonal Range</strong></td><td>{seasonal_range:.4f} units</td></tr>
                    <tr><td><strong>Peak Month</strong></td><td>{month_names[peak_month-1]} (avg: {monthly_means[peak_month]:.4f})</td></tr>
                    <tr><td><strong>Low Month</strong></td><td>{month_names[low_month-1]} (avg: {monthly_means[low_month]:.4f})</td></tr>
                </table>
                
                <h6>📅 Monthly Averages</h6>
                <table class="data-table" style="width: 100%;">
                    <tr style="background: #f2f2f2;"><th>Month</th><th>Average Value</th></tr>
            """
            
            for month, avg in monthly_means.items():
                html_content += f"<tr><td>{month_names[month-1]}</td><td>{avg:.4f}</td></tr>"
            
            html_content += "</table></div>"
        
        elif analysis_type == 'changepoint':
            # Simple change point detection using rolling statistics
            window = max(30, len(series) // 10)  # Adaptive window size
            rolling_mean = series.rolling(window=window, center=True).mean()
            rolling_std = series.rolling(window=window, center=True).std()
            
            # Find significant changes in mean
            mean_changes = rolling_mean.diff().abs()
            significant_changes = mean_changes[mean_changes > mean_changes.quantile(0.95)].dropna()
            
            html_content += f"""
            <div style="margin: 20px 0;">
                <h6>📍 Change Point Analysis</h6>
                <p><strong>Detection Window:</strong> {window} time steps</p>
                <p><strong>Potential Change Points:</strong> {len(significant_changes)}</p>
                
                {f"<h6>🎯 Significant Changes Detected</h6>" if len(significant_changes) > 0 else ""}
            """
            
            if len(significant_changes) > 0:
                html_content += '<table class="data-table" style="width: 100%;"><tr style="background: #f2f2f2;"><th>Date</th><th>Change Magnitude</th></tr>'
                for date, change in significant_changes.head(10).items():
                    html_content += f'<tr><td>{date.strftime("%Y-%m-%d")}</td><td>{change:.4f}</td></tr>'
                html_content += "</table>"
            else:
                html_content += "<p style='color: #666; font-style: italic;'>No significant change points detected</p>"
            
            html_content += "</div>"
        
        html_content += """
        <div style="background: #f0f8ff; padding: 15px; border-radius: 8px; margin-top: 20px;">
            <h6>💡 Analysis Notes</h6>
            <ul style="margin: 10px 0; padding-left: 20px;">
                <li><strong>Linear Trend:</strong> Tests for monotonic increase/decrease over time</li>
                <li><strong>Seasonal Patterns:</strong> Examines monthly variations</li>
                <li><strong>Change Points:</strong> Identifies sudden shifts in data behavior</li>
                <li><strong>P-value < 0.05:</strong> Indicates statistically significant trend</li>
            </ul>
        </div>
        """
        
        return jsonify({'html': html_content})
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/analyze/wqi', methods=['POST'])
def calculate_water_quality_index():
    """Calculate Water Quality Index"""
    try:
        if data_store['df'] is None:
            return jsonify({'error': 'No data loaded'})
        
        data = request.get_json()
        wqi_type = data.get('wqi_type', 'basic')
        custom_params = data.get('parameters', [])
        
        df = data_store['df']
        
        html_content = f"""
        <h5>🌊 Water Quality Index Results</h5>
        <p><strong>Index Type:</strong> {wqi_type.title()}</p>
        """
        
        if wqi_type == 'basic':
            # Basic WQI using DO, pH, Temperature
            required_params = ['DO', 'pH', 'Temperature', 'T(C)', 'TEMP']
            available_params = {}
            
            for param in required_params:
                matches = [col for col in df.columns if param.lower() in col.lower()]
                if matches:
                    available_params[param] = matches[0]
            
            if len(available_params) < 2:
                return jsonify({'error': 'Insufficient parameters for Basic WQI. Need DO, pH, and/or Temperature columns'})
            
            # Simple WQI calculation (0-100 scale)
            wqi_scores = []
            param_results = {}
            
            for param, col_name in available_params.items():
                values = df[col_name].dropna()
                
                if 'do' in param.lower():
                    # DO: optimal range 7-10 mg/L
                    scores = np.where(values >= 7, 
                                     np.minimum(100, 100 - (values - 10)**2), 
                                     np.maximum(0, values * 14.3))  # Linear scale 0-7
                elif 'ph' in param.lower():
                    # pH: optimal range 6.5-8.5
                    scores = np.maximum(0, 100 - np.abs(values - 7.5) * 20)
                elif 'temp' in param.lower():
                    # Temperature: penalize extremes
                    scores = np.maximum(0, 100 - np.abs(values - 20) * 2)  # Optimal ~20°C
                else:
                    scores = np.full(len(values), 50)  # Default neutral score
                
                param_results[param] = {
                    'column': col_name,
                    'mean_score': np.mean(scores),
                    'min_score': np.min(scores),
                    'max_score': np.max(scores)
                }
                wqi_scores.append(scores)
            
            # Overall WQI (average of parameter scores)
            overall_wqi = np.mean(wqi_scores, axis=0)
            mean_wqi = np.mean(overall_wqi)
            
            # WQI classification
            if mean_wqi >= 90:
                wqi_class = 'Excellent'
                class_color = '#28a745'
            elif mean_wqi >= 70:
                wqi_class = 'Good'
                class_color = '#17a2b8'
            elif mean_wqi >= 50:
                wqi_class = 'Fair'
                class_color = '#ffc107'
            elif mean_wqi >= 25:
                wqi_class = 'Poor'
                class_color = '#fd7e14'
            else:
                wqi_class = 'Very Poor'
                class_color = '#dc3545'
            
            html_content += f"""
            <div style="margin: 20px 0;">
                <h6>📊 Overall Water Quality</h6>
                <div style="background: {class_color}; color: white; padding: 15px; border-radius: 8px; text-align: center; margin: 10px 0;">
                    <h4 style="margin: 0;">WQI: {mean_wqi:.1f}</h4>
                    <h5 style="margin: 5px 0 0 0;">{wqi_class}</h5>
                </div>
            </div>
            
            <div style="margin: 20px 0;">
                <h6>📋 Parameter Scores</h6>
                <table class="data-table" style="width: 100%;">
                    <tr style="background: #f2f2f2;"><th>Parameter</th><th>Column</th><th>Mean Score</th><th>Range</th></tr>
            """
            
            for param, results in param_results.items():
                html_content += f"""
                <tr>
                    <td>{param}</td>
                    <td>{results['column']}</td>
                    <td>{results['mean_score']:.1f}</td>
                    <td>{results['min_score']:.1f} - {results['max_score']:.1f}</td>
                </tr>
                """
            
            html_content += "</table></div>"
            
        elif wqi_type == 'trophic':
            # Trophic State Index (simplified)
            chlorophyll_cols = [col for col in df.columns if 'chla' in col.lower() or 'chlorophyll' in col.lower()]
            
            if not chlorophyll_cols:
                return jsonify({'error': 'Chlorophyll-a data required for Trophic State Index'})
            
            chla_data = df[chlorophyll_cols[0]].dropna()
            
            # Carlson's TSI for Chlorophyll-a
            tsi_values = 9.81 * np.log(chla_data) + 30.6
            mean_tsi = np.mean(tsi_values)
            
            # TSI classification
            if mean_tsi < 40:
                tsi_class = 'Oligotrophic (nutrient poor)'
                class_color = '#007bff'
            elif mean_tsi < 50:
                tsi_class = 'Mesotrophic (moderate nutrients)'
                class_color = '#28a745'
            elif mean_tsi < 70:
                tsi_class = 'Eutrophic (nutrient rich)'
                class_color = '#ffc107'
            else:
                tsi_class = 'Hypereutrophic (excessive nutrients)'
                class_color = '#dc3545'
            
            html_content += f"""
            <div style="margin: 20px 0;">
                <h6>🌱 Trophic State Assessment</h6>
                <div style="background: {class_color}; color: white; padding: 15px; border-radius: 8px; text-align: center; margin: 10px 0;">
                    <h4 style="margin: 0;">TSI: {mean_tsi:.1f}</h4>
                    <h5 style="margin: 5px 0 0 0;">{tsi_class}</h5>
                </div>
                
                <table class="data-table" style="width: 100%; margin-top: 15px;">
                    <tr><td><strong>Parameter Used</strong></td><td>{chlorophyll_cols[0]}</td></tr>
                    <tr><td><strong>Mean Chlorophyll-a</strong></td><td>{np.mean(chla_data):.2f} µg/L</td></tr>
                    <tr><td><strong>TSI Range</strong></td><td>{np.min(tsi_values):.1f} - {np.max(tsi_values):.1f}</td></tr>
                </table>
            </div>
            """
            
        html_content += """
        <div style="background: #f0f8ff; padding: 15px; border-radius: 8px; margin-top: 20px;">
            <h6>💡 WQI Scale Reference</h6>
            <ul style="margin: 10px 0; padding-left: 20px;">
                <li><strong>90-100:</strong> Excellent water quality</li>
                <li><strong>70-89:</strong> Good water quality</li>
                <li><strong>50-69:</strong> Fair water quality</li>
                <li><strong>25-49:</strong> Poor water quality</li>
                <li><strong>0-24:</strong> Very poor water quality</li>
            </ul>
        </div>
        """
        
        return jsonify({'html': html_content})
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/analyze/anomalies', methods=['POST'])
def detect_anomalies_analysis():
    """Detect anomalies in the dataset"""
    try:
        if data_store['df'] is None:
            return jsonify({'error': 'No data loaded'})
        
        data = request.get_json()
        method = data.get('method', 'zscore')
        sensitivity = data.get('sensitivity', 'medium')
        
        # Handle numeric sensitivity values
        if isinstance(sensitivity, (int, float)):
            # Convert numeric to string equivalent
            if sensitivity <= 2.0:
                sensitivity = 'high'
            elif sensitivity <= 3.0:
                sensitivity = 'medium'
            else:
                sensitivity = 'low'
        
        df = data_store['df']
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        if len(numeric_cols) == 0:
            return jsonify({'error': 'No numeric columns found for anomaly detection'})
        
        # Sensitivity thresholds
        thresholds = {
            'low': {'zscore': 3.5, 'iqr': 3.0},
            'medium': {'zscore': 3.0, 'iqr': 2.5},
            'high': {'zscore': 2.5, 'iqr': 2.0}
        }
        
        anomaly_results = {}
        total_anomalies = 0
        
        html_content = f"""
        <h5>🚨 Anomaly Detection Results</h5>
        <p><strong>Method:</strong> {method.title()} | <strong>Sensitivity:</strong> {sensitivity.title()}</p>
        """
        
        for col in numeric_cols:
            data_series = df[col].dropna()
            if len(data_series) < 10:  # Skip columns with too little data
                continue
            
            anomalies = []
            
            if method == 'zscore':
                z_scores = np.abs(stats.zscore(data_series))
                threshold = thresholds[sensitivity]['zscore']
                anomaly_mask = z_scores > threshold
                anomalies = data_series[anomaly_mask]
                
            elif method == 'iqr':
                Q1 = data_series.quantile(0.25)
                Q3 = data_series.quantile(0.75)
                IQR = Q3 - Q1
                multiplier = thresholds[sensitivity]['iqr']
                
                lower_bound = Q1 - multiplier * IQR
                upper_bound = Q3 + multiplier * IQR
                
                anomaly_mask = (data_series < lower_bound) | (data_series > upper_bound)
                anomalies = data_series[anomaly_mask]
            
            if len(anomalies) > 0:
                anomaly_results[col] = {
                    'count': len(anomalies),
                    'percentage': (len(anomalies) / len(data_series)) * 100,
                    'min_anomaly': anomalies.min(),
                    'max_anomaly': anomalies.max(),
                    'dates': anomalies.index.strftime('%Y-%m-%d').tolist()[:5] if isinstance(df.index, pd.DatetimeIndex) else []
                }
                total_anomalies += len(anomalies)
        
        # Summary
        html_content += f"""
        <div style="margin: 20px 0;">
            <h6>📊 Detection Summary</h6>
            <table class="data-table" style="width: 100%;">
                <tr><td><strong>Total Anomalies Detected</strong></td><td style="font-weight: bold; color: #dc3545;">{total_anomalies}</td></tr>
                <tr><td><strong>Parameters Analyzed</strong></td><td>{len(numeric_cols)}</td></tr>
                <tr><td><strong>Parameters with Anomalies</strong></td><td>{len(anomaly_results)}</td></tr>
            </table>
        </div>
        """
        
        if anomaly_results:
            html_content += """
            <div style="margin: 20px 0;">
                <h6>🎯 Anomalies by Parameter</h6>
                <table class="data-table" style="width: 100%;">
                    <tr style="background: #f2f2f2;">
                        <th>Parameter</th><th>Count</th><th>Percentage</th><th>Range</th><th>Sample Dates</th>
                    </tr>
            """
            
            for param, results in sorted(anomaly_results.items(), key=lambda x: x[1]['count'], reverse=True):
                dates_str = ', '.join(results['dates'][:3])
                if len(results['dates']) > 3:
                    dates_str += f" (+{len(results['dates'])-3} more)"
                
                # Color code by severity
                if results['percentage'] > 10:
                    row_color = '#ffebee'  # High anomaly rate
                elif results['percentage'] > 5:
                    row_color = '#fff3e0'  # Medium anomaly rate
                else:
                    row_color = '#ffffff'  # Low anomaly rate
                
                html_content += f"""
                <tr style="background: {row_color};">
                    <td style="font-weight: bold;">{param}</td>
                    <td>{results['count']}</td>
                    <td>{results['percentage']:.1f}%</td>
                    <td>{results['min_anomaly']:.3f} - {results['max_anomaly']:.3f}</td>
                    <td style="font-size: 12px;">{dates_str}</td>
                </tr>
                """
            
            html_content += "</table></div>"
        else:
            html_content += """
            <div style="margin: 20px 0; text-align: center; color: #28a745;">
                <h6>✅ No Anomalies Detected</h6>
                <p>All data points fall within expected ranges using the selected method and sensitivity.</p>
            </div>
            """
        
        html_content += """
        <div style="background: #f0f8ff; padding: 15px; border-radius: 8px; margin-top: 20px;">
            <h6>💡 Detection Methods</h6>
            <ul style="margin: 10px 0; padding-left: 20px;">
                <li><strong>Z-Score:</strong> Identifies values beyond ±2.5-3.5 standard deviations</li>
                <li><strong>IQR:</strong> Uses interquartile range to find outliers beyond Q1-k*IQR or Q3+k*IQR</li>
                <li><strong>High Sensitivity:</strong> Detects more anomalies (may include false positives)</li>
                <li><strong>Low Sensitivity:</strong> Detects fewer anomalies (focuses on extreme outliers)</li>
            </ul>
        </div>
        """
        
        return jsonify({'html': html_content})
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/download/method/<format_type>', methods=['POST'])
def download_method_results(format_type):
    """Download method results"""
    try:
        request_data = request.get_json() or {}
        
        if 'csv_data' not in request_data:
            return jsonify({'error': 'No method results available'}), 400
            
        # Parse the CSV data back into a DataFrame
        from io import StringIO
        csv_data = request_data['csv_data']
        df = pd.read_csv(StringIO(csv_data))
        
        # Try to parse DateTime column if present
        if 'DateTime' in df.columns:
            try:
                df['DateTime'] = pd.to_datetime(df['DateTime'])
                df.set_index('DateTime', inplace=True)
            except:
                pass
        
        column = request_data.get('column', 'data')
        method = request_data.get('method', 'processed')
        base_name = f"{column}_{method}"
        
        output, mimetype, filename = export_data_to_format(df, format_type, base_name)
        
        # Use Flask Response with direct byte content
        output.seek(0)
        content = output.read()
        
        response = flask.make_response(content)
        response.headers['Content-Type'] = mimetype
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Content-Length'] = len(content)
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_stats', methods=['POST'])
def get_stats():
    """Get current data statistics for auto-refresh"""
    try:
        if data_store['df'] is None:
            return jsonify({'error': 'No data loaded'}), 400
            
        df = data_store['df']
        
        # Calculate basic stats
        stats = {
            'rows': len(df),
            'columns': len(df.columns),
            'missing_values': int(df.isnull().sum().sum()),
            'quality_score': data_store.get('validation', {}).get('data_quality_score', 0)
        }
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/monitor_parameter', methods=['POST'])
def monitor_parameter():
    """Monitor a specific parameter for real-time updates"""
    try:
        if data_store['df'] is None:
            return jsonify({'error': 'No data loaded'}), 400
            
        request_data = request.get_json() or {}
        parameter = request_data.get('parameter')
        
        if not parameter:
            return jsonify({'error': 'No parameter specified'}), 400
            
        df = data_store['df']
        
        if parameter not in df.columns:
            return jsonify({'error': f'Parameter {parameter} not found'}), 400
            
        # Calculate parameter statistics
        data_series = df[parameter].dropna()
        
        if len(data_series) == 0:
            return jsonify({'error': f'No valid data for parameter {parameter}'}), 400
            
        stats = {
            'current_value': float(data_series.iloc[-1]) if len(data_series) > 0 else None,
            'mean': float(data_series.mean()),
            'std': float(data_series.std()),
            'min': float(data_series.min()),
            'max': float(data_series.max()),
            'count': int(len(data_series))
        }
        
        # Check for alerts based on statistical thresholds
        alert = None
        if stats['current_value'] is not None:
            z_score = (stats['current_value'] - stats['mean']) / stats['std'] if stats['std'] > 0 else 0
            if abs(z_score) > 3:
                alert = f"⚠️ Current value ({stats['current_value']:.3f}) is {abs(z_score):.1f} standard deviations from mean"
            elif abs(z_score) > 2:
                alert = f"ℹ️ Current value is moderately outside normal range"
                
        stats['alert'] = alert
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def simulate_live_data():
    """Simulate live data streaming for demonstration purposes"""
    while data_store['live_stream']:
        if data_store['df'] is not None and len(data_store['df']) > 0:
            # Simulate new data point based on existing data patterns
            df = data_store['df']
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            if len(numeric_cols) > 0:
                # Create new data point with some variation
                new_point = {}
                timestamp = datetime.datetime.now()
                
                for col in numeric_cols:
                    # Get recent mean and std for realistic simulation
                    recent_data = df[col].dropna().tail(50)
                    if len(recent_data) > 0:
                        mean_val = recent_data.mean()
                        std_val = recent_data.std()
                        # Add some random variation
                        new_val = mean_val + random.gauss(0, max(std_val, 0.1))
                        new_point[col] = new_val
                
                new_point['timestamp'] = timestamp.isoformat()
                data_store['stream_data'].append(new_point)
                
                # Keep only recent points (last 100)
                if len(data_store['stream_data']) > 100:
                    data_store['stream_data'] = data_store['stream_data'][-100:]
        
        time.sleep(2)  # Update every 2 seconds

@app.route('/start_live_stream', methods=['POST'])
def start_live_stream():
    """Start live data streaming"""
    try:
        if data_store['df'] is None:
            return jsonify({'error': 'No data loaded'}), 400
            
        if not data_store['live_stream']:
            data_store['live_stream'] = True
            data_store['stream_data'] = []
            
            # Start streaming thread
            stream_thread = threading.Thread(target=simulate_live_data, daemon=True)
            stream_thread.start()
            data_store['stream_thread'] = stream_thread
            
        return jsonify({'success': True, 'message': 'Live streaming started'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stop_live_stream', methods=['POST'])
def stop_live_stream():
    """Stop live data streaming"""
    try:
        data_store['live_stream'] = False
        data_store['stream_data'] = []
        
        return jsonify({'success': True, 'message': 'Live streaming stopped'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_live_data', methods=['POST'])
def get_live_data():
    """Get latest live data points"""
    try:
        request_data = request.get_json() or {}
        parameter = request_data.get('parameter', '')
        
        if not data_store['live_stream']:
            return jsonify({'error': 'Live streaming not active'}), 400
            
        # Return recent stream data
        live_points = []
        for point in data_store['stream_data'][-20:]:  # Last 20 points
            if parameter and parameter in point:
                live_points.append({
                    'timestamp': point['timestamp'],
                    'value': point[parameter],
                    'parameter': parameter
                })
            elif not parameter:
                live_points.append(point)
        
        # Calculate streaming statistics
        if live_points and parameter:
            values = [p['value'] for p in live_points]
            stats = {
                'current': values[-1] if values else None,
                'mean': np.mean(values) if values else None,
                'std': np.std(values) if len(values) > 1 else 0,
                'count': len(values),
                'trend': 'increasing' if len(values) > 1 and values[-1] > values[0] else 'stable'
            }
        else:
            stats = None
            
        return jsonify({
            'success': True,
            'data': live_points,
            'stats': stats,
            'streaming': data_store['live_stream']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🌊 Starting ClearView Flask Data Viewer...")
    print("🌐 Open browser to: http://localhost:9999")
    app.run(host='127.0.0.1', port=9999, debug=False)