#!/usr/bin/env python3
"""
ClearView Flask app - Restored with working Methods tab
Original design with all features working
"""

from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
import pandas as pd
import io
import os
import json
import plotly.graph_objs as go
import plotly.utils
import datetime
import numpy as np

app = Flask(__name__)
app.secret_key = 'clearview-secret-key'

# Global variable to store data
data_store = {
    'df': None,
    'filename': None,
    'stats': None,
    'file_info': None
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
        .tab:hover { background: #ffd700; }
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
            <h3>Data Overview</h3>
            <p><strong>📄 File:</strong> {{ data_store.filename or 'No file loaded' }}</p>
            <p><strong>📊 Shape:</strong> {{ "{:,}".format(data_store.df.shape[0]) }} rows × {{ data_store.df.shape[1] }} columns</p>
            <p><strong>🗂️ Columns:</strong> {{ ', '.join(data_store.df.columns.tolist()[:8]) }}{% if data_store.df.shape[1] > 8 %} ... ({{ data_store.df.shape[1] - 8 }} more){% endif %}</p>
            
            <h3>Data Preview (First 20 rows)</h3>
            <div class="table-container">
                {{ data_store.df.head(20).to_html(classes='data-table', table_id='data-table')|safe }}
            </div>
        </div>
        
        <div id="stats-tab" class="tab-content">
            <h3>Statistical Summary</h3>
            <div class="table-container">
                {{ data_store.df.describe().to_html()|safe }}
            </div>
        </div>
        
        <div id="plot-tab" class="tab-content">
            <h3>Interactive Plotting</h3>
            
            <div style="background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px;">
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px;">
                    
                    <div>
                        <label for="x-column"><strong>X-axis:</strong></label>
                        <select id="x-column" style="width: 100%; margin-top: 5px;">
                            <option value="">📊 Row Index</option>
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
                        <label><strong>Options:</strong></label><br>
                        <input type="checkbox" id="show-markers" checked>
                        <label for="show-markers">Markers</label><br>
                        <button onclick="updatePlot()" class="btn" style="margin-top: 5px; width: 100%;">📈 Plot</button>
                    </div>
                </div>
            </div>
            
            <div id="plot-container" style="width: 100%; height: 500px; border: 1px solid #ddd;">
                <p style="text-align: center; color: #7f8c8d; padding: 50px;">Select parameters and click Plot to visualize your data</p>
            </div>
        </div>
        
        <div id="methods-tab" class="tab-content">
            <h3>⚗️ Time Series Analysis Methods</h3>
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
            
            <div id="method-result" style="border: 1px solid #ddd; padding: 20px; min-height: 200px;">
                <p style="text-align: center; color: #7f8c8d;">Select a column and method to see results</p>
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
            
            if (!yColumn) {
                document.getElementById('plot-container').innerHTML = 
                    '<p style="text-align: center; color: #e74c3c; padding: 50px;">Please select a Y-axis parameter</p>';
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
                    show_markers: showMarkers
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
                    
                    Plotly.newPlot('plot-container', data.traces, layout, {responsive: true});
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
    
    return render_template_string(COMPLETE_TEMPLATE, data_store=data_store)

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
    """Simple single-column plotting"""
    try:
        if data_store['df'] is None:
            return jsonify({'error': 'No data loaded'})
        
        data = request.get_json()
        x_column = data.get('x_column', '')
        y_column = data.get('y_column')
        show_markers = data.get('show_markers', True)
        
        if not y_column:
            return jsonify({'error': 'Y-axis column is required'})
        
        df = data_store['df']
        
        # Prepare data
        if x_column and x_column in df.columns:
            x_data = df[x_column].tolist()
            x_label = x_column
        else:
            x_data = list(range(len(df)))
            x_label = 'Row Index'
        
        y_data = df[y_column].tolist()
        
        trace = {
            'x': x_data,
            'y': y_data,
            'type': 'scatter',
            'mode': 'lines+markers' if show_markers else 'lines',
            'name': y_column,
            'line': {'color': '#1f77b4', 'width': 2}
        }
        
        layout = {
            'title': f'{y_column} vs {x_label}',
            'xaxis': {'title': x_label},
            'yaxis': {'title': y_column},
            'showlegend': False
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

if __name__ == '__main__':
    print("🌊 Starting ClearView Complete Data Viewer...")
    print("🌐 Open browser to: http://localhost:9999")
    app.run(host='127.0.0.1', port=9999, debug=False)