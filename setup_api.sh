#!/bin/bash

echo "🔧 Setting up Celebrity Question API Server..."
echo ""

# Step 1: Upgrade pip
echo "📦 Step 1: Upgrading pip..."
python3 -m pip install --upgrade pip

# Step 2: Install wheel and setuptools
echo "📦 Step 2: Installing build tools..."
pip3 install --upgrade wheel setuptools

# Step 3: Install FastAPI dependencies
echo "📦 Step 3: Installing FastAPI dependencies..."
pip3 install -r api_requirements.txt

# Step 4: Install main dependencies
echo "📦 Step 4: Installing main dependencies..."
pip3 install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "  1. Edit .env file and add your CLAUDE_KEY"
echo "  2. Start the API server: python3 api_server.py"
echo ""
