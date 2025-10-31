# Test Docker build locally before deploying to Heroku

Write-Host "Testing Docker build for Rasa server..."
docker build -f Dockerfile.rasa -t expobeton-rasa-test .

Write-Host "Testing Docker build for Action server..."
docker build -f Dockerfile.actions -t expobeton-actions-test .

Write-Host "If builds succeed, you can test locally with:"
Write-Host "docker run -p 5005:5005 expobeton-rasa-test"
Write-Host "docker run -p 5055:5055 expobeton-actions-test"