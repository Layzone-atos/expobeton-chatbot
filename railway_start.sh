#!/bin/bash

echo "🚀 Starting Rasa on Railway (Simple Config)..."
echo "Port: $PORT"

# Train a fresh minimal model
echo "Training minimal model..."
rasa train --config config_simple.yml --fixed-model-name expobeton-railway --out models/

if [ ! -f "models/expobeton-railway.tar.gz" ]; then
    echo "❌ Model training failed!"
    exit 1
fi

echo "✅ Model ready"

# Start Rasa on port 5005 in background
echo "Starting Rasa on port 5005..."
rasa run --enable-api --cors "*" --port 5005 -i 0.0.0.0 --model models/expobeton-railway.tar.gz &

# Wait for Rasa to start
sleep 10

# Start static server on Railway port (serves web interface + proxies to Rasa)
echo "Starting web interface on port $PORT..."
python static_server.py
