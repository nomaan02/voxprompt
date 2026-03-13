#!/usr/bin/env bash
set -e

echo "=== VoxPrompt Setup ==="
echo

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install PyTorch with CUDA first
echo "Installing PyTorch with CUDA support..."
pip install torch --index-url https://download.pytorch.org/whl/cu128

# Install remaining dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo
echo "=== Setup complete ==="
echo
echo "To run VoxPrompt:"
echo "  source .venv/bin/activate"
echo "  python -m voxprompt.main"
