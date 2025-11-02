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
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Get port from environment variable
PORT = int(os.environ.get('PORT', 5005))
RASA_PORT = 5006  # Use a fixed port for Rasa server

def start_rasa_server():
    """Start the Rasa server as a subprocess"""
    print("Starting Rasa server...")
    
    # Change to the project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Train the model if it doesn't exist
    if not os.path.exists('models/expobeton-railway.tar.gz'):
        print("Training model...")
        train_cmd = [
            'rasa', 'train',
            '--config', 'config_simple.yml',
            '--fixed-model-name', 'expobeton-railway',
            '--out', 'models/'
        ]
        train_process = subprocess.run(train_cmd, capture_output=True, text=True)
        if train_process.returncode != 0:
            print(f"Training failed: {train_process.stderr}")
            return None
    
    # Start Rasa server
    rasa_cmd = [
        'rasa', 'run',
        '--enable-api',
        '--cors', '*',
        '--port', str(RASA_PORT),
        '--debug',
        '-i', '0.0.0.0',
        '--model', 'models/expobeton-railway.tar.gz'
    ]
    
    print(f"Starting Rasa server with command: {' '.join(rasa_cmd)}")
    process = subprocess.Popen(rasa_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process

class CombinedHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Set the directory to serve files from
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)
    
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
        
        return SimpleHTTPRequestHandler.do_GET(self)
    
    def do_POST(self):
        # Forward webhook requests to Rasa server
        if self.path.startswith('/webhooks/'):
            try:
                # Read the request data
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                # Forward to Rasa server
                rasa_url = f'http://localhost:{RASA_PORT}{self.path}'
                
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
    # Start the HTTP server
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, CombinedHandler)
    print(f"Starting combined server on port {PORT}")
    print(f"Access the chat interface at: http://localhost:{PORT}/")
    httpd.serve_forever()

def main():
    # Start Rasa server in a separate thread
    rasa_process = start_rasa_server()
    if rasa_process is None:
        print("Failed to start Rasa server")
        sys.exit(1)
    
    # Give Rasa server some time to start
    print("Waiting for Rasa server to start...")
    time.sleep(10)
    
    # Start the combined server
    try:
        start_server()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        if rasa_process:
            rasa_process.terminate()
            rasa_process.wait()

if __name__ == '__main__':
    main()