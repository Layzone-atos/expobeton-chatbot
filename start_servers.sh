#!/bin/bash

# Start Servers Script for PythonAnywhere
# This script starts both Rasa and Action servers

echo "Starting ExpoBeton RDC Chatbot Servers..."

# Kill any existing processes
pkill -f "rasa run"
pkill -f "rasa run actions"

# Start Action Server in background
echo "Starting Action Server on port 5055..."
nohup rasa run actions --port 5055 > action_server.log 2>&1 &

# Wait a bit for action server to start
sleep 10

# Start Rasa Server in background
echo "Starting Rasa Server on port 5005..."
nohup rasa run --enable-api --port 5005 --cors "*" > rasa_server.log 2>&1 &

# Wait for servers to initialize
sleep 15

echo "✅ Servers started!"
echo "📋 Check logs:"
echo "  - Action Server: tail -f action_server.log"
echo "  - Rasa Server: tail -f rasa_server.log"

# Keep script running
tail -f rasa_server.log
