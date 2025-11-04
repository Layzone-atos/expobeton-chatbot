#!/bin/bash

echo "🚀 Starting Rasa on Railway (Paid Plan)..."
echo "Port: $PORT"

# Use lightweight fallback model for stability
echo "Using fallback model..."
if [ -f "models/expobeton-fallback.tar.gz" ]; then
    cp models/expobeton-fallback.tar.gz models/expobeton-railway.tar.gz
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
