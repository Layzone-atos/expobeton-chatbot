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
ls -la models/

# Start Rasa action server on port 5055 in the background
echo "Starting Rasa action server on port 5055..."
rasa run actions --port 5055 &
ACTION_SERVER_PID=$!

# Give action server time to start
sleep 5

echo "✅ Action server started (PID: $ACTION_SERVER_PID)"

# Start Rasa server on Railway's port
echo "Starting Rasa server on port $PORT..."
rasa run --enable-api --cors "*" --port ${PORT:-5005} -i 0.0.0.0 --model models/expobeton-railway.tar.gz