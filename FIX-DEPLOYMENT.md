# Fixing Heroku Deployment Issues

It appears your Rasa chatbot deployment to Heroku is experiencing issues, showing a 502 Bad Gateway error. Here's how to fix it:

## Issues Identified

1. **Incorrect PORT handling in Dockerfiles** - The Dockerfiles were trying to use Heroku's PORT environment variable incorrectly
2. **Missing environment variables** - The ACTION_ENDPOINT_URL needs to be set correctly
3. **Container deployment configuration** - Need to ensure proper Heroku stack is set

## Steps to Fix

### 1. Set the Correct Heroku Stack

Make sure you're using the container stack:

```bash
heroku stack:set container --app expobeton-rasa-db7b1977a90f
```

### 2. Set Required Environment Variables

Run the PowerShell script to set the environment variables:

```powershell
.\set-heroku-env.ps1
```

Or manually set them:

```bash
heroku config:set ACTION_ENDPOINT_URL=https://expobeton-rasa-db7b1977a90f.herokuapp.com/webhook --app expobeton-rasa-db7b1977a90f
heroku config:set RASA_MODEL=/app/models/expobeton-french.tar.gz --app expobeton-rasa-db7b1977a90f
```

### 3. Redeploy Your Application

After making these changes, redeploy your application:

```bash
git add .
git commit -m "Fix Heroku deployment issues"
git push heroku main
```

### 4. Scale Your Dynos

Make sure both web and worker dynos are scaled properly:

```bash
heroku ps:scale web=1 worker=1 --app expobeton-rasa-db7b1977a90f
```

### 5. Check the Logs

Monitor your application logs to see if the issues are resolved:

```bash
heroku logs --tail --app expobeton-rasa-db7b1977a90f
```

## Testing Your Deployment

After fixing the deployment, test it using the provided test script:

```bash
python test-heroku-deployment.py
```

## Common Issues and Solutions

1. **502 Bad Gateway**: Usually indicates the web process isn't starting correctly
2. **Application Error**: Could be due to missing dependencies or incorrect paths
3. **H10 Error**: Means the application crashed on startup

If you continue to experience issues, check the logs for specific error messages and ensure:
- Your model file is correctly included in the deployment
- All required dependencies are in requirements.txt
- The Dockerfiles are correctly configured
- Environment variables are properly set

## Next Steps

Once your deployment is working, you can:
1. Integrate the chatbot with your website using the web widget
2. Test the conversation flows
3. Monitor usage and performance