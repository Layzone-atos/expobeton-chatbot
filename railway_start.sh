#!/bin/bash

echo "🚀 Starting Rasa on Railway (Working Model!)..."
echo "Port: $PORT"

# Use the WORKING model from commit 022803e
echo "Using working model (27KB - the one that worked!)..."
if [ -f "models/expobeton-railway.tar.gz" ]; then
    echo "✅ Model ready"
else
    echo "❌ Model not found!"
    exit 1
fi

# Start Rasa on port 5005 in background
echo "Starting Rasa on port 5005..."
rasa run --enable-api --cors "*" --port 5005 -i 0.0.0.0 --model models/expobeton-railway.tar.gz &

# Wait for Rasa to start
sleep 10

# Start static server on Railway port (serves web interface + proxies to Rasa)
echo "Starting web interface on port $PORT..."
python static_server.py
