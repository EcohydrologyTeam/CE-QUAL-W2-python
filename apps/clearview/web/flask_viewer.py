#!/usr/bin/env python3
"""
ClearView Flask app - Restored with working Methods tab
Original design with all features working
"""

from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify, send_file, make_response
import pandas as pd
import io
import os
import json
import plotly.graph_objs as go
import plotly.utils
import plotly.io as pio
import datetime
import numpy as np
import sqlite3
import tempfile
import h5py
try:
    import netCDF4 as nc
    import xarray as xr
    NETCDF_AVAILABLE = True
except ImportError:
    NETCDF_AVAILABLE = False

# Import cequalw2 for JDAY conversion
try:
    from cequalw2.utils.datetime import day_of_year_to_datetime
    CEQUALW2_AVAILABLE = True
except ImportError:
    CEQUALW2_AVAILABLE = False

app = Flask(__name__)
app.secret_key = 'clearview-secret-key'

# Global variable to store data
data_store = {
    'df': None,
    'filename': None,
    'stats': None,
    'file_info': None,
    'year': datetime.datetime.now().year  # Default to current year
}

def read_file_with_validation(file_content, filename):
    """Read file with basic validation"""
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(file_content)
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_content)
        else:
            # Try CSV as fallback
            df = pd.read_csv(file_content)
        
        return df, {'format': 'CSV', 'encoding': 'utf-8'}
    except Exception as e:
        raise Exception(f"Error reading file: {e}")

