#!/bin/bash

echo "🚀 Starting Rasa on Railway..."
echo "Port: $PORT"

# Train model if it doesn't exist
if [ ! -f "models/expobeton-railway.tar.gz" ]; then
    echo "Training model..."
    rasa train --config config_simple.yml --fixed-model-name expobeton-railway --out models/
    
    # Check if model was created
    if [ ! -f "models/expobeton-railway.tar.gz" ]; then
        echo "❌ Error: Model was not created!"
        ls -la models/
        exit 1
    fi
fi

echo "✅ Model is ready"

# Start Rasa action server on port 5055 in the background
echo "Starting Rasa action server on port 5055..."
rasa run actions --port 5055 --debug &

# Start Rasa server on port 5005 in the background
echo "Starting Rasa server on port 5005..."
rasa run --enable-api --cors "*" --port 5005 --debug -i 0.0.0.0 --model models/expobeton-railway.tar.gz &

# Give servers time to start
sleep 15

# Start static file server on Railway's port
echo "Starting static file server on port $PORT..."
python static_server.py