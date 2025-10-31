# PowerShell script to help set up Heroku deployment
# This script provides guidance and commands for deploying to Heroku

Write-Host "=== Heroku Deployment Setup ===" -ForegroundColor Green
Write-Host ""

# Check if Heroku CLI is installed
Write-Host "Checking if Heroku CLI is installed..." -ForegroundColor Yellow
try {
    $herokuVersion = heroku --version
    Write-Host "Heroku CLI is installed: $herokuVersion" -ForegroundColor Green
    $herokuInstalled = $true
} catch {
    Write-Host "Heroku CLI is not installed." -ForegroundColor Red
    $herokuInstalled = $false
}

Write-Host ""
Write-Host "=== Deployment Steps ===" -ForegroundColor Green

if (-not $herokuInstalled) {
    Write-Host "1. Install Heroku CLI:" -ForegroundColor Yellow
    Write-Host "   - Download from: https://devcenter.heroku.com/articles/heroku-cli" -ForegroundColor Cyan
    Write-Host "   - Run the installer and follow instructions" -ForegroundColor Cyan
    Write-Host "   - Restart your terminal/command prompt after installation" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host "2. Login to Heroku:" -ForegroundColor Yellow
Write-Host "   heroku login" -ForegroundColor Cyan
Write-Host ""

Write-Host "3. Add Heroku remote to your repository:" -ForegroundColor Yellow
Write-Host "   heroku git:remote -a expobeton-rasa-db7b1977a90f" -ForegroundColor Cyan
Write-Host ""

Write-Host "4. Set the container stack:" -ForegroundColor Yellow
Write-Host "   heroku stack:set container --app expobeton-rasa-db7b1977a90f" -ForegroundColor Cyan
Write-Host ""

Write-Host "5. Set required environment variables:" -ForegroundColor Yellow
Write-Host "   heroku config:set ACTION_ENDPOINT_URL=https://expobeton-rasa-db7b1977a90f.herokuapp.com/webhook --app expobeton-rasa-db7b1977a90f" -ForegroundColor Cyan
Write-Host "   heroku config:set RASA_MODEL=/app/models/expobeton-french.tar.gz --app expobeton-rasa-db7b1977a90f" -ForegroundColor Cyan
Write-Host ""

Write-Host "6. Deploy your application:" -ForegroundColor Yellow
Write-Host "   git add ." -ForegroundColor Cyan
Write-Host "   git commit -m 'Deploy to Heroku'" -ForegroundColor Cyan
Write-Host "   git push heroku main" -ForegroundColor Cyan
Write-Host ""

Write-Host "7. Scale your dynos:" -ForegroundColor Yellow
Write-Host "   heroku ps:scale web=1 worker=1 --app expobeton-rasa-db7b1977a90f" -ForegroundColor Cyan
Write-Host ""

Write-Host "8. Check application logs:" -ForegroundColor Yellow
Write-Host "   heroku logs --tail --app expobeton-rasa-db7b1977a90f" -ForegroundColor Cyan
Write-Host ""

Write-Host "=== Alternative Deployment Method ===" -ForegroundColor Green
Write-Host "If you prefer to deploy via the Heroku Dashboard:" -ForegroundColor Yellow
Write-Host "1. Go to https://dashboard.heroku.com/" -ForegroundColor Cyan
Write-Host "2. Select your app 'expobeton-rasa-db7b1977a90f'" -ForegroundColor Cyan
Write-Host "3. Go to the 'Deploy' tab" -ForegroundColor Cyan
Write-Host "4. In 'Deployment method', select 'GitHub'" -ForegroundColor Cyan
Write-Host "5. Connect your GitHub account and repository" -ForegroundColor Cyan
Write-Host "6. Enable automatic deploys or click 'Deploy Branch'" -ForegroundColor Cyan
Write-Host ""

Write-Host "For detailed instructions, see HEROKU-DEPLOYMENT-INSTRUCTIONS.md" -ForegroundColor Green