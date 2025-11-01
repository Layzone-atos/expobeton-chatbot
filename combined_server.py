#!/usr/bin/env python3
"""
Simple server to serve both Rasa API and static web files
"""

import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import threading
import time

# Get port from environment variable
PORT = int(os.environ.get('PORT', 5005))

class RasaWebHandler(SimpleHTTPRequestHandler):
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
        # Handle Rasa webhook requests by forwarding to the Rasa server
        # For now, we'll just return a simple response
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # Parse the JSON data
        try:
            data = json.loads(post_data.decode('utf-8'))
            message = data.get('message', '')
            sender = data.get('sender', 'user')
            
            # Simple response - in a real implementation, this would call the Rasa server
            response_data = [
                {
                    "recipient_id": sender,
                    "text": f"Je suis l'assistant ExpoBeton. Vous avez dit: {message}"
                }
            ]
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        except Exception as e:
            # Error response
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {"error": str(e)}
            self.wfile.write(json.dumps(error_response).encode('utf-8'))

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
    httpd = HTTPServer(server_address, RasaWebHandler)
    print(f"Starting server on port {PORT}")
    print(f"Access the chat interface at: http://localhost:{PORT}/")
    httpd.serve_forever()

if __name__ == '__main__':
    start_server()