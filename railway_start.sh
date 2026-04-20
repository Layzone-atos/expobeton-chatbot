#!/bin/bash
# STARTUP v2026-04-17 - Model pre-trained in Docker image, instant startup
# No training at runtime = Railway health check passes immediately

echo "🚀 Starting ExpoBeton Chatbot services..."
echo "Port: $PORT"

# Verify pre-trained model exists
if [ -f "models/expobeton-railway.tar.gz" ]; then
    echo "✅ Pre-trained model found: models/expobeton-railway.tar.gz"
else
    echo "❌ ERROR: No pre-trained model found! Check Docker build logs."
    ls -la models/ 2>/dev/null || echo "models/ directory is empty or missing"
    exit 1
fi

# ============================================================
# STEP 1: Start action server on port 5055
# ============================================================
echo "🤖 Starting action server on port 5055..."
pkill -f "rasa run actions" 2>/dev/null || true
rasa run actions --port 5055 &
ACTION_PID=$!
echo "✅ Action server started (PID $ACTION_PID)"

# Wait for action server to initialize
sleep 5

# ============================================================
# STEP 2: Start Rasa server on port 5005
# ============================================================
echo "💬 Starting Rasa server on port 5005..."
rasa run --enable-api --cors "*" --port 5005 -i 0.0.0.0 --model models/expobeton-railway.tar.gz &
RASA_PID=$!
echo "✅ Rasa server started (PID $RASA_PID)"

# Wait for Rasa to load model
sleep 15

# ============================================================
# STEP 3: Start web server (foreground - keeps container alive)
# Railway health check will pass as soon as this binds to $PORT
# ============================================================
echo "🌐 Starting web interface on port $PORT..."
echo "🎉 All services starting - chatbot will be ready in ~15 seconds!"
exec python static_server.py
