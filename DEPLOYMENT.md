# ExpoBeton RDC Chatbot - Deployment Guide

## 🚀 PythonAnywhere Deployment

### Prerequisites
- PythonAnywhere account (free or paid)
- Git repository or ZIP file of this project

### Step 1: Upload Project to PythonAnywhere

#### Option A: Using Git (Recommended)
1. Go to PythonAnywhere Dashboard
2. Open a **Bash Console**
3. Clone your repository:
   ```bash
   git clone https://github.com/yourusername/expobeton-chatbot.git
   cd expobeton-chatbot
   ```

#### Option B: Upload ZIP File
1. Go to **Files** tab in PythonAnywhere
2. Click **Upload a file**
3. Upload your project ZIP file
4. Unzip it:
   ```bash
   unzip expobeton-chatbot.zip
   cd expobeton-chatbot
   ```

### Step 2: Set Up Virtual Environment

```bash
# Create virtual environment
python3.10 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Create `.env` file:
```bash
nano .env
```

Add your API keys:
```
COHERE_API_KEY=your_cohere_api_key_here
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
NOTIFICATION_EMAIL=notifications@expobetonrdc.com
```

### Step 4: Train the Model

```bash
# Make sure you're in the project directory
cd ~/expobeton-chatbot

# Activate virtual environment
source venv/bin/activate

# Train the model
rasa train --fixed-model-name expobeton-french
```

### Step 5: Start Servers

Make the startup script executable:
```bash
chmod +x start_servers.sh
```

Start the servers:
```bash
./start_servers.sh
```

Or start manually:

**Terminal 1 - Action Server:**
```bash
source venv/bin/activate
rasa run actions --port 5055
```

**Terminal 2 - Rasa Server:**
```bash
source venv/bin/activate
rasa run --enable-api --port 5005 --cors "*"
```

### Step 6: Set Up Web App

1. Go to **Web** tab in PythonAnywhere
2. Click **Add a new web app**
3. Choose **Manual configuration**
4. Select **Python 3.10**

#### Configure WSGI File

Edit `/var/www/yourusername_pythonanywhere_com_wsgi.py`:

```python
import sys
import os
from pathlib import Path

# Add your project directory to the sys.path
project_home = '/home/yourusername/expobeton-chatbot'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Set up static files
from flask import Flask, send_from_directory

app = Flask(__name__)

@app.route('/')
def index():
    return send_from_directory(os.path.join(project_home, 'web'), 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(os.path.join(project_home, 'web'), path)

# Proxy to Rasa server
@app.route('/webhooks/rest/webhook', methods=['POST'])
def rasa_webhook():
    import requests
    from flask import request, jsonify
    
    # Forward to local Rasa server
    response = requests.post(
        'http://localhost:5005/webhooks/rest/webhook',
        json=request.get_json(),
        headers={'Content-Type': 'application/json'}
    )
    return jsonify(response.json())
```

#### Configure Static Files

In the **Web** tab:
- **Static files:**
  - URL: `/`
  - Directory: `/home/yourusername/expobeton-chatbot/web`

### Step 7: Keep Servers Running

Create a scheduled task (in **Tasks** tab):
```bash
cd /home/yourusername/expobeton-chatbot && source venv/bin/activate && ./start_servers.sh
```

Schedule it to run every hour.

---

## ⚠️ PythonAnywhere Limitations

### Issues You May Face:

1. **Memory Limits** - Rasa is heavy, may crash on free tier
2. **CPU Limits** - Responses may be slow
3. **Port Restrictions** - Can't expose ports 5005/5055 directly
4. **Background Processes** - May be killed if inactive

---

## 🎯 Better Alternatives

### 1. **Railway.app** (Recommended)
- Free tier with generous limits
- Easy deployment with GitHub
- Better for Rasa/Python apps
- Free domain included

### 2. **Render.com**
- Free tier available
- Docker support
- Auto-deploy from Git
- Good for Rasa

### 3. **DigitalOcean App Platform**
- $5/month basic tier
- Full control
- Best performance

---

## 🌐 Update Web Chat URL

After deployment, update the Rasa server URL in `web/chat-widget.js`:

```javascript
const RASA_SERVER_URL = 'https://yourusername.pythonanywhere.com/webhooks/rest/webhook';
```

---

## 📧 Support

For issues, check:
- Action server logs: `tail -f action_server.log`
- Rasa server logs: `tail -f rasa_server.log`
- Web app error log in PythonAnywhere dashboard

---

## ✅ Testing

After deployment, test:
1. Visit: `https://yourusername.pythonanywhere.com`
2. Open chat widget
3. Test conversation in French and English
4. Test feedback system
