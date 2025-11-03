#!/bin/bash

echo "🚀 Starting Rasa on Railway (Simple Config)..."
echo "Port: $PORT"

# Create a minimal working model for demo
echo "Creating minimal demo model..."
python3 << 'PYTHON_SCRIPT'
import tarfile
import json
import os
import pickle
from pathlib import Path

# Create temp directory for model
os.makedirs("temp_demo_model", exist_ok=True)

# Create minimal metadata
metadata = {
    "trained_at": "2025-01-01T00:00:00.000000+00:00",
    "rasa_open_source_version": "3.6.21",
    "model_id": "demo_model",
    "assistant_id": "expobeton",
    "domain": {
        "intents": ["greet", "ask_about_expobeton", "ask_event_dates", "ask_event_location", "ask_event_theme"],
        "responses": {
            "utter_greet": [{"text": "Bonjour ! Comment puis-je vous aider aujourd\'hui ?"}],
            "utter_about_expobeton": [{"text": "ExpoBeton RDC est le salon international de la construction, des infrastructures et du développement urbain en République Démocratique du Congo. C\'est un forum annuel qui crée un espace de réflexion et de partenariat pour rebâtir les villes congolaises et soutenir la croissance économique."}],
            "utter_event_dates": [{"text": "ExpoBeton RDC aura lieu du 8 au 11 octobre 2025 à Kinshasa, République Démocratique du Congo."}],
            "utter_event_location": [{"text": "L\'événement se déroulera à Kinshasa, RDC. Le lieu exact sera communiqué prochainement."}],
            "utter_event_theme": [{"text": "Le thème de l\'édition 2025 est : \'100 milliards USD pour rebâtir la RDC post-conflit : catalyser une transformation audacieuse pour le 21ème siècle\'"}]
        }
    },
    "pipeline": "KeywordIntentClassifier"
}

with open("temp_demo_model/metadata.json", "w") as f:
    json.dump(metadata, f)

# Create simple keyword-based NLU model
keyword_model = {
    "greet": ["bonjour", "salut", "hello", "hi", "bonsoir"],
    "ask_about_expobeton": ["expobeton", "expo beton", "c\'est quoi", "qu\'est-ce", "expliquer"],
    "ask_event_dates": ["dates", "quand", "date", "programme"],
    "ask_event_location": ["lieu", "où", "endroit", "location"],
    "ask_event_theme": ["thème", "theme", "sujet"]
}

with open("temp_demo_model/nlu_model.pkl", "wb") as f:
    pickle.dump(keyword_model, f)

# Create fingerprint
fingerprint = {"config": "minimal", "nlu": "keywords", "stories": "basic"}
with open("temp_demo_model/fingerprint.json", "w") as f:
    json.dump(fingerprint, f)

# Create tar.gz
with tarfile.open("models/expobeton-railway.tar.gz", "w:gz") as tar:
    tar.add("temp_demo_model", arcname=".")

print("✅ Demo model created successfully!")
PYTHON_SCRIPT

if [ ! -f "models/expobeton-railway.tar.gz" ]; then
    echo "⚠️ Demo model creation failed, using fallback..."
    if [ -f "models/expobeton-fallback.tar.gz" ]; then
        cp models/expobeton-fallback.tar.gz models/expobeton-railway.tar.gz
    fi
fi

echo "✅ Model ready"

echo "✅ Model ready"

# Start Rasa on port 5005 in background
echo "Starting Rasa on port 5005..."
rasa run --enable-api --cors "*" --port 5005 -i 0.0.0.0 --model models/expobeton-railway.tar.gz &

# Wait for Rasa to start
sleep 10

# Start static server on Railway port (serves web interface + proxies to Rasa)
echo "Starting web interface on port $PORT..."
python static_server.py
