#!/usr/bin/env python3
"""
Super simple debug version to isolate tab issue
"""

from flask import Flask, render_template_string, request, redirect, url_for
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = 'debug-key'

data_store = {'df': None, 'filename': None}

DEBUG_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ClearView Debug</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .tab { background: gold; color: black; padding: 10px; margin: 5px; cursor: pointer; display: inline-block; }
        .tab.active { background: blue; color: white; }
        .content { border: 1px solid #ccc; padding: 20px; margin: 10px 0; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <h1>ClearView Debug - Tab Test</h1>
    
    {% if data_store.df is none %}
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="file" accept=".csv" required>
        <button type="submit">Load File</button>
    </form>
    {% else %}
    
    <p>File: {{ data_store.filename }} | Shape: {{ data_store.df.shape }}</p>
    
    <div id="tabs">
        <button class="tab active" onclick="showContent('data')">Data</button>
        <button class="tab" onclick="showContent('stats')">Stats</button>
        <button class="tab" onclick="showContent('info')">Info</button>
    </div>
    
    <div id="data" class="content">
        <h2>Data</h2>
        <p>First 5 rows:</p>
        {{ data_store.df.head(5).to_html()|safe }}
    </div>
    
    <div id="stats" class="content hidden">
        <h2>Statistics</h2>
        {{ data_store.df.describe().to_html()|safe }}
    </div>
    
    <div id="info" class="content hidden">
        <h2>Info</h2>
        <p>Columns: {{ data_store.df.columns.tolist() }}</p>
        <p>Data types: {{ data_store.df.dtypes.to_dict() }}</p>
    </div>
    
    <br><a href="/">Reset</a>
    
    {% endif %}

    <script>
        function showContent(tabId) {
            console.log('showContent called with:', tabId);
            
            // Hide all content divs
            var contents = document.querySelectorAll('.content');
            contents.forEach(function(content) {
                content.classList.add('hidden');
            });
            
            // Remove active from all tabs
            var tabs = document.querySelectorAll('.tab');
            tabs.forEach(function(tab) {
                tab.classList.remove('active');
            });
            
            // Show selected content
            var target = document.getElementById(tabId);
            if (target) {
                target.classList.remove('hidden');
                console.log('Showed:', tabId);
            } else {
                console.error('Target not found:', tabId);
            }
            
            // Add active to clicked tab
            event.target.classList.add('active');
            
            console.log('showContent completed');
        }
        
        console.log('Debug script loaded');
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.csv'):
            try:
                df = pd.read_csv(io.BytesIO(file.read()))
                data_store['df'] = df
                data_store['filename'] = file.filename
                print(f"Loaded: {file.filename}, shape: {df.shape}")
            except Exception as e:
                print(f"Error: {e}")
        return redirect(url_for('index'))
    
    if request.args.get('reset'):
        data_store['df'] = None
        data_store['filename'] = None
        return redirect(url_for('index'))
    
    return render_template_string(DEBUG_TEMPLATE, data_store=data_store)

if __name__ == '__main__':
    print("🔧 Debug ClearView at http://localhost:7777")
    app.run(host='127.0.0.1', port=7777, debug=True)