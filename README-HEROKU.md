# Deploying Rasa Chatbot to Heroku

This guide explains how to deploy your Rasa chatbot to Heroku.

## Prerequisites

1. Heroku account (free tier available)
2. Heroku CLI installed
3. Git installed

## Deployment Steps

### 1. Login to Heroku

```bash
heroku login
```

### 2. Create a Heroku App

```bash
heroku create your-app-name
```

Or if you want Heroku to generate a name:

```bash
heroku create
```

### 3. Set Buildpack (Optional - for container deployment)

If you want to use container deployment:

```bash
heroku stack:set container
```

### 4. Set Environment Variables

You'll need to set the following environment variables in Heroku:

```bash
heroku config:set ACTION_ENDPOINT_URL=https://your-app-name.herokuapp.com/webhook
```

### 5. Deploy to Heroku

Add and commit your changes:

```bash
git add .
git commit -m "Prepare for Heroku deployment"
```

Deploy to Heroku:

```bash
git push heroku main
```

### 6. Scale Dynos

After deployment, scale your dynos:

```bash
heroku ps:scale web=1 worker=1
```

### 7. Check Logs

Monitor your application logs:

```bash
heroku logs --tail
```

## Access Your Bot

Once deployed, your Rasa server will be accessible at:
`https://your-app-name.herokuapp.com`

Your action server webhook endpoint will be:
`https://your-app-name.herokuapp.com/webhook`

## Troubleshooting

1. If you encounter memory issues, consider upgrading to a paid Heroku dyno
2. Make sure your model file is included in the deployment
3. Check logs with `heroku logs --tail` for error messages