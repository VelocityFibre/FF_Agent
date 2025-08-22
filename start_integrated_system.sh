#!/bin/bash

echo "🚀 Starting FF_Agent Integrated System"
echo "======================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Load .env file if it exists
if [ -f ".env" ]; then
    echo "📋 Loading environment from .env file..."
    set -a
    source .env
    set +a
    
    # Map the variables from .env to expected names
    export DATABASE_URL="${NEON_DATABASE_URL:-$DATABASE_URL}"
    export GOOGLE_API_KEY="${GOOGLE_AI_STUDIO_API_KEY:-$GOOGLE_API_KEY}"
    
    # Also export individual Postgres components for Vanna
    export PGHOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:\/]*\).*/\1/p')
    export PGDATABASE=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
    export PGUSER=$(echo $DATABASE_URL | sed -n 's/.*:\/\/\([^:]*\).*/\1/p')
    export PGPASSWORD=$(echo $DATABASE_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\).*/\1/p')
    export PGPORT=5432
    
    echo "✅ Environment variables loaded from .env"
fi

# Check environment variables
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL not set"
    echo "   Please ensure .env file exists with NEON_DATABASE_URL"
    exit 1
fi

if [ -z "$GOOGLE_API_KEY" ]; then
    echo "❌ GOOGLE_API_KEY not set"
    exit 1
fi

echo "✅ Environment variables loaded"

# Check if Vanna model exists
if [ ! -f "ff_agent_vanna.py" ]; then
    echo "❌ Vanna model not found"
    exit 1
fi

# Check if vector store exists
if [ ! -f "vector_store_cached.py" ]; then
    echo "❌ Vector store not found"
    exit 1
fi

echo "✅ Components verified"

# Start the integrated API
echo ""
echo "🎯 Starting Integrated API on port 8000..."
echo "   Features enabled:"
echo "   ✅ Vanna AI SQL generation"
echo "   ✅ Vector search with semantic matching"
echo "   ✅ Query suggestions"
echo "   ✅ Feedback system"
echo "   ✅ Monitoring and analytics"
echo ""
echo "🌐 UI available at: http://localhost:3000"
echo "📊 API docs at: http://localhost:8000/docs"
echo ""

# Start the API
python api_integrated.py