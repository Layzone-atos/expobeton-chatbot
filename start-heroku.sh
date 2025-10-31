#!/bin/bash

# Start script for Heroku deployment

# Check if we're starting the action server
if [ "$ROLE" = "action" ]; then
    echo "Starting Action Server..."
    rasa run actions --port $PORT
else
    # Default to starting the Rasa server
    echo "Starting Rasa Server..."
    rasa run --enable-api --port $PORT --cors "*" --debug
fi