#!/bin/bash

echo "Setting up HWInfo TUI development environment..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "Error: Python not found. Please install Python 3.8 or higher."
        exit 1
    fi
    PYTHON=python
else
    PYTHON=python3
fi

# Check Python version
PYTHON_VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python $REQUIRED_VERSION or higher required. Found: $PYTHON_VERSION"
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
$PYTHON -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install project in development mode
echo "Installing HWInfo TUI in development mode..."
pip install -e .

# Install development dependencies
echo "Installing development dependencies..."
pip install -e ".[dev]"

echo ""
echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "To run HWInfo TUI:"
echo "  hwinfo-tui --help"
echo ""
echo "To run tests:"
echo "  pytest"
echo ""