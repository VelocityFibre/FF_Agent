#!/bin/bash

echo "Setting up FF_Agent environment..."

# Install system dependencies
echo "Installing Python venv..."
sudo apt install python3.13-venv python3-pip -y

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate and install packages
echo "Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

echo "Setup complete! Run the agent with:"
echo "  source venv/bin/activate"
echo "  python main.py"