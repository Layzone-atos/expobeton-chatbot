#!/bin/bash
# FORCE REDEPLOY: 2025-11-08 17:30 - LUBUMBASHI FIX V4 - CRITICAL RELOAD REQUIRED
# Timestamp changed to force full redeploy and Python cache invalidation

echo "🧹 Cleaning Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "✅ Python cache cleaned"

echo "💥 Deleting Rasa cache to force full retrain..."
rm -rf .rasa 2>/dev/null || true
rm -rf models/*.tar.gz 2>/dev/null || true
echo "✅ Rasa cache deleted"

echo "🚀 Starting Rasa on Railway (With Cohere!)..."
echo "Port: $PORT"

# Train model with latest data (NLU examples) - FULL RETRAIN WITHOUT CACHE
echo "🏋️ Training model with updated NLU data (FULL RETRAIN)..."
rasa train --domain domain.yml --data data --out models --fixed-model-name expobeton-railway --force

# Use the NEW trained model with 85.5% accuracy
echo "Using trained model (85.5% accuracy - with Cohere support)..."
if [ -f "models/expobeton-railway.tar.gz" ]; then
    echo "✅ Model ready"
else
    echo "❌ Model not found!"
    exit 1
fi

# Start action server on port 5055 in background
echo "Starting action server on port 5055..."
echo "🔥 CRITICAL: actions.py should print TIMESTAMP 2025-11-08 17:30:00 UTC"
pkill -f "rasa run actions" 2>/dev/null || true  # Kill any old action servers
sleep 2
rasa run actions --port 5055 &

# Wait for action server to start
sleep 5

# Start Rasa on port 5005 in background
echo "Starting Rasa on port 5005..."
rasa run --enable-api --cors "*" --port 5005 -i 0.0.0.0 --model models/expobeton-railway.tar.gz &

# Wait for Rasa to start
sleep 20

# Start static server on Railway port (serves web interface + proxies to Rasa)
echo "Starting web interface on port $PORT..."
python static_server.py
