#!/usr/bin/env python3
"""
Minimal Flask app test
"""

from flask import Flask, render_template_string

app = Flask(__name__)

SIMPLE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Flask App</title>
</head>
<body>
    <h1>Flask App is Working!</h1>
    <p>If you can see this, Flask is serving correctly.</p>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(SIMPLE_TEMPLATE)

if __name__ == '__main__':
    print("🧪 Starting Simple Test App...")
    print("🌐 Open browser to: http://localhost:9998")
    app.run(host='127.0.0.1', port=9998, debug=False)