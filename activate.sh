#!/bin/bash
# Quick activation script for Unix-like systems

if [ ! -f "venv/bin/activate" ]; then
    echo "Virtual environment not found. Run ./setup.sh first."
    exit 1
fi

echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "Or source this script:"
echo "  source ./activate.sh"
echo ""
echo "Available commands after activation:"
echo "  hwinfo-tui --help    - Show help"
echo "  pytest               - Run tests"
echo "  deactivate           - Exit virtual environment"
echo ""

# If sourced, activate the environment
if [ "${BASH_SOURCE[0]}" != "${0}" ]; then
    source venv/bin/activate
    echo "Virtual environment activated!"
fi