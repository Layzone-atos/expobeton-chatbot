from flask import Flask
import os
import subprocess
import sys

app = Flask(__name__)

@app.route('/')
def home():
    return "Rasa Chatbot is running!"

@app.route('/health')
def health():
    return {"status": "healthy", "service": "rasa-chatbot"}

@app.route('/status')
def status():
    # Check if required files exist
    model_exists = os.path.exists("models/expobeton-french.tar.gz")
    actions_exist = os.path.exists("actions")
    domain_exists = os.path.exists("domain")
    
    return {
        "status": "running" if (model_exists and actions_exist and domain_exists) else "degraded",
        "service": "rasa-chatbot",
        "checks": {
            "model_file": model_exists,
            "actions_directory": actions_exist,
            "domain_directory": domain_exists
        }
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5005))
    app.run(host='0.0.0.0', port=port)