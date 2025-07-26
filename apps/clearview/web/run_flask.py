import sys
import os
sys.path.insert(0, '/Users/todd/GitHub/ecohydrology/CE-QUAL-W2-python/src')

from flask_viewer import app

print("Starting ClearView Flask app directly...")
print("URL: http://localhost:8888")

try:
    from werkzeug.serving import run_simple
    run_simple('localhost', 8888, app, use_reloader=False, use_debugger=True)
except Exception as e:
    print(f"Error: {e}")
    app.run(host='localhost', port=8888, debug=True)