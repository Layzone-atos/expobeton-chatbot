#!/bin/bash

echo "🚀 Starting Rasa on Render..."
echo "Port: $PORT"

# Use the trained model from git (81.9% accuracy)
echo "Using pre-trained model (50 epochs, 81.9% accuracy)..."
if [ -f "models/expobeton-railway.tar.gz" ]; then
    echo "✅ Model found and ready"
else
    echo "⚠️ Model not found, using fallback..."
    if [ -f "models/expobeton-fallback.tar.gz" ]; then
        cp models/expobeton-fallback.tar.gz models/expobeton-railway.tar.gz
    else
        echo "❌ No model available!"
        exit 1
    fi
fi

# Start Rasa on port 5005 in background
echo "Starting Rasa on port 5005..."
rasa run --enable-api --cors "*" --port 5005 -i 0.0.0.0 --model models/expobeton-railway.tar.gz &

# Wait for Rasa to start
sleep 15

# Start static server on Render port
echo "Starting web interface on port $PORT..."
python static_server.py
