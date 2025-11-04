#!/bin/bash

echo "🚀 Starting Rasa on Railway (With Cohere!)..."
echo "Port: $PORT"

# Use the NEW trained model with 85.5% accuracy
echo "Using trained model (85.5% accuracy - with Cohere support)..."
if [ -f "models/expobeton-railway.tar.gz" ]; then
    echo "✅ Model ready"
else
    echo "❌ Model not found!"
    exit 1
fi

# Start action server on port 5055 in background
echo "Starting action server on port 5055..."
rasa run actions --port 5055 &

# Wait for action server to start
sleep 5

# Start Rasa on port 5005 in background
echo "Starting Rasa on port 5005..."
rasa run --enable-api --cors "*" --port 5005 -i 0.0.0.0 --model models/expobeton-railway.tar.gz &

# Wait for Rasa to start
sleep 20

# Start static server on Railway port (serves web interface + proxies to Rasa)
echo "Starting web interface on port $PORT..."
python static_server.py
