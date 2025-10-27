"""
Flask API pour exposer le chatbot Rasa sur PythonAnywhere
Ce fichier permet d'héberger le backend Rasa sur un hébergement gratuit
"""

import os
import sys
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS

# Ajouter le projet au path
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Charger les variables d'environnement
from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

# Import Rasa
from rasa.core.agent import Agent
from rasa.core.channels.channel import UserMessage, OutputChannel
from rasa.core.tracker_store import InMemoryTrackerStore

app = Flask(__name__)
CORS(app)  # Permettre les requêtes cross-origin

# Charger l'agent Rasa
model_path = os.path.join(project_home, "models", "expobeton-french.tar.gz")
agent = None

def load_rasa_agent():
    """Charger l'agent Rasa au démarrage"""
    global agent
    print(f"Loading Rasa model from: {model_path}")
    
    # Utiliser asyncio pour charger l'agent
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    agent = loop.run_until_complete(Agent.load(model_path))
    print("Rasa agent loaded successfully!")

# Charger l'agent au démarrage
try:
    load_rasa_agent()
except Exception as e:
    print(f"Error loading Rasa agent: {e}")
    agent = None


class SimpleOutputChannel(OutputChannel):
    """Canal de sortie simple pour collecter les réponses"""
    
    def __init__(self):
        self.messages = []
    
    async def send_text_message(self, recipient_id, text, **kwargs):
        self.messages.append({"recipient_id": recipient_id, "text": text})
    
    async def send_image_url(self, recipient_id, image, **kwargs):
        self.messages.append({"recipient_id": recipient_id, "image": image})
    
    async def send_attachment(self, recipient_id, attachment, **kwargs):
        self.messages.append({"recipient_id": recipient_id, "attachment": attachment})
    
    async def send_text_with_buttons(self, recipient_id, text, buttons, **kwargs):
        self.messages.append({
            "recipient_id": recipient_id,
            "text": text,
            "buttons": buttons
        })
    
    async def send_custom_json(self, recipient_id, json_message, **kwargs):
        self.messages.append({"recipient_id": recipient_id, "custom": json_message})


@app.route('/', methods=['GET'])
def index():
    """Page d'accueil de l'API"""
    return jsonify({
        "status": "online",
        "service": "ExpoBeton RDC Chatbot API",
        "version": "1.0.0",
        "agent_loaded": agent is not None,
        "endpoints": {
            "webhook": "/webhooks/rest/webhook",
            "health": "/health"
        }
    })


@app.route('/health', methods=['GET'])
def health():
    """Endpoint de santé"""
    return jsonify({
        "status": "healthy" if agent else "unhealthy",
        "agent_loaded": agent is not None
    })


@app.route('/webhooks/rest/webhook', methods=['POST', 'OPTIONS'])
def webhook():
    """Endpoint principal pour recevoir les messages du chatbot"""
    
    # Gérer les requêtes OPTIONS (CORS preflight)
    if request.method == 'OPTIONS':
        return '', 204
    
    # Vérifier que l'agent est chargé
    if not agent:
        return jsonify({
            "error": "Rasa agent not loaded. Please check server logs."
        }), 500
    
    try:
        # Récupérer les données de la requête
        data = request.json
        sender_id = data.get('sender', 'default_user')
        message_text = data.get('message', '')
        metadata = data.get('metadata', {})
        
        print(f"Received message from {sender_id}: {message_text}")
        
        # Créer un canal de sortie pour collecter les réponses
        output_channel = SimpleOutputChannel()
        
        # Créer le message utilisateur
        user_message = UserMessage(
            text=message_text,
            output_channel=output_channel,
            sender_id=sender_id,
            metadata=metadata
        )
        
        # Traiter le message avec Rasa (asynchrone)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(agent.handle_message(user_message))
        
        # Formater les réponses pour le format attendu par le frontend
        responses = []
        for msg in output_channel.messages:
            response = {"recipient_id": msg.get("recipient_id", sender_id)}
            
            if "text" in msg:
                response["text"] = msg["text"]
            if "image" in msg:
                response["image"] = msg["image"]
            if "buttons" in msg:
                response["buttons"] = msg["buttons"]
            if "custom" in msg:
                response["custom"] = msg["custom"]
            
            responses.append(response)
        
        print(f"Sending {len(responses)} responses")
        return jsonify(responses)
    
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "error": f"Error processing message: {str(e)}"
        }), 500


@app.route('/reload', methods=['POST'])
def reload_agent():
    """Endpoint pour recharger l'agent (utile pour les mises à jour)"""
    try:
        load_rasa_agent()
        return jsonify({"status": "success", "message": "Agent reloaded successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    # En développement local
    app.run(host='0.0.0.0', port=5000, debug=True)
