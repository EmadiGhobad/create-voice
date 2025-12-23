#!/bin/bash

# StyleTTS2 Local Setup Script for macOS

set -e

echo "Setting up StyleTTS2 locally..."

# Check if StyleTTS2 directory exists
if [ ! -d "StyleTTS2" ]; then
    echo "Cloning StyleTTS2 repository..."
    git clone https://github.com/yl4579/StyleTTS2.git
else
    echo "StyleTTS2 directory already exists, skipping clone..."
fi

cd StyleTTS2

# Install system dependencies (macOS)
echo "Installing system dependencies..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Please install Homebrew first: https://brew.sh"
        exit 1
    fi
    
    # Install espeak-ng via Homebrew
    if ! command -v espeak-ng &> /dev/null; then
        echo "Installing espeak-ng..."
        brew install espeak-ng
    else
        echo "espeak-ng already installed"
    fi
else
    echo "This script is designed for macOS. For other systems, please install espeak-ng manually."
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Upgrade phonemizer
echo "Upgrading phonemizer..."
pip install --upgrade phonemizer

# Download NLTK data
echo "Downloading NLTK punkt data..."
python -c "import nltk; nltk.download('punkt_tab', quiet=True)"

# Create Demo directory if it doesn't exist
if [ ! -d "Demo" ]; then
    mkdir -p Demo
    echo "Created Demo directory. Please download reference_audio.zip from:"
    echo "https://huggingface.co/yl4579/StyleTTS2-LibriTTS/resolve/main/reference_audio.zip"
    echo "and extract it to the Demo folder."
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Download reference_audio.zip from:"
echo "   https://huggingface.co/yl4579/StyleTTS2-LibriTTS/resolve/main/reference_audio.zip"
echo "2. Extract it to StyleTTS2/Demo/reference_audio/"
echo "3. Download the model checkpoint and place it in the appropriate location"
echo "4. Run the inference script: python inference_local.py"

