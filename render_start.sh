#!/bin/bash

echo "🚀 Starting Rasa on Render..."
echo "Port: $PORT"

# Use fallback model (no training on Render free tier)
echo "Using pre-trained model..."
if [ -f "models/expobeton-fallback.tar.gz" ]; then
    cp models/expobeton-fallback.tar.gz models/expobeton-railway.tar.gz
    echo "✅ Model ready"
else
    echo "❌ No model available!"
    exit 1
fi

# Start Rasa on port 5005 in background
echo "Starting Rasa on port 5005..."
rasa run --enable-api --cors "*" --port 5005 -i 0.0.0.0 --model models/expobeton-railway.tar.gz &

# Wait for Rasa to start
sleep 15

# Start static server on Render port
echo "Starting web interface on port $PORT..."
python static_server.py
