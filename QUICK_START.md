# 🚀 Quick Start - Render.com Deployment

## ⚡ Super Fast Deployment (5 Steps)

### 1️⃣ **Push to GitHub** (5 minutes)

```bash
# Navigate to project
cd "f:\Louison\Layhosting\Clients\Expo beton\prod-rasa-d3f2c138"

# Initialize Git
git init
git add .
git commit -m "Initial commit for Render deployment"

# Create repo on GitHub.com, then:
git remote add origin https://github.com/YOUR_USERNAME/expobeton-chatbot.git
git branch -M main
git push -u origin main
```

---

### 2️⃣ **Deploy Action Server** (3 minutes)

1. Go to [render.com](https://render.com) → **New +** → **Web Service**
2. Connect GitHub repo: `expobeton-chatbot`
3. Settings:
   - **Name**: `expobeton-actions`
   - **Runtime**: Docker
   - **Dockerfile**: `Dockerfile.actions`
   - **Plan**: Free
4. Add Environment Variables:
   ```
   COHERE_API_KEY = [your key]
   SMTP_USERNAME = [your email]
   SMTP_PASSWORD = [your app password]
   NOTIFICATION_EMAIL = info@expobetonrdc.com
   ```
5. Click **Create Web Service**

Copy the URL: `https://expobeton-actions.onrender.com` ✅

---

### 3️⃣ **Deploy Rasa Server** (3 minutes)

1. **New +** → **Web Service**
2. Connect same repo
3. Settings:
   - **Name**: `expobeton-rasa`
   - **Runtime**: Docker
   - **Dockerfile**: `Dockerfile.rasa`
   - **Plan**: Free
4. Add Environment Variable:
   ```
   ACTION_ENDPOINT_URL = https://expobeton-actions.onrender.com/webhook
   ```
5. Click **Create Web Service**

Copy the URL: `https://expobeton-rasa.onrender.com` ✅

---

### 4️⃣ **Update Chat Widget** (1 minute)

Edit `web/chat-widget.js` line 5:

```javascript
const RASA_SERVER_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:5005/webhooks/rest/webhook'
    : 'https://expobeton-rasa.onrender.com/webhooks/rest/webhook'; // ← Your URL here
```

Push changes:
```bash
git add web/chat-widget.js
git commit -m "Update Rasa URL"
git push
```

---

### 5️⃣ **Deploy Web Server** (2 minutes)

1. **New +** → **Static Site**
2. Connect same repo
3. Settings:
   - **Name**: `expobeton-web`
   - **Build Command**: Leave empty
   - **Publish Directory**: `web`
4. Click **Create Static Site**

Your chatbot is LIVE! 🎉

Visit: `https://expobeton-web.onrender.com`

---

## 🎯 **Total Time: ~15 minutes**

## ✅ **What You Get**

- ✨ **Live Chatbot**: Working on Render's domain
- 🌐 **HTTPS**: Free SSL certificate
- 🔄 **Auto-Deploy**: Push to GitHub = Auto update
- 📊 **Monitoring**: Built-in logs & metrics
- 🆓 **Free**: 750 hours/month per service

---

## 🌍 **Add Your Domain (Optional)**

In Render dashboard:
1. Go to `expobeton-web` service
2. **Settings** → **Custom Domain**
3. Add: `expobetonrdc.com`
4. Update DNS:
   ```
   CNAME record
   Name: www
   Value: expobeton-web.onrender.com
   ```

---

## 📚 **Full Guide**

See [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for complete details.

---

## ⚡ **Keep Alive (Prevent Sleep)**

Free tier sleeps after 15 min. Use [UptimeRobot](https://uptimerobot.com):
1. Sign up (free)
2. Add monitor: `https://expobeton-web.onrender.com`
3. Interval: Every 5 minutes

This keeps your chatbot always ready! 🚀

---

**Need help?** Check logs in Render dashboard → Service → Logs tab
