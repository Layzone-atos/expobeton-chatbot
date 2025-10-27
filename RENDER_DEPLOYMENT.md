# 🚀 ExpoBeton RDC Chatbot - Render.com Deployment Guide

## 📋 Prerequisites

- ✅ Render.com account (free) - [Sign up here](https://render.com)
- ✅ GitHub account
- ✅ Git installed locally
- ✅ Trained Rasa model (`models/expobeton-french.tar.gz`)

---

## 🎯 **Deployment Strategy**

We'll deploy **3 separate services** on Render:

1. **Action Server** - Handles custom actions (Python)
2. **Rasa Server** - Main chatbot engine
3. **Web Server** - Static site with chat widget

---

## 📦 **Step 1: Prepare Your Project**

### 1.1 Train Model Locally (if not done)

```bash
cd "f:\Louison\Layhosting\Clients\Expo beton\prod-rasa-d3f2c138"
uv run rasa train --fixed-model-name expobeton-french
```

This creates: `models/expobeton-french.tar.gz`

### 1.2 Update .gitignore

Make sure your `.gitignore` does **NOT** exclude the trained model:

```bash
# In .gitignore, comment out this line if present:
# models/*.tar.gz

# We NEED to commit the trained model for Render
```

### 1.3 Update Chat Widget URL

Edit `web/chat-widget.js` line 1:

```javascript
// For now, use relative URL - we'll update after deployment
const RASA_SERVER_URL = '/webhooks/rest/webhook';
```

---

## 🐙 **Step 2: Push to GitHub**

### 2.1 Initialize Git Repository

```bash
cd "f:\Louison\Layhosting\Clients\Expo beton\prod-rasa-d3f2c138"

# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - ExpoBeton chatbot for Render deployment"
```

### 2.2 Create GitHub Repository

1. Go to [github.com](https://github.com)
2. Click **New repository**
3. Name: `expobeton-chatbot`
4. **Don't** initialize with README (we already have files)
5. Click **Create repository**

### 2.3 Push to GitHub

```bash
# Add remote
git remote add origin https://github.com/YOUR_USERNAME/expobeton-chatbot.git

# Push
git branch -M main
git push -u origin main
```

---

## 🌐 **Step 3: Deploy to Render**

### 3.1 Login to Render

1. Go to [render.com](https://render.com)
2. Click **Sign In** or **Get Started**
3. Sign in with **GitHub** (easiest)

### 3.2 Create Action Server

1. Click **New +** → **Web Service**
2. Connect your GitHub repository: `expobeton-chatbot`
3. Configure:

   **Basic Info:**
   - Name: `expobeton-actions`
   - Region: Choose closest to your users (e.g., Frankfurt for Europe)
   - Branch: `main`
   - Runtime: **Docker**
   - Dockerfile Path: `Dockerfile.actions`

   **Instance Type:**
   - Select: **Free**

   **Environment Variables:**
   Click **Add Environment Variable** for each:
   ```
   COHERE_API_KEY = your_cohere_api_key_here
   SMTP_SERVER = smtp.gmail.com
   SMTP_PORT = 587
   SMTP_USERNAME = your_email@gmail.com
   SMTP_PASSWORD = your_app_password
   NOTIFICATION_EMAIL = info@expobetonrdc.com
   ```

4. Click **Create Web Service**

Wait for deployment (5-10 minutes). You'll get URL like:
`https://expobeton-actions.onrender.com`

### 3.3 Create Rasa Server

1. Click **New +** → **Web Service**
2. Connect same repository: `expobeton-chatbot`
3. Configure:

   **Basic Info:**
   - Name: `expobeton-rasa`
   - Region: Same as action server
   - Branch: `main`
   - Runtime: **Docker**
   - Dockerfile Path: `Dockerfile.rasa`

   **Instance Type:**
   - Select: **Free**

   **Environment Variables:**
   ```
   ACTION_ENDPOINT_URL = https://expobeton-actions.onrender.com/webhook
   RASA_MODEL = /app/models/expobeton-french.tar.gz
   ```

4. Click **Create Web Service**

Wait for deployment. You'll get URL like:
`https://expobeton-rasa.onrender.com`

### 3.4 Create Web Server (Static Site)

1. Click **New +** → **Static Site**
2. Connect same repository
3. Configure:

   **Basic Info:**
   - Name: `expobeton-web`
   - Branch: `main`
   - Build Command: Leave empty or `echo "No build"`
   - Publish Directory: `web`

   **Custom Domain (Optional):**
   - You can add `expobetonrdc.com` later

4. Click **Create Static Site**

You'll get URL like:
`https://expobeton-web.onrender.com`

---

## 🔧 **Step 4: Configure URLs**

### 4.1 Update Chat Widget

Edit `web/chat-widget.js`:

```javascript
// Update with your Rasa server URL
const RASA_SERVER_URL = 'https://expobeton-rasa.onrender.com/webhooks/rest/webhook';
```

### 4.2 Update endpoints.yml

Edit `endpoints.yml`:

```yaml
action_endpoint:
  url: "https://expobeton-actions.onrender.com/webhook"
```

### 4.3 Commit and Push Changes

```bash
git add .
git commit -m "Update URLs for Render deployment"
git push origin main
```

Render will **auto-deploy** when you push! 🎉

---

## 🧪 **Step 5: Test Your Chatbot**

1. Visit: `https://expobeton-web.onrender.com`
2. Click the chat button (bottom right)
3. Test conversation:
   - French: "Bonjour, je m'appelle Louis"
   - English: "Hello, how are you?"
   - Questions: "How to become an ambassador?"
   - Feedback system

---

## 🌍 **Step 6: Add Custom Domain (expobetonrdc.com)**

### 6.1 In Render Dashboard

1. Go to your **expobeton-web** service
2. Click **Settings** → **Custom Domain**
3. Click **Add Custom Domain**
4. Enter: `chat.expobetonrdc.com` (or `www.expobetonrdc.com`)

### 6.2 Update DNS Settings

In your domain registrar (where you bought expobetonrdc.com):

**Add CNAME Record:**
```
Type: CNAME
Name: chat (or www)
Value: expobeton-web.onrender.com
TTL: 3600
```

**Or A Record:**
```
Type: A
Name: @ (root domain)
Value: [IP provided by Render]
TTL: 3600
```

Wait 24-48 hours for DNS propagation.

### 6.3 Enable HTTPS

Render automatically provides free SSL certificate! 🔒

---

## 📊 **Monitoring & Logs**

### View Logs

1. Go to Render Dashboard
2. Click on service (e.g., `expobeton-rasa`)
3. Click **Logs** tab
4. See real-time logs

### Check Service Health

Each service has a **Metrics** tab showing:
- CPU usage
- Memory usage
- Request rate
- Response time

---

## ⚠️ **Important Notes**

### Free Tier Limitations

- **Sleeps after 15 minutes** of inactivity
- **First request** may be slow (30-60 seconds to wake up)
- **750 hours/month** limit per service

### Keep Services Alive (Optional)

Use a free service like **UptimeRobot** to ping your site every 5 minutes:
1. Sign up at [uptimerobot.com](https://uptimerobot.com)
2. Add monitor: `https://expobeton-web.onrender.com`
3. Interval: Every 5 minutes

### Upgrade If Needed

If your chatbot gets popular:
- **Starter Plan**: $7/month (no sleep, faster)
- **Professional**: $20/month (dedicated resources)

---

## 🔄 **Auto-Deploy Workflow**

Every time you push to GitHub:
1. ✅ Render detects changes
2. ✅ Rebuilds Docker images
3. ✅ Deploys new version
4. ✅ Zero downtime deployment

### Update Chatbot

```bash
# Make changes locally
# ... edit files ...

# Train new model if needed
uv run rasa train --fixed-model-name expobeton-french

# Commit and push
git add .
git commit -m "Update chatbot responses"
git push origin main

# Render auto-deploys! 🚀
```

---

## 🐛 **Troubleshooting**

### Service Won't Start

**Check Logs:**
- Go to service → Logs tab
- Look for error messages

**Common Issues:**
- Missing environment variables
- Model file too large (max 500MB on free tier)
- Dockerfile errors

### Chatbot Not Responding

1. **Check Action Server** is running
2. **Check Rasa Server** is running
3. **Check endpoints.yml** has correct action URL
4. **Check browser console** for CORS errors

### CORS Errors

In Rasa Dockerfile, ensure:
```dockerfile
CMD ["run", "--enable-api", "--port", "5005", "--cors", "*"]
```

---

## 📈 **Performance Tips**

1. **Optimize Model Size**
   - Use `--augmentation 0` when training
   - Remove unnecessary components

2. **Cache Responses**
   - Implement caching in action server
   - Reduce API calls

3. **Use CDN**
   - Render provides automatic CDN for static files

---

## 🎯 **Next Steps**

- [ ] Test chatbot thoroughly
- [ ] Monitor usage in Render dashboard
- [ ] Set up UptimeRobot to prevent sleep
- [ ] Add custom domain
- [ ] Configure email notifications
- [ ] Set up analytics (Google Analytics)
- [ ] Plan for scaling if needed

---

## 📞 **Support**

**Render Documentation:**
- [Render Docs](https://render.com/docs)
- [Docker Deployments](https://render.com/docs/docker)

**Need Help?**
- Check logs in Render dashboard
- Render Community Forum
- GitHub Issues

---

## ✅ **Deployment Checklist**

- [ ] Trained model exists (`models/expobeton-french.tar.gz`)
- [ ] Code pushed to GitHub
- [ ] Action server deployed on Render
- [ ] Rasa server deployed on Render
- [ ] Web server deployed on Render
- [ ] Environment variables configured
- [ ] URLs updated in code
- [ ] Custom domain added (optional)
- [ ] Chatbot tested and working
- [ ] UptimeRobot configured (optional)

---

**You're all set!** 🎉

Your ExpoBeton chatbot is now live on Render.com! 🚀
