#!/bin/bash

# Quick Deployment to Render.com
# Run this script to prepare your project for Render deployment

echo "🚀 ExpoBeton RDC - Render.com Deployment Preparation"
echo "===================================================="
echo ""

# Step 1: Check if model exists
echo "📋 Step 1: Checking trained model..."
if [ -f "models/expobeton-french.tar.gz" ]; then
    echo "✅ Model found: models/expobeton-french.tar.gz"
else
    echo "❌ Model not found!"
    echo "   Training model now..."
    uv run rasa train --fixed-model-name expobeton-french
fi

# Step 2: Check Git
echo ""
echo "📋 Step 2: Checking Git repository..."
if [ -d ".git" ]; then
    echo "✅ Git repository exists"
else
    echo "⚠️  Initializing Git repository..."
    git init
    echo "✅ Git initialized"
fi

# Step 3: Create .env.example
echo ""
echo "📋 Step 3: Creating .env.example..."
cat > .env.example << 'EOF'
# Cohere API Key
COHERE_API_KEY=your_cohere_api_key_here

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
NOTIFICATION_EMAIL=info@expobetonrdc.com
EOF
echo "✅ Created .env.example"

# Step 4: Update gitignore to keep model
echo ""
echo "📋 Step 4: Updating .gitignore..."
# Remove models/*.tar.gz from gitignore if present
sed -i '/^models\/\*\.tar\.gz$/d' .gitignore 2>/dev/null || true
echo "✅ .gitignore updated (model will be committed)"

# Step 5: Stage files
echo ""
echo "📋 Step 5: Staging files for commit..."
git add .
echo "✅ Files staged"

echo ""
echo "======================================================"
echo "✅ Preparation Complete!"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1️⃣  Review your files:"
echo "   git status"
echo ""
echo "2️⃣  Commit changes:"
echo "   git commit -m 'Prepare for Render deployment'"
echo ""
echo "3️⃣  Create GitHub repository:"
echo "   - Go to https://github.com/new"
echo "   - Name: expobeton-chatbot"
echo "   - Don't initialize with README"
echo "   - Copy the commands shown"
echo ""
echo "4️⃣  Push to GitHub:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/expobeton-chatbot.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "5️⃣  Deploy on Render:"
echo "   - Follow RENDER_DEPLOYMENT.md guide"
echo "   - Go to https://render.com"
echo "   - Connect GitHub repository"
echo ""
echo "======================================================"
