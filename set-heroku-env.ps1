# PowerShell script to set Heroku environment variables
# Run this after deploying to Heroku

Write-Host "Setting Heroku environment variables..."

# Set the action endpoint URL
heroku config:set ACTION_ENDPOINT_URL=https://expobeton-rasa-db7b1977a90f.herokuapp.com/webhook --app expobeton-rasa-db7b1977a90f

# Set the RASA_MODEL environment variable
heroku config:set RASA_MODEL=/app/models/expobeton-french.tar.gz --app expobeton-rasa-db7b1977a90f

Write-Host "Environment variables set. Restarting dynos..."
heroku restart --app expobeton-rasa-db7b1977a90f

Write-Host "Done! Check your app at https://expobeton-rasa-db7b1977a90f.herokuapp.com/"