COMPLETE_TEMPLATE = """
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
        .btn.danger { background: #e74c3c; color: white; }
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
        
        /* Proper tab styling */
        .tabs { display: flex; margin: 20px 0 0 0; }
        .tab { 
            background: gold; 
            color: black; 
            padding: 10px 20px; 
            cursor: pointer; 
            border: 1px solid #bdc3c7; 
            margin-right: 2px; 
            font-size: 14px; 
            text-align: center; 
            font-weight: bold; 
            min-width: 100px;
        }
        .tab.active { background: #00aedb; color: black; }
        /* No hover effect - tabs stay gold unless active */
        .tab-content { border: 1px solid #bdc3c7; padding: 20px; display: none; }
        .tab-content.active { display: block; }
    </style>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">🌊 ClearView - CE-QUAL-W2 Data Viewer</h1>
            <p style="margin: 10px 0 0 0;">Advanced water quality data analysis and visualization</p>
        </div>
        
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="success">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        {% if data_store.df is none %}
        <div class="upload-area">
            <h2>📁 Upload Data File</h2>
            <form id="upload-form" method="POST" enctype="multipart/form-data">
                <input type="file" id="file-input" name="file" accept=".csv,.xlsx,.xls,.npt,.opt" required style="margin: 10px;">
                <button type="submit" class="btn">🔄 Load Data</button>
            </form>
            <p style="color: #7f8c8d; margin-top: 15px;">
                Supported formats: CSV, Excel (.xlsx/.xls), NPT, OPT files<br>
                Maximum file size: 50MB
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
                <div class="tab" onclick="showTab('methods-tab')">⚗️ Methods</div>
                <div class="tab" onclick="showTab('info-tab')">ℹ️ Info</div>
            </div>
            <button onclick="clearData()" class="btn danger" style="margin-left: 20px;">
                ❌ Close File
            </button>
        </div>
        
        <div id="data-tab" class="tab-content active">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="margin: 0;">📊 Complete Data Table</h3>
                <div>
                    <select id="export-format" style="margin-right: 10px; padding: 5px;">
                        <option value="csv">CSV (.csv)</option>
                        <option value="excel">Excel (.xlsx)</option>
                        <option value="sqlite">SQLite (.db)</option>
                        <option value="hdf5">HDF5 (.h5)</option>
                        {% if netcdf_available %}
                        <option value="netcdf">NetCDF (.nc)</option>
                        {% endif %}
                    </select>
                    <button onclick="exportData()" class="btn">📥 Export Data</button>
                </div>
            </div>
            
            <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 15px;">
                <strong>📄 File:</strong> {{ data_store.filename or 'No file loaded' }} &nbsp;|&nbsp;
                <strong>📊 Shape:</strong> {{ "{:,}".format(data_store.df.shape[0]) }} rows × {{ data_store.df.shape[1] }} columns &nbsp;|&nbsp;
                <strong>🗂️ Columns:</strong> {{ ', '.join(data_store.df.columns.tolist()[:6]) }}{% if data_store.df.shape[1] > 6 %} ... ({{ data_store.df.shape[1] - 6 }} more){% endif %}
            </div>
            
            <div class="table-container" style="max-height: 600px; overflow: auto; border: 2px solid #ddd; border-radius: 5px;">
                {{ data_store.df.to_html(classes='data-table', table_id='full-data-table', max_rows=None)|safe }}
            </div>
            
            <div style="margin-top: 10px; color: #7f8c8d; font-size: 12px;">
                💡 Tip: This table shows all {{ "{:,}".format(data_store.df.shape[0]) }} rows. Use the export button above to save data in various formats.
            </div>
        </div>
        
        <div id="stats-tab" class="tab-content">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="margin: 0;">📈 Statistical Summary</h3>
                <div>
                    <select id="stats-export-format" style="margin-right: 10px; padding: 5px;">
                        <option value="csv">CSV (.csv)</option>
                        <option value="excel">Excel (.xlsx)</option>
                        <option value="sqlite">SQLite (.db)</option>
                        <option value="hdf5">HDF5 (.h5)</option>
                        {% if netcdf_available %}
                        <option value="netcdf">NetCDF (.nc)</option>
                        {% endif %}
                    </select>
                    <button onclick="exportStats()" class="btn">📥 Export Stats</button>
                </div>
            </div>
            
            <div class="table-container" style="max-height: 500px; overflow: auto; border: 2px solid #ddd; border-radius: 5px;">
                {{ data_store.df.describe().to_html(classes='stats-table', table_id='stats-table')|safe }}
            </div>
            
            <div style="margin-top: 10px; color: #7f8c8d; font-size: 12px;">
                💡 Statistical summary includes count, mean, std, min, 25%, 50%, 75%, max for numeric columns
            </div>
        </div>
        
        <div id="plot-tab" class="tab-content">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="margin: 0;">📈 Interactive Plotting</h3>
                <div>
                    <select id="plot-export-format" style="margin-right: 10px; padding: 5px;">
                        <option value="png">PNG (.png)</option>
                        <option value="jpg">JPEG (.jpg)</option>
                        <option value="svg">SVG (.svg)</option>
                        <option value="html">Interactive HTML (.html)</option>
                        <option value="pdf">PDF (.pdf)</option>
                    </select>
                    <button onclick="exportPlot()" class="btn">📥 Export Plot</button>
                </div>
            </div>
            
            <div style="background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px;">
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 15px;">
                    
                    <div>
                        <label for="x-column"><strong>X-axis:</strong></label>
                        <select id="x-column" style="width: 100%; margin-top: 5px;">
                            <option value="">📊 Row Index</option>
                            <option value="datetime">📅 DateTime (JDAY conversion)</option>
                            {% for col in data_store.df.columns %}
                            <option value="{{ col }}">{{ col }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div>
                        <label for="y-column"><strong>Y-axis:</strong></label>
                        <select id="y-column" style="width: 100%; margin-top: 5px;">
                            {% for col in data_store.df.select_dtypes(include=['number']).columns %}
                            <option value="{{ col }}">{{ col }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div>
                        <label for="plot-year"><strong>Year (for JDAY):</strong></label>
                        <input type="number" id="plot-year" value="{{ data_store.year }}" min="1900" max="2100" style="width: 100%; margin-top: 5px;">
                        <div style="margin-top: 10px;">
                            <input type="checkbox" id="show-markers" checked>
                            <label for="show-markers">Markers</label>
                            <input type="checkbox" id="show-grid" checked style="margin-left: 10px;">
                            <label for="show-grid">Grid</label>
                        </div>
                    </div>
                    
                    <div>
                        <label>&nbsp;</label><br>
                        <button onclick="updatePlot()" class="btn" style="width: 100%; margin-top: 5px;">📈 Create Plot</button>
                        <div style="margin-top: 10px; font-size: 11px; color: #666;">
                            💡 DateTime converts JDAY column using specified year
                        </div>
                    </div>
                </div>
            </div>
            
            <div id="plot-container" style="width: 100%; height: 500px; border: 2px solid #ddd; border-radius: 5px;">
                <p style="text-align: center; color: #7f8c8d; padding: 50px;">Select parameters and click "Create Plot" to visualize your data</p>
            </div>
            
            <div style="margin-top: 10px; color: #7f8c8d; font-size: 12px;">
                💡 Tip: Use DateTime for time-series data. Export plots in various formats using the export button above.
            </div>
        </div>
        
        <div id="methods-tab" class="tab-content">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="margin: 0;">⚗️ Time Series Analysis Methods</h3>
                <div>
                    <select id="method-export-format" style="margin-right: 10px; padding: 5px;">
                        <option value="csv">CSV (.csv)</option>
                        <option value="excel">Excel (.xlsx)</option>
                        <option value="sqlite">SQLite (.db)</option>
                        <option value="hdf5">HDF5 (.h5)</option>
                        {% if netcdf_available %}
                        <option value="netcdf">NetCDF (.nc)</option>
                        {% endif %}
                    </select>
                    <button onclick="exportMethodResults()" class="btn">📥 Export Results</button>
                </div>
            </div>
            
            <p style="color: #7f8c8d; margin: 10px 0;">Statistical analysis methods for water quality data</p>
            <div style="margin: 20px 0;">
                <label for="method-column">Select Column:</label>
                <select id="method-column" style="margin-right: 20px;">
                    <option value="">Select column...</option>
                    {% for col in data_store.df.select_dtypes(include=['number']).columns %}
                    <option value="{{ col }}">{{ col }}</option>
                    {% endfor %}
                </select>
                
                <label for="method-type">Select Method:</label>
                <select id="method-type" style="margin-right: 20px;">
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
                
                <button onclick="applyMethod()" class="btn">🔬 Apply Method</button>
            </div>
            
            <div id="method-result" style="border: 2px solid #ddd; border-radius: 5px; padding: 20px; min-height: 200px;">
                <p style="text-align: center; color: #7f8c8d;">Select a column and method to see results</p>
            </div>
            
            <div style="margin-top: 10px; color: #7f8c8d; font-size: 12px;">
                💡 Tip: Apply statistical methods to analyze temporal patterns. Export results using the button above.
            </div>
        </div>
        
        <div id="info-tab" class="tab-content">
            <h3>File Information</h3>
            <ul>
                <li><strong>Filename:</strong> {{ data_store.filename }}</li>
                <li><strong>Shape:</strong> {{ data_store.df.shape[0] }} rows × {{ data_store.df.shape[1] }} columns</li>
                <li><strong>Columns:</strong> {{ data_store.df.columns.tolist()|join(', ') }}</li>
                <li><strong>Data types:</strong></li>
                <ul>
                    {% for col, dtype in data_store.df.dtypes.items() %}
                    <li>{{ col }}: {{ dtype }}</li>
                    {% endfor %}
                </ul>
            </ul>
        </div>
        
        {% endif %}
    </div>

    <script>
        // Simple tab switching
        function showTab(tabId) {
            // Hide all content
            var contents = document.querySelectorAll('.tab-content');
            contents.forEach(function(content) {
                content.classList.remove('active');
            });
            
            // Remove active from tabs
            var tabs = document.querySelectorAll('.tab');
            tabs.forEach(function(tab) {
                tab.classList.remove('active');
            });
            
            // Show selected content
            document.getElementById(tabId).classList.add('active');
            
            // Add active to clicked tab
            if (window.event && window.event.target) {
                window.event.target.classList.add('active');
            }
        }
        
        function clearData() {
            if (confirm('Close this file and clear all data?')) {
                window.location.href = '/clear';
            }
        }
        
        function updatePlot() {
            var xColumn = document.getElementById('x-column').value;
            var yColumn = document.getElementById('y-column').value;
            var showMarkers = document.getElementById('show-markers').checked;
            var showGrid = document.getElementById('show-grid').checked;
            var year = parseInt(document.getElementById('plot-year').value);
            
            if (!yColumn) {
                document.getElementById('plot-container').innerHTML = 
                    '<p style="text-align: center; color: #e74c3c; padding: 50px;">Please select a Y-axis parameter</p>';
                return;
            }
            
            if (xColumn === 'datetime' && (!year || year < 1900 || year > 2100)) {
                document.getElementById('plot-container').innerHTML = 
                    '<p style="text-align: center; color: #e74c3c; padding: 50px;">Please enter a valid year (1900-2100) for JDAY conversion</p>';
                return;
            }
            
            document.getElementById('plot-container').innerHTML = 
                '<p style="text-align: center; color: #3498db; padding: 50px;">Creating plot...</p>';
            
            fetch('/plot_data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    x_column: xColumn,
                    y_column: yColumn,
                    show_markers: showMarkers,
                    show_grid: showGrid,
                    year: year
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('plot-container').innerHTML = 
                        '<p style="text-align: center; color: #e74c3c; padding: 50px;">Error: ' + data.error + '</p>';
                } else {
                    var layout = data.layout;
                    layout.autosize = true;
                    layout.margin = {t: 50, l: 60, r: 20, b: 60};
                    
                    // Store plot data for export
                    window.currentPlotData = data.traces;
                    window.currentPlotLayout = layout;
                    
                    Plotly.newPlot('plot-container', data.traces, layout, {
                        responsive: true,
                        displayModeBar: true,
                        modeBarButtonsToRemove: ['pan2d','lasso2d'],
                        toImageButtonOptions: {
                            format: 'png',
                            filename: 'clearview_plot',
                            height: 600,
                            width: 800,
                            scale: 1
                        }
                    });
                }
            })
            .catch(error => {
                document.getElementById('plot-container').innerHTML = 
                    '<p style="text-align: center; color: #e74c3c; padding: 50px;">Error: ' + error + '</p>';
            });
        }
        
        function applyMethod() {
            var column = document.getElementById('method-column').value;
            var method = document.getElementById('method-type').value;
            
            if (!column || !method) {
                alert('Please select both a column and method');
                return;
            }
            
            document.getElementById('method-result').innerHTML = 
                '<p style="text-align: center; color: #3498db; padding: 50px;">Applying ' + method.replace('_', ' ') + ' to ' + column + '...</p>';
            
            fetch('/apply_method', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    column: column,
                    method: method
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('method-result').innerHTML = 
                        '<p style="color: #e74c3c;">Error: ' + data.error + '</p>';
                } else {
                    // Store results for export
                    window.currentMethodResults = data;
                    
                    document.getElementById('method-result').innerHTML = 
                        '<h4>Results: ' + data.method_name + ' for ' + data.column + '</h4>' +
                        '<p><strong>Original data points:</strong> ' + data.original_count + '</p>' +
                        '<p><strong>Result data points:</strong> ' + data.result_count + '</p>' +
                        '<h5>Preview (first 20 rows):</h5>' +
                        data.result_table;
                }
            })
            .catch(error => {
                document.getElementById('method-result').innerHTML = 
                    '<p style="color: #e74c3c;">Error: ' + error + '</p>';
            });
        }
        
        function exportData() {
            var format = document.getElementById('export-format').value;
            var filename = prompt('Enter filename (without extension):', 'data_export');
            if (filename) {
                window.location.href = '/export/data/' + format + '?filename=' + encodeURIComponent(filename);
            }
        }
        
        function exportStats() {
            var format = document.getElementById('stats-export-format').value;
            var filename = prompt('Enter filename (without extension):', 'stats_export');
            if (filename) {
                window.location.href = '/export/stats/' + format + '?filename=' + encodeURIComponent(filename);
            }
        }
        
        function exportPlot() {
            if (!window.currentPlotData || !window.currentPlotLayout) {
                alert('No plot available to export. Please create a plot first.');
                return;
            }
            
            var format = document.getElementById('plot-export-format').value;
            var filename = prompt('Enter filename (without extension):', 'plot_export');
            if (filename) {
                // Send plot data to server for export
                fetch('/export/plot/' + format, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        traces: window.currentPlotData,
                        layout: window.currentPlotLayout,
                        filename: filename
                    })
                })
                .then(response => {
                    if (response.ok) {
                        return response.blob();
                    } else {
                        throw new Error('Export failed');
                    }
                })
                .then(blob => {
                    // Create download link
                    var url = window.URL.createObjectURL(blob);
                    var a = document.createElement('a');
                    a.href = url;
                    a.download = filename + '.' + format;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                })
                .catch(error => {
                    alert('Export failed: ' + error.message);
                });
            }
        }
        
        function exportMethodResults() {
            if (!window.currentMethodResults) {
                alert('No method results available to export. Please apply a statistical method first.');
                return;
            }
            
            var format = document.getElementById('method-export-format').value;
            var filename = prompt('Enter filename (without extension):', 'method_results');
            if (filename) {
                window.location.href = '/export/method/' + format + '?filename=' + encodeURIComponent(filename);
            }
        }
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename:
            try:
                filename = file.filename
                df, file_info = read_file_with_validation(io.BytesIO(file.read()), filename)
                
                data_store['df'] = df
                data_store['filename'] = filename
                data_store['file_info'] = file_info
                data_store['stats'] = df.describe()
                
                flash(f"Successfully loaded {filename}: {df.shape[0]} rows × {df.shape[1]} columns")
                
            except Exception as e:
                flash(f"Error loading file: {str(e)}")
        
        return redirect(url_for('index'))
    
    return render_template_string(COMPLETE_TEMPLATE, data_store=data_store, netcdf_available=NETCDF_AVAILABLE)

@app.route('/clear')
def clear_data():
    data_store['df'] = None
    data_store['filename'] = None
    data_store['stats'] = None
    data_store['file_info'] = None
    flash("Data cleared successfully")
    return redirect(url_for('index'))

@app.route('/plot_data', methods=['POST'])
def plot_data():
    """Enhanced plotting with datetime support"""
    try:
        if data_store['df'] is None:
            return jsonify({'error': 'No data loaded'})
        
        data = request.get_json()
        x_column = data.get('x_column', '')
        y_column = data.get('y_column')
        show_markers = data.get('show_markers', True)
        show_grid = data.get('show_grid', True)
        
        if not y_column:
            return jsonify({'error': 'Y-axis column is required'})
        
        df = data_store['df']
        
        # Prepare X-axis data
        if x_column == 'datetime':
            year = data.get('year', data_store['year'])
            
            # Look for JDAY column (case insensitive)
            jday_col = None
            for col in df.columns:
                if col.upper() == 'JDAY' or col.upper() == 'DAY':
                    jday_col = col
                    break
            
            if jday_col and CEQUALW2_AVAILABLE:
                try:
                    # Convert JDAY to datetime using cequalw2
                    jday_values = df[jday_col].tolist()
                    datetime_values = day_of_year_to_datetime(year, jday_values)
                    x_data = datetime_values
                    x_label = f'DateTime (from {jday_col}, Year: {year})'
                except Exception as e:
                    # Fallback if conversion fails
                    x_data = list(range(len(df)))
                    x_label = f'Row Index (JDAY conversion failed: {str(e)})'
            elif pd.api.types.is_datetime64_any_dtype(df.index):
                x_data = df.index.tolist()
                x_label = 'DateTime (from index)'
            else:
                # Look for existing datetime columns
                datetime_cols = df.select_dtypes(include=['datetime64']).columns
                if len(datetime_cols) > 0:
                    x_data = df[datetime_cols[0]].tolist()
                    x_label = datetime_cols[0]
                else:
                    x_data = list(range(len(df)))
                    x_label = 'Row Index (No JDAY or DateTime found)'
        elif x_column and x_column in df.columns:
            x_data = df[x_column].tolist()
            x_label = x_column
        else:
            x_data = list(range(len(df)))
            x_label = 'Row Index'
        
        y_data = df[y_column].tolist()
        
        # Create trace
        trace = {
            'x': x_data,
            'y': y_data,
            'type': 'scatter',
            'mode': 'lines+markers' if show_markers else 'lines',
            'name': y_column,
            'line': {'color': '#1f77b4', 'width': 2},
            'marker': {'size': 4} if show_markers else {}
        }
        
        # Enhanced layout
        layout = {
            'title': {
                'text': f'{y_column} vs {x_label}',
                'font': {'size': 16}
            },
            'xaxis': {
                'title': x_label,
                'showgrid': show_grid,
                'gridcolor': 'lightgray'
            },
            'yaxis': {
                'title': y_column,
                'showgrid': show_grid,
                'gridcolor': 'lightgray'
            },
            'showlegend': False,
            'plot_bgcolor': 'white',
            'paper_bgcolor': 'white'
        }
        
        return jsonify({
            'traces': [trace],
            'layout': layout
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/apply_method', methods=['POST'])
def apply_method():
    """Apply statistical method to data - simplified version"""
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
        method_name = method.replace('_', ' ').title()
        
        # Apply simple statistical methods
        if method == 'daily_mean':
            # Group by day (assuming first column is date-like)
            result = series.groupby(series.index // 24).mean() if len(series) > 24 else series.rolling(window=24).mean()
        elif method == 'weekly_mean':
            result = series.groupby(series.index // 168).mean() if len(series) > 168 else series.rolling(window=168).mean()
        elif method == 'rolling_mean_7':
            result = series.rolling(window=7).mean()
        elif method == 'rolling_mean_30':
            result = series.rolling(window=30).mean()
        elif method == 'cumulative_sum':
            result = series.cumsum()
        elif method == 'cumulative_max':
            result = series.cummax()
        elif method == 'cumulative_min':
            result = series.cummin()
        else:
            # For other methods, just return basic statistics
            result = series.rolling(window=min(10, len(series))).mean()
        
        # Create result DataFrame
        result_df = pd.DataFrame({
            'Index': range(len(result)),
            column + '_' + method: result.values
        })
        
        # Store results for export
        data_store['method_results'] = result_df
        data_store['method_info'] = {
            'method_name': method_name,
            'column': column,
            'method': method
        }
        
        # Generate HTML table for display
        result_table = result_df.head(20).to_html(classes='data-table', index=False)
        
        return jsonify({
            'method_name': method_name,
            'column': column,
            'method': method,
            'original_count': len(series),
            'result_count': len(result),
            'result_table': result_table
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/export/<data_type>/<format_type>')
def export_data_endpoint(data_type, format_type):
    """Export data or stats in various formats"""
    try:
        if data_store['df'] is None:
            flash("No data loaded to export")
            return redirect(url_for('index'))
        
        filename = request.args.get('filename', 'export')
        
        # Choose data to export
        if data_type == 'data':
            df_to_export = data_store['df']
            filename_base = filename
        elif data_type == 'stats':
            df_to_export = data_store['df'].describe()
            filename_base = filename + '_stats'
        elif data_type == 'method':
            if 'method_results' not in data_store or data_store['method_results'] is None:
                flash("No method results available to export")
                return redirect(url_for('index'))
            df_to_export = data_store['method_results']
            method_info = data_store.get('method_info', {})
            filename_base = filename + f"_{method_info.get('method', 'method')}"
        else:
            flash("Invalid data type")
            return redirect(url_for('index'))
        
        # Create temporary file and export in requested format
        if format_type == 'csv':
            output = io.StringIO()
            df_to_export.to_csv(output, index=True)
            output.seek(0)
            
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'application/csv'
            response.headers['Content-Disposition'] = f'attachment; filename={filename_base}.csv'
            return response
            
        elif format_type == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_to_export.to_excel(writer, index=True, sheet_name='Data')
            output.seek(0)
            
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = f'attachment; filename={filename_base}.xlsx'
            return response
            
        elif format_type == 'sqlite':
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
                conn = sqlite3.connect(temp_file.name)
                df_to_export.to_sql('data', conn, if_exists='replace', index=True)
                conn.close()
                
                return send_file(temp_file.name, as_attachment=True, 
                               download_name=f'{filename_base}.db',
                               mimetype='application/x-sqlite3')
                               
        elif format_type == 'hdf5':
            with tempfile.NamedTemporaryFile(delete=False, suffix='.h5') as temp_file:
                df_to_export.to_hdf(temp_file.name, key='data', mode='w', format='table')
                
                return send_file(temp_file.name, as_attachment=True,
                               download_name=f'{filename_base}.h5',
                               mimetype='application/x-hdf5')
                               
        elif format_type == 'netcdf':
            if not NETCDF_AVAILABLE:
                flash("NetCDF export requires netCDF4 and xarray packages")
                return redirect(url_for('index'))
                
            with tempfile.NamedTemporaryFile(delete=False, suffix='.nc') as temp_file:
                # Convert DataFrame to xarray Dataset
                ds = xr.Dataset.from_dataframe(df_to_export)
                ds.to_netcdf(temp_file.name)
                
                return send_file(temp_file.name, as_attachment=True,
                               download_name=f'{filename_base}.nc',
                               mimetype='application/x-netcdf')
        else:
            flash("Unsupported export format")
            return redirect(url_for('index'))
            
    except Exception as e:
        flash(f"Export error: {str(e)}")
        return redirect(url_for('index'))

@app.route('/export/plot/<format_type>', methods=['POST'])
def export_plot_endpoint(format_type):
    """Export plot in various formats"""
    try:
        plot_data = request.get_json()
        traces = plot_data.get('traces', [])
        layout = plot_data.get('layout', {})
        filename = plot_data.get('filename', 'plot_export')
        
        if not traces:
            return jsonify({'error': 'No plot data provided'}), 400
        
        # Create plotly figure
        fig = go.Figure(data=traces, layout=layout)
        
        # Set figure size
        fig.update_layout(width=800, height=600)
        
        if format_type == 'png':
            img_bytes = pio.to_image(fig, format='png', engine='kaleido')
            response = make_response(img_bytes)
            response.headers['Content-Type'] = 'image/png'
            response.headers['Content-Disposition'] = f'attachment; filename={filename}.png'
            return response
            
        elif format_type == 'jpg':
            img_bytes = pio.to_image(fig, format='jpeg', engine='kaleido')
            response = make_response(img_bytes)
            response.headers['Content-Type'] = 'image/jpeg'
            response.headers['Content-Disposition'] = f'attachment; filename={filename}.jpg'
            return response
            
        elif format_type == 'svg':
            svg_string = pio.to_image(fig, format='svg', engine='kaleido')
            response = make_response(svg_string)
            response.headers['Content-Type'] = 'image/svg+xml'
            response.headers['Content-Disposition'] = f'attachment; filename={filename}.svg'
            return response
            
        elif format_type == 'pdf':
            pdf_bytes = pio.to_image(fig, format='pdf', engine='kaleido')
            response = make_response(pdf_bytes)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename={filename}.pdf'
            return response
            
        elif format_type == 'html':
            html_string = pio.to_html(fig, include_plotlyjs='cdn', div_id=f'plot-{filename}')
            response = make_response(html_string)
            response.headers['Content-Type'] = 'text/html'
            response.headers['Content-Disposition'] = f'attachment; filename={filename}.html'
            return response
            
        else:
            return jsonify({'error': 'Unsupported plot export format'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Plot export failed: {str(e)}'}), 500

if __name__ == '__main__':
    print("🌊 Starting ClearView Complete Data Viewer...")
    print("🌐 Open browser to: http://localhost:8080")
    app.run(host='0.0.0.0', port=8080, debug=True)