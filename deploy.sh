#!/bin/bash

# Quick Deployment Script for PythonAnywhere
# Run this after uploading your project

echo "🚀 ExpoBeton RDC Chatbot - PythonAnywhere Setup"
echo "================================================"

# Step 1: Create virtual environment
echo "📦 Step 1: Creating virtual environment..."
python3.10 -m venv venv
source venv/bin/activate

# Step 2: Install dependencies
echo "📥 Step 2: Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Step 3: Set up environment variables
echo "🔐 Step 3: Setting up environment variables..."
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
COHERE_API_KEY=your_cohere_api_key_here
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
NOTIFICATION_EMAIL=notifications@expobetonrdc.com
EOF
    echo "⚠️  IMPORTANT: Edit .env file with your actual credentials!"
    echo "   Run: nano .env"
else
    echo "✅ .env file already exists"
fi

# Step 4: Train model
echo "🧠 Step 4: Training Rasa model..."
rasa train --fixed-model-name expobeton-french

# Step 5: Make start script executable
echo "⚙️  Step 5: Setting up startup script..."
chmod +x start_servers.sh

echo ""
echo "✅ Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Edit .env file with your API keys: nano .env"
echo "2. Start servers: ./start_servers.sh"
echo "3. Configure web app in PythonAnywhere dashboard"
echo ""
echo "📚 Full instructions: See DEPLOYMENT.md"
