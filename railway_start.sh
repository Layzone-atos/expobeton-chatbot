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

# Start Rasa directly on Railway port (no action server, no proxy)
echo "Starting Rasa on port $PORT..."
rasa run --enable-api --cors "*" --port ${PORT:-5005} -i 0.0.0.0 --model models/expobeton-railway.tar.gz
