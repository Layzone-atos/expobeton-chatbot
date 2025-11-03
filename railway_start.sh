#!/bin/bash

echo "🚀 Starting Rasa on Railway..."
echo "Port: $PORT"

# Always train a fresh model with current configuration
echo "Training model with current configuration..."
rasa train --config config_simple.yml --fixed-model-name expobeton-railway --out models/

# Check if model was created
if [ ! -f "models/expobeton-railway.tar.gz" ]; then
    echo "❌ Error: Model was not created!"
    ls -la models/
    exit 1
fi

echo "✅ Model is ready"
ls -la models/

# NOTE: Action server disabled to save memory on Railway
# Re-enable only if using custom actions (action_answer_expobeton, etc.)
# echo "Starting Rasa action server on port 5055..."
# rasa run actions --port 5055 &
# ACTION_SERVER_PID=$!
# sleep 5
# echo "✅ Action server started (PID: $ACTION_SERVER_PID)"

# Start Rasa server on port 5005 in background
echo "Starting Rasa server on port 5005..."
rasa run --enable-api --cors "*" --port 5005 -i 0.0.0.0 --model models/expobeton-railway.tar.gz &

# Wait for Rasa to be ready
echo "Waiting for Rasa server to start..."
sleep 15

echo "✅ Rasa server should be ready"

# Start static file server on Railway's port (serves web interface + proxies to Rasa)
echo "Starting static file server on port $PORT..."
python static_server.py