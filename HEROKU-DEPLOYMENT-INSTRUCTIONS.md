# Heroku Deployment Instructions

Since the Heroku CLI is not installed on your system, you'll need to install it first before you can deploy your application.

## Step 1: Install Heroku CLI

1. Download the Heroku CLI installer from: https://devcenter.heroku.com/articles/heroku-cli
2. Run the installer and follow the installation instructions
3. After installation, restart your terminal/command prompt
4. Verify the installation by running:
   ```bash
   heroku --version
   ```

## Step 2: Login to Heroku

After installing the Heroku CLI, login to your account:
```bash
heroku login
```

This will open a browser window where you can log in to your Heroku account.

## Step 3: Add Heroku Remote

Navigate to your project directory and add the Heroku remote:
```bash
cd F:\Louison\Layhosting\Clients\Expo beton\prod-rasa-d3f2c138
heroku git:remote -a expobeton-rasa-db7b1977a90f
```

## Step 4: Set Heroku Stack

Set the container stack for your application:
```bash
heroku stack:set container --app expobeton-rasa-db7b1977a90f
```

## Step 5: Set Environment Variables

Set the required environment variables:
```bash
heroku config:set ACTION_ENDPOINT_URL=https://expobeton-rasa-db7b1977a90f.herokuapp.com/webhook --app expobeton-rasa-db7b1977a90f
heroku config:set RASA_MODEL=/app/models/expobeton-french.tar.gz --app expobeton-rasa-db7b1977a90f
```

## Step 6: Deploy to Heroku

Now you can deploy your application:
```bash
git add .
git commit -m "Prepare for Heroku deployment"
git push heroku main
```

## Step 7: Scale Dynos

After deployment, scale your dynos:
```bash
heroku ps:scale web=1 worker=1 --app expobeton-rasa-db7b1977a90f
```

## Step 8: Check Application Logs

Monitor your application logs:
```bash
heroku logs --tail --app expobeton-rasa-db7b1977a90f
```

## Alternative Deployment Method

If you continue to have issues with the Heroku CLI, you can also deploy using the Heroku Dashboard:

1. Go to https://dashboard.heroku.com/
2. Select your app "expobeton-rasa-db7b1977a90f"
3. Go to the "Deploy" tab
4. In the "Deployment method" section, select "GitHub"
5. Connect your GitHub account if not already connected
6. Search for your repository and connect it
7. Enable automatic deploys from your preferred branch (usually main)
8. Click "Deploy Branch" to deploy manually

## Troubleshooting

If you encounter any issues:

1. Make sure you have the latest version of Heroku CLI installed
2. Ensure you're logged in to the correct Heroku account
3. Check that your app name is correct
4. Verify that your repository contains all necessary files
5. Check the application logs for specific error messages

## Testing Your Deployment

After successful deployment, test your application:
```bash
curl https://expobeton-rasa-db7b1977a90f.herokuapp.com/health
```

If everything is working correctly, you should see a response indicating that your application is healthy.