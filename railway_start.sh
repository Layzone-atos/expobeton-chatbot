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
ACTION_SERVER_PID=$!

# Give action server time to start
sleep 5

# Check if action server is running
if kill -0 $ACTION_SERVER_PID 2>/dev/null; then
    echo "✅ Action server is running (PID: $ACTION_SERVER_PID)"
else
    echo "❌ Action server failed to start"
    exit 1
fi

# Start Rasa server on port 5005 in the background
echo "Starting Rasa server on port 5005..."
rasa run --enable-api --cors "*" --port 5005 --debug -i 0.0.0.0 --model models/expobeton-railway.tar.gz &
RASA_SERVER_PID=$!

# Give Rasa server time to start
sleep 10

# Check if Rasa server is running
if kill -0 $RASA_SERVER_PID 2>/dev/null; then
    echo "✅ Rasa server is running (PID: $RASA_SERVER_PID)"
else
    echo "❌ Rasa server failed to start"
    exit 1
fi

# Start static file server on Railway's port
echo "Starting static file server on port $PORT..."
python static_server.py