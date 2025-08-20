#!/bin/bash

# FF_Agent Stop Script
# Stops all FF_Agent services

echo "=========================================="
echo "     FF_Agent - Stopping All Services     "
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Kill API server
echo "Stopping API server..."
pkill -f "python api.py" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ API server stopped${NC}"
else
    echo -e "${RED}API server was not running${NC}"
fi

# Kill UI server
echo "Stopping UI server..."
pkill -f "python3 -m http.server 3000" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ UI server stopped${NC}"
else
    echo -e "${RED}UI server was not running${NC}"
fi

# Kill any uvicorn processes
pkill -f "uvicorn" 2>/dev/null

echo -e "\n${GREEN}All FF_Agent services stopped.${NC}"