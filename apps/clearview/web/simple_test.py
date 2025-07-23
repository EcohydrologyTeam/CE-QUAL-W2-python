#!/usr/bin/env python3
"""
Ultra-simple test server to verify connection works
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket

class TestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>ClearView Test</title></head>
        <body>
            <h1>🎉 SUCCESS!</h1>
            <p>If you can see this, the web server is working!</p>
            <p>Now we can deploy the actual data viewer.</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

if __name__ == '__main__':
    port = 8080
    print(f"🧪 Starting test server on http://localhost:{port}")
    print("📱 Open your browser to that address")
    
    try:
        server = HTTPServer(('localhost', port), TestHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Error: {e}")