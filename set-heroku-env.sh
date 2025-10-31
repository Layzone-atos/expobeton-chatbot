#!/bin/bash

# Script to set Heroku environment variables
# Run this after deploying to Heroku

echo "Setting Heroku environment variables..."

# Set the action endpoint URL
heroku config:set ACTION_ENDPOINT_URL=https://expobeton-rasa-db7b1977a90f.herokuapp.com/webhook --app expobeton-rasa-db7b1977a90f

# Set the RASA_MODEL environment variable
heroku config:set RASA_MODEL=/app/models/expobeton-french.tar.gz --app expobeton-rasa-db7b1977a90f

echo "Environment variables set. Restarting dynos..."
heroku restart --app expobeton-rasa-db7b1977a90f

echo "Done! Check your app at https://expobeton-rasa-db7b1977a90f.herokuapp.com/"