#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Set environment variables
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Run the server
python tts_websocket_server.py 

# Wait for user input before closing
read -p "Press Enter to close..." 