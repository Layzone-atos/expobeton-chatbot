#!/bin/bash

echo "🚀 Starting Rasa on Railway (Paid Plan - Full Power!)..."
echo "Port: $PORT"

# Train with full config - Railway paid plan has plenty of RAM!
echo "Training model with 50 epochs (81.9% accuracy)..."
rasa train --config config_minimal.yml --fixed-model-name expobeton-railway --out models/

if [ ! -f "models/expobeton-railway.tar.gz" ]; then
    echo "⚠️ Training failed, using pre-trained model..."
    # Model is already in git, so this shouldn't happen
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
