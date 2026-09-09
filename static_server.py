#!/usr/bin/env python3
"""
Simple server to serve static files and forward API requests to Rasa server
"""

import os
import sys
import json
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

# Get port from environment variable
PORT = int(os.environ.get('PORT', 5005))

# Delai (secondes) laisse a Rasa pour repondre. Sans lui, urlopen() attendait
# indefiniment : comme le serveur etait mono-thread, UNE requete lente gelait
# alors TOUT le chatbot pour tous les visiteurs, sans jamais se liberer.
# Mesure en production : ~25 % des requetes n'aboutissaient pas dans les 30 s.
RASA_PROXY_TIMEOUT = 60

# Racine des fichiers statiques. Fixee UNE fois au demarrage au lieu d'etre
# changee a chaque requete : os.chdir() est global au processus, pas au thread.
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


# ThreadingHTTPServer (au lieu de HTTPServer) traite chaque requete dans son
# propre thread. C'est aussi lui qui fixe daemon_threads = True, donc les
# requetes en cours n'empechent pas l'arret du conteneur quand Railway envoie
# SIGTERM. HTTPServer etait mono-thread : une seule requete lente mettait en
# attente toutes les suivantes, y compris celles des autres visiteurs.
class StaticFileHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # directory= est le pendant thread-safe du chdir par requete : chaque
        # instance connait sa racine sans toucher a l'etat global du processus.
        # Sans lui, deux GET simultanés auraient pu lire le fichier d'un autre
        # repertoire, ou tomber sur un chdir deja restaure.
        kwargs['directory'] = PROJECT_DIR
        super().__init__(*args, **kwargs)

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
        
        # La racine statique est deja fixee par __init__ (directory=PROJECT_DIR) :
        # plus besoin de chdir ici. L'ancien try/os.chdir/finally etait sans effet
        # tant que le serveur etait mono-thread (start_server() a deja fait le
        # meme chdir au demarrage), mais il serait devenu une course entre threads
        # avec ThreadingHTTPServer, puisque os.chdir() modifie tout le processus.
        return SimpleHTTPRequestHandler.do_GET(self)
    
    def do_POST(self):
        # Forward webhook requests to Rasa server
        if self.path.startswith('/webhooks/'):
            try:
                # Read the request data
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                # Inject client IP into metadata so the action server can use it
                try:
                    data = json.loads(post_data)
                    if 'metadata' not in data or data['metadata'] is None:
                        data['metadata'] = {}
                    data['metadata']['client_ip'] = self.client_address[0]
                    # Also check X-Forwarded-For for proxied requests (Railway)
                    forwarded_for = self.headers.get('X-Forwarded-For', '')
                    if forwarded_for:
                        data['metadata']['client_ip'] = forwarded_for.split(',')[0].strip()
                    post_data = json.dumps(data).encode('utf-8')
                except (json.JSONDecodeError, TypeError):
                    pass  # If not JSON, forward as-is
                
                # Forward to Rasa server (assuming it's running on port 5005)
                rasa_url = f'http://localhost:5005{self.path}'
                
                # Create the request
                req = urllib.request.Request(
                    rasa_url,
                    data=post_data,
                    headers={
                        'Content-Type': self.headers.get('Content-Type', 'application/json'),
                        'Content-Length': str(len(post_data))
                    },
                    method='POST'
                )
                
                # Forward the request to Rasa server.
                # Le timeout est indispensable : sans lui, un Rasa muet bloquait
                # ce thread pour toujours. Avec ThreadingHTTPServer les autres
                # visiteurs ne sont plus affectes, et celui-ci recoit un 504
                # explicite au lieu d'attendre indefiniment.
                with urllib.request.urlopen(req, timeout=RASA_PROXY_TIMEOUT) as response:
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
                # Le corps est serialize AVANT d'ecrire les en-tetes, afin de
                # pouvoir annoncer Content-Length : sinon le client attend la
                # fermeture du socket pour connaitre la fin du corps.
                print(f"URL Error connecting to Rasa server: {e.reason}")
                error_response = json.dumps({
                    "error": "Service Unavailable",
                    "message": "Unable to connect to Rasa server. Please check that the server is running."
                }).encode('utf-8')
                self.send_response(503)  # Service Unavailable
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(error_response)))
                self.end_headers()
                self.wfile.write(error_response)
                
            except TimeoutError as e:
                # Un delai de lecture leve TimeoutError (et non URLError) : sans
                # cette branche il tombait dans le « except Exception » et
                # renvoyait 500, ce qui laissait croire a un bug du proxy alors
                # que c'est Rasa qui n'a pas repondu a temps. 504 est le code
                # exact pour une passerelle dont l'amont ne repond pas.
                # TimeoutError seulement : un OSError plus large avalerait les
                # BrokenPipeError (client deja parti), pour lesquels ecrire une
                # reponse n'a aucun sens.
                print(f"Rasa server timed out after {RASA_PROXY_TIMEOUT}s: {e}")
                self.send_response(504)
                self.send_header('Content-Type', 'application/json')
                error_response = json.dumps({
                    "error": "Gateway Timeout",
                    "message": "The chatbot engine did not answer in time. Please try again."
                }).encode('utf-8')
                self.send_header('Content-Length', str(len(error_response)))
                self.end_headers()
                self.wfile.write(error_response)

            except Exception as e:
                # Handle other errors.
                # Le detail de l'exception part dans les journaux du conteneur,
                # PAS dans la reponse : ce serveur est le point d'entree public,
                # et str(e) peut reveler des chemins internes, des noms d'hotes ou
                # des extraits de configuration. Un attaquant n'a pas a les lire.
                print(f"Unexpected error: {type(e).__name__}: {e}")
                error_response = json.dumps({
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred. Please try again."
                }).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(error_response)))
                self.end_headers()
                self.wfile.write(error_response)
        else:
            # Handle other POST requests by sending a 404
            # Content-Length obligatoire : sans lui le client ne sait pas ou
            # s'arrete le corps et attend la fermeture du socket. Constate sur
            # POST /model/parse, ou la lecture du corps d'un 404 a bloque 60 s.
            body_404 = b'Not Found'
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', str(len(body_404)))
            self.end_headers()
            self.wfile.write(body_404)

    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def start_server():
    # Change to the project directory
    os.chdir(PROJECT_DIR)
    
    # Start the HTTP server
    server_address = ('', PORT)
    httpd = ThreadingHTTPServer(server_address, StaticFileHandler)
    print(f"Starting static file server on port {PORT}")
    print(f"Access the chat interface at: http://localhost:{PORT}/")
    httpd.serve_forever()

if __name__ == '__main__':
    try:
        start_server()
    except KeyboardInterrupt:
        print("\nShutting down server...")