#!/bin/bash

echo "🚀 Starting Rasa on Railway (Simple Config)..."
echo "Port: $PORT"

# DON'T train - just use fallback model to save memory
echo "Using pre-trained fallback model..."
if [ -f "models/expobeton-fallback.tar.gz" ]; then
    cp models/expobeton-fallback.tar.gz models/expobeton-railway.tar.gz
    echo "✅ Model copied"
else
    echo "❌ No fallback model found!"
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
