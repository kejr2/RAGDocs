#!/bin/bash
# Setup script for testing environment

echo "🚀 Setting up test environment..."

# Check if virtual environment exists
if [ ! -d "test_venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv test_venv
fi

# Activate and install requests
echo "Installing requests..."
source test_venv/bin/activate
pip install --quiet requests

echo "✅ Test environment ready!"
echo ""
echo "To run tests:"
echo "  source test_venv/bin/activate"
echo "  python3 test_api.py"
echo ""
echo "Or use the bash script (no setup needed):"
echo "  ./test_api.sh"

