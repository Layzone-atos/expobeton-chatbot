@echo off
echo === Heroku Deployment Setup ===
echo.

echo Checking if Heroku CLI is installed...
heroku --version >nul 2>&1
if %errorlevel% == 0 (
    echo Heroku CLI is installed.
) else (
    echo Heroku CLI is not installed.
    echo.
    echo Please install Heroku CLI:
    echo 1. Download from: https://devcenter.heroku.com/articles/heroku-cli
    echo 2. Run the installer and follow instructions
    echo 3. Restart your command prompt after installation
    echo.
)

echo.
echo === Deployment Steps ===
echo.

echo 1. Login to Heroku:
echo    heroku login
echo.

echo 2. Add Heroku remote to your repository:
echo    heroku git:remote -a expobeton-rasa-db7b1977a90f
echo.

echo 3. Set the container stack:
echo    heroku stack:set container --app expobeton-rasa-db7b1977a90f
echo.

echo 4. Set required environment variables:
echo    heroku config:set ACTION_ENDPOINT_URL=https://expobeton-rasa-db7b1977a90f.herokuapp.com/webhook --app expobeton-rasa-db7b1977a90f
echo    heroku config:set RASA_MODEL=/app/models/expobeton-french.tar.gz --app expobeton-rasa-db7b1977a90f
echo.

echo 5. Deploy your application:
echo    git add .
echo    git commit -m "Deploy to Heroku"
echo    git push heroku main
echo.

echo 6. Scale your dynos:
echo    heroku ps:scale web=1 worker=1 --app expobeton-rasa-db7b1977a90f
echo.

echo 7. Check application logs:
echo    heroku logs --tail --app expobeton-rasa-db7b1977a90f
echo.

echo === Alternative Deployment Method ===
echo If you prefer to deploy via the Heroku Dashboard:
echo 1. Go to https://dashboard.heroku.com/
echo 2. Select your app 'expobeton-rasa-db7b1977a90f'
echo 3. Go to the 'Deploy' tab
echo 4. In 'Deployment method', select 'GitHub'
echo 5. Connect your GitHub account and repository
echo 6. Enable automatic deploys or click 'Deploy Branch'
echo.

echo For detailed instructions, see HEROKU-DEPLOYMENT-INSTRUCTIONS.md
pause