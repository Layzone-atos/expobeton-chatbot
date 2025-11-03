#!/bin/bash

echo "🚀 Starting Rasa on Railway (Simple Config)..."
echo "Port: $PORT"

# Train with minimal config - Railway has enough RAM for this
echo "Training minimal model for demo..."
rasa train --config config_minimal.yml --fixed-model-name expobeton-railway --out models/ 2>&1 | tail -20

if [ ! -f "models/expobeton-railway.tar.gz" ]; then
    echo "⚠️ Training failed, using fallback model..."
    if [ -f "models/expobeton-fallback.tar.gz" ]; then
        cp models/expobeton-fallback.tar.gz models/expobeton-railway.tar.gz
        echo "✅ Fallback model copied"
    else
        echo "❌ No model available!"
        exit 1
    fi
else
    echo "✅ Training completed successfully!"
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
