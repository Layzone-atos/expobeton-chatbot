#!/bin/bash

# Test Docker build locally before deploying to Heroku

echo "Testing Docker build for Rasa server..."
docker build -f Dockerfile.rasa -t expobeton-rasa-test .

echo "Testing Docker build for Action server..."
docker build -f Dockerfile.actions -t expobeton-actions-test .

echo "If builds succeed, you can test locally with:"
echo "docker run -p 5005:5005 expobeton-rasa-test"
echo "docker run -p 5055:5055 expobeton-actions-test"