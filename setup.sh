#!/bin/bash
# Setup script for PDF Comparison Application

echo "=========================================="
echo "PDF Comparison Application Setup"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
echo "✓ Virtual environment created"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip
echo "✓ pip upgraded"
echo ""

# Install dependencies (note: --pre flag required for agent-framework)
echo "Installing dependencies..."
echo "Note: Installing agent-framework with --pre flag (required for preview)"
pip install --pre -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env file with your Azure credentials:"
    echo "   - AZURE_OPENAI_ENDPOINT"
    echo "   - AZURE_OPENAI_API_KEY"
    echo "   - AZURE_OPENAI_DEPLOYMENT_NAME"
    echo ""
else
    echo "✓ .env file already exists"
    echo ""
fi

# Verify input folder exists
if [ ! -d "input" ]; then
    echo "Creating input folder..."
    mkdir -p input
    echo "✓ input folder created"
    echo ""
fi

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Azure OpenAI credentials"
echo "2. Place two PDF files in the 'input' folder"
echo "3. Run: python main.py"
echo ""
