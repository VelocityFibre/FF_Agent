#!/bin/bash
# Start script for enhanced API with prompt improvements

echo "🚀 Starting FF_Agent Enhanced API with Prompt Improvements"
echo "=========================================================="

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "✅ Virtual environment found"
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please create .env with your credentials:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Check if prompt_improvements.py exists
if [ ! -f "prompt_improvements.py" ]; then
    echo "❌ prompt_improvements.py not found!"
    echo "The enhanced prompt system is missing."
    exit 1
fi

echo ""
echo "✅ All checks passed. Starting API..."
echo ""
echo "API will be available at: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================================="
echo ""

# Start the API
python3 api_enhanced.py