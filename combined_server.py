#!/usr/bin/env python3
"""
Simple server to serve both Rasa API and static web files
"""

import os
import sys
import json
import subprocess
import threading
import time
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Get port from environment variable
PORT = int(os.environ.get('PORT', 5005))

class CombinedHandler(SimpleHTTPRequestHandler):
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
                rasa_port = 5005
                if PORT == 5005:
                    rasa_port = 5006  # Use a different port if Railway assigned 5005
                
                rasa_url = f'http://localhost:{rasa_port}{self.path}'
                
                req = urllib.request.Request(
                    rasa_url,
                    data=post_data,
                    headers={
                        'Content-Type': self.headers['Content-Type'],
                        'Content-Length': str(len(post_data))
                    },
                    method='POST'
                )
                
                with urllib.request.urlopen(req) as response:
                    response_data = response.read()
                    self.send_response(response.getcode())
                    # Forward all headers from Rasa response
                    for header_name, header_value in response.headers.items():
                        self.send_header(header_name, header_value)
                    self.end_headers()
                    self.wfile.write(response_data)
                    
            except Exception as e:
                # Error response
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {"error": str(e)}
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
    httpd = HTTPServer(server_address, CombinedHandler)
    print(f"Starting combined server on port {PORT}")
    print(f"Access the chat interface at: http://localhost:{PORT}/")
    httpd.serve_forever()

if __name__ == '__main__':
    try:
        start_server()
    except KeyboardInterrupt:
        print("\nShutting down server...")