#!/bin/bash
# FORCE REDEPLOY: 2026-04-17 19:00 - FIX STARTUP ORDER: web server starts first
# Static server starts immediately so Railway health check passes during model training

echo "🚀 Starting Rasa on Railway (With Cohere!)..."
echo "Port: $PORT"

# ============================================================
# STEP 1: Start static web server IMMEDIATELY so Railway
# health check passes. Chatbot will show loading state
# until training completes (~5-8 min).
# ============================================================
echo "🌐 Starting web interface on port $PORT (health check will pass)..."
python static_server.py &
WEB_PID=$!
echo "✅ Web server started (PID $WEB_PID)"

# Small pause to ensure port is bound before training starts
sleep 3

# ============================================================
# STEP 2: Clean caches and train model in background
# ============================================================
echo "🧹 Cleaning Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "✅ Python cache cleaned"

echo "💥 Deleting Rasa cache to force full retrain..."
rm -rf .rasa 2>/dev/null || true
rm -rf models/*.tar.gz 2>/dev/null || true
echo "✅ Rasa cache deleted"

# Train model (this takes 5-8 min - web server already running during this time)
echo "🏋️ Training model with updated NLU data (FULL RETRAIN)..."
rasa train --domain domain.yml --data data --out models --fixed-model-name expobeton-railway --force

# Verify model was created
if [ -f "models/expobeton-railway.tar.gz" ]; then
    echo "✅ Model trained and ready"
else
    echo "❌ Model training failed!"
    # Keep web server running even if training fails
    wait $WEB_PID
    exit 1
fi

# ============================================================
# STEP 3: Start action server
# ============================================================
echo "Starting action server on port 5055..."
pkill -f "rasa run actions" 2>/dev/null || true
sleep 2
rasa run actions --port 5055 &
ACTION_PID=$!
echo "✅ Action server started (PID $ACTION_PID)"

# Wait for action server to be ready
sleep 5

# ============================================================
# STEP 4: Start Rasa server
# ============================================================
echo "Starting Rasa on port 5005..."
rasa run --enable-api --cors "*" --port 5005 -i 0.0.0.0 --model models/expobeton-railway.tar.gz &
RASA_PID=$!
echo "✅ Rasa server started (PID $RASA_PID)"

echo "🎉 All services started. Chatbot is ready!"

# Keep the script alive (web server is the main process)
wait $WEB_PID
