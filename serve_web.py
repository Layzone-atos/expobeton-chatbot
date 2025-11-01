#!/usr/bin/env python3

import http.server
import socketserver
import os
import sys

# Set the port (use PORT environment variable or default to 8000)
PORT = int(os.environ.get('PORT', 8000))

# Define the handler to serve static files
class StaticFileHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # If root path, serve index.html
        if self.path == '/':
            self.path = '/web/index.html'
        # If path starts with /web, serve from web directory
        elif self.path.startswith('/web/'):
            pass  # Already in correct format
        # For other paths, check if file exists in web directory
        else:
            # Check if file exists in web directory
            web_path = os.path.join('web', self.path.lstrip('/'))
            if os.path.exists(web_path) and not os.path.isdir(web_path):
                self.path = '/' + web_path
            else:
                # Serve index.html for any other path (for SPA routing)
                self.path = '/web/index.html'
        
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

# Change to the project root directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Start the server
with socketserver.TCPServer(("", PORT), StaticFileHandler) as httpd:
    print(f"Serving web interface at http://0.0.0.0:{PORT}")
    print(f"Rasa API should be running on the main Railway port")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()