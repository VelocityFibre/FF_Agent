#!/bin/bash

# FF_Agent Startup Script
# This script starts all components needed for FF_Agent

echo "=========================================="
echo "     FF_Agent - Starting All Services     "
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo -e "${GREEN}✓ Virtual environment found${NC}"
    source venv/bin/activate
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${RED}✗ .env file not found!${NC}"
    echo "Creating from template..."
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env with your credentials and restart${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Environment variables loaded${NC}"
fi

# Check for Firebase credentials
if [ -f "firebase-credentials.json" ]; then
    echo -e "${GREEN}✓ Firebase credentials found${NC}"
else
    echo -e "${YELLOW}⚠ Firebase credentials not found (Firebase queries disabled)${NC}"
fi

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# Kill any existing processes
echo -e "\n${YELLOW}Stopping any existing services...${NC}"
pkill -f "python api.py" 2>/dev/null
pkill -f "python3 -m http.server 3000" 2>/dev/null
sleep 2

# Start API server
echo -e "\n${GREEN}Starting API server on port 8000...${NC}"
source venv/bin/activate
python api.py &
API_PID=$!

# Wait for API to start
echo "Waiting for API to start..."
for i in {1..10}; do
    if curl -s http://localhost:8000 > /dev/null; then
        echo -e "${GREEN}✓ API server started successfully${NC}"
        break
    fi
    sleep 1
done

# Start UI server
echo -e "\n${GREEN}Starting UI server on port 3000...${NC}"
cd ui
python3 -m http.server 3000 > /dev/null 2>&1 &
UI_PID=$!
cd ..

# Wait a moment for UI to start
sleep 2
if check_port 3000; then
    echo -e "${GREEN}✓ UI server started successfully${NC}"
else
    echo -e "${RED}✗ UI server failed to start${NC}"
fi

# Display status
echo -e "\n=========================================="
echo -e "${GREEN}     FF_Agent is running!${NC}"
echo -e "=========================================="
echo ""
echo "Services:"
echo "  📡 API: http://localhost:8000"
echo "  🌐 UI:  http://localhost:3000"
echo "  📚 Docs: http://localhost:8000/docs"
echo ""
echo "Process IDs:"
echo "  API PID: $API_PID"
echo "  UI PID:  $UI_PID"
echo ""
echo -e "${YELLOW}To stop all services, run: ./stop.sh${NC}"
echo -e "${GREEN}Opening browser...${NC}"

# Try to open browser
if command -v xdg-open > /dev/null; then
    xdg-open http://localhost:3000 2>/dev/null &
elif command -v open > /dev/null; then
    open http://localhost:3000 2>/dev/null &
fi

# Keep script running and show logs
echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}\n"
echo "API Logs:"
echo "---------"

# Trap Ctrl+C to cleanup
trap cleanup INT

cleanup() {
    echo -e "\n${YELLOW}Stopping services...${NC}"
    kill $API_PID 2>/dev/null
    kill $UI_PID 2>/dev/null
    pkill -f "python api.py" 2>/dev/null
    pkill -f "python3 -m http.server 3000" 2>/dev/null
    echo -e "${GREEN}Services stopped.${NC}"
    exit 0
}

# Wait and show API logs
wait $API_PID