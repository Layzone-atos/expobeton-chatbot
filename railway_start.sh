#!/bin/bash

echo "🚀 Starting Rasa on Railway (Simple Config)..."
echo "Port: $PORT"

# Always train to use latest NLU data
echo "Training minimal model..."
rasa train --config config_minimal.yml --fixed-model-name expobeton-railway --out models/

if [ ! -f "models/expobeton-railway.tar.gz" ]; then
    echo "❌ Model training failed!"
    # Try using fallback as last resort
    if [ -f "models/expobeton-fallback.tar.gz" ]; then
        cp models/expobeton-fallback.tar.gz models/expobeton-railway.tar.gz
        echo "⚠️ Using fallback model"
    else
        exit 1
    fi
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
