#!/bin/bash

echo "🚀 Starting Rasa on Railway (Simple Config)..."
echo "Port: $PORT"

# Use existing fallback model (don't train to save memory)
echo "Using pre-trained model..."
if [ -f "models/expobeton-fallback.tar.gz" ]; then
    cp models/expobeton-fallback.tar.gz models/expobeton-railway.tar.gz
    echo "✅ Using fallback model"
elif [ ! -f "models/expobeton-railway.tar.gz" ]; then
    echo "⚠️ No model found, training minimal model..."
    rasa train --config config_simple.yml --fixed-model-name expobeton-railway --out models/
fi

if [ ! -f "models/expobeton-railway.tar.gz" ]; then
    echo "❌ No model available!"
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
