#!/usr/bin/env python3
"""
Simple server to serve static files and forward API requests to Rasa server
"""

import os
import sys
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Get port from environment variable
PORT = int(os.environ.get('PORT', 5005))

class StaticFileHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # Serve static files for web interface
        if self.path == '/' or self.path == '/index.html':
            self.path = '/web/index.html'
        elif self.path.startswith('/web/'):
            # Already in correct format
            pass
        elif self.path.startswith('/chat-widget'):
            # Serve chat widget files
            pass
        elif self.path == '/chat-widget.css':
            self.path = '/web/chat-widget.css'
        elif self.path == '/chat-widget.js':
            self.path = '/web/chat-widget.js'
        elif self.path == '/chat-widget-standalone.js':
            self.path = '/web/chat-widget-standalone.js'
        else:
            # For other paths, check if it's a static file
            if '.' in self.path.split('/')[-1]:
                # Has file extension, try to serve as static file
                pass
            else:
                # No file extension, serve index.html (for SPA routing)
                self.path = '/web/index.html'
        
        # Set the correct working directory
        original_cwd = os.getcwd()
        try:
            os.chdir(os.path.dirname(os.path.abspath(__file__)))
            return SimpleHTTPRequestHandler.do_GET(self)
        finally:
            os.chdir(original_cwd)
    
    def do_POST(self):
        # Forward webhook requests to Rasa server
        if self.path.startswith('/webhooks/'):
            try:
                # Read the request data
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                # Forward to Rasa server (assuming it's running on port 5005)
                rasa_url = f'http://localhost:5005{self.path}'
                
                # Create the request
                req = urllib.request.Request(
                    rasa_url,
                    data=post_data,
                    headers={
                        'Content-Type': self.headers['Content-Type'],
                        'Content-Length': str(len(post_data))
                    },
                    method='POST'
                )
                
                # Forward the request to Rasa server
                with urllib.request.urlopen(req) as response:
                    response_data = response.read()
                    self.send_response(response.getcode())
                    # Forward all headers from Rasa response
                    for header_name, header_value in response.headers.items():
                        self.send_header(header_name, header_value)
                    self.end_headers()
                    self.wfile.write(response_data)
                    
            except urllib.error.HTTPError as e:
                # Handle HTTP errors from Rasa server
                print(f"HTTP Error from Rasa server: {e.code} - {e.reason}")
                self.send_response(e.code)
                # Forward headers if available
                for header_name, header_value in e.headers.items():
                    self.send_header(header_name, header_value)
                self.end_headers()
                if e.fp:
                    self.wfile.write(e.fp.read())
                    
            except urllib.error.URLError as e:
                # Handle URL errors (connection issues)
                print(f"URL Error connecting to Rasa server: {e.reason}")
                self.send_response(503)  # Service Unavailable
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {
                    "error": "Service Unavailable",
                    "message": "Unable to connect to Rasa server. Please check that the server is running."
                }
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
                
            except Exception as e:
                # Handle other errors
                print(f"Unexpected error: {e}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {
                    "error": "Internal Server Error",
                    "message": str(e)
                }
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
        else:
            # Handle other POST requests by sending a 404
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def start_server():
    # Change to the project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Start the HTTP server
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, StaticFileHandler)
    print(f"Starting static file server on port {PORT}")
    print(f"Access the chat interface at: http://localhost:{PORT}/")
    httpd.serve_forever()

if __name__ == '__main__':
    try:
        start_server()
    except KeyboardInterrupt:
        print("\nShutting down server...")