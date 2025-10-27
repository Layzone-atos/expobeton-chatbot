# ExpoBeton RDC - Web Chat Interface

## 📋 Overview

This is a beautiful, modern web chat interface for the ExpoBeton RDC chatbot. It features:

- 💬 Floating chat icon (bottom-right corner)
- 📝 User information form (name required, phone/email optional)
- 🎨 Professional design with ExpoBeton branding
- ⚡ Real-time chat with Rasa backend
- 📱 Fully responsive design

## 🚀 Quick Start

### 1. Start the Rasa Servers

You need **two terminals** running:

**Terminal 1 - Action Server:**
```powershell
.\.venv\Scripts\python.exe -m rasa_sdk --actions actions
```

**Terminal 2 - Rasa Server (REST API):**
```powershell
uv run rasa run --enable-api --cors "*" --port 5005
```

> **Important:** Use `--cors "*"` to allow the web page to communicate with the Rasa server.

### 2. Open the Web Interface

Simply open the `index.html` file in your browser:
```
web/index.html
```

Or use a local web server (recommended):
```powershell
# Using Python
cd web
python -m http.server 8000

# Then open: http://localhost:8000
```

## 📁 File Structure

```
web/
├── index.html          # Main HTML file
├── chat-widget.css     # Styles
├── chat-widget.js      # Chat functionality
└── README.md          # This file
```

## 🎨 Customization

### Change Colors

Edit `chat-widget.css` and modify these variables:

```css
/* Primary color (ExpoBeton blue) */
background: linear-gradient(135deg, #0A2A66 0%, #1e3a8a 100%);

/* Secondary color (grey) */
color: #6C757D;
```

### Change Rasa Server URL

Edit `chat-widget.js`, line 2:

```javascript
const RASA_SERVER_URL = 'http://localhost:5005';
```

For production, change to your production server:
```javascript
const RASA_SERVER_URL = 'https://your-domain.com/rasa';
```

### Customize Welcome Message

Edit the form in `index.html`:

```html
<h3>👋 Bienvenue chez ExpoBeton RDC!</h3>
<p>Pour mieux vous servir, veuillez remplir ces informations:</p>
```

## 🔧 Integration with Your Website

### Option 1: Copy Files

1. Copy all files from `web/` folder to your website
2. Link the CSS and JS in your HTML:

```html
<link rel="stylesheet" href="chat-widget.css">
<script src="chat-widget.js"></script>
```

3. Add the chat widget HTML (see `index.html` for the widget code)

### Option 2: Use as Widget

You can include just the chat widget part in any page:

```html
<!-- In your <head> -->
<link rel="stylesheet" href="path/to/chat-widget.css">

<!-- Before closing </body> -->
<div id="chat-widget">
    <!-- Copy the chat widget HTML from index.html -->
</div>
<script src="path/to/chat-widget.js"></script>
```

## 🌐 CORS Configuration

If you encounter CORS errors, make sure your Rasa server is started with:

```powershell
uv run rasa run --enable-api --cors "*" --port 5005
```

For production, limit CORS to your domain:

```powershell
uv run rasa run --enable-api --cors "https://your-domain.com" --port 5005
```

## 📱 Mobile Responsive

The chat widget is fully responsive and adapts to:
- Desktop (400px width)
- Tablet (full width with margins)
- Mobile (full screen)

## ✨ Features

### User Information Collection
- **Name:** Required field
- **Phone:** Optional
- **Email:** Optional

This information is sent with each message to Rasa as metadata.

### Chat Features
- Smooth animations
- Typing indicator
- Message timestamps
- Auto-scroll to latest message
- Notification badge
- Professional UI/UX

## 🎯 Testing

1. Open the page
2. Click the floating chat button (bottom-right)
3. Fill in the user form
4. Start chatting!

Test questions:
- "C'est quoi ExpoBeton ?"
- "Quelles sont les dates ?"
- "Comment devenir ambassadeur ?"

## 🐛 Troubleshooting

### Chat widget doesn't open
- Check browser console for errors
- Ensure JavaScript is enabled

### Messages not sending
- Verify Rasa server is running on port 5005
- Check console for CORS errors
- Ensure action server is running on port 5055

### Styling issues
- Clear browser cache
- Check if CSS file is loaded
- Verify file paths are correct

## 📞 Support

For issues or questions, contact the ExpoBeton RDC team.

---

**Developed for ExpoBeton RDC** 🏗️🇨🇩
