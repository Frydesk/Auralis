#!/bin/bash

# Exit on error
set -e

echo "🚀 Starting Auralis TTS WebSocket Server Setup..."

# Check if Python 3.10 is installed
if ! command -v python3.10 &> /dev/null; then
    echo "❌ Python 3.10 is not installed. Please install Python 3.10 first."
    exit 1
fi

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y portaudio19-dev

# Create and activate virtual environment
echo "📦 Creating virtual environment..."
python3.10 -m venv venv

# Activate environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install required packages
echo "📥 Installing required packages..."
pip install --upgrade pip
pip install websockets
pip install sounddevice
pip install numpy
pip install auralis
pip install torchaudio

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p models
mkdir -p audio_samples

# Download default speaker file if not exists
if [ ! -f "audio_samples/default_speaker.wav" ]; then
    echo "🎵 Please place your default speaker WAV file in audio_samples/default_speaker.wav"
    echo "   You can use any WAV file for voice cloning."
fi

# Update the server configuration
echo "⚙️ Updating server configuration..."
sed -i "s|DEFAULT_SPEAKER_FILE = \".*\"|DEFAULT_SPEAKER_FILE = \"$(pwd)/audio_samples/default_speaker.wav\"|" tts_websocket_server.py

# Make scripts executable
echo "🔑 Making scripts executable..."
chmod +x run_server.sh
chmod +x setup.sh

echo """
✅ Setup completed successfully!

To start the server:
1. Activate the environment: source venv/bin/activate
2. Run the server: ./run_server.sh

The server will be available at ws://localhost:9100

Note: Make sure to place your default speaker WAV file in:
    $(pwd)/audio_samples/default_speaker.wav
"""

# Print system information
echo """
📊 System Information:
Python version: $(python --version)
CUDA available: $(python -c "import torch; print(torch.cuda.is_available())")
GPU device: $(python -c "import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No GPU available')")
""" 

read -p "Press Enter to close..." 