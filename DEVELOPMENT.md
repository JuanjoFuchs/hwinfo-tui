# Development Guide

## Quick Start

### Windows
```bash
# Clone and setup
git clone https://github.com/hwinfo-tui/hwinfo-tui.git
cd hwinfo-tui

# Command Prompt
setup.bat

# PowerShell (recommended)
.\setup.ps1

# Daily development
activate.bat       # Command Prompt
.\activate.ps1     # PowerShell

hwinfo-tui --help
```

### Linux/macOS
```bash
# Clone and setup  
git clone https://github.com/hwinfo-tui/hwinfo-tui.git
cd hwinfo-tui
./setup.sh

# Daily development
source ./activate.sh
hwinfo-tui --help
```

## Virtual Environment

This project **requires** a virtual environment to isolate dependencies. The setup scripts automatically create and configure it.

### Manual Virtual Environment Setup

If you prefer to set up manually:

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"
```

### Virtual Environment Structure

```
hwinfo-tui/
├── venv/                 # Virtual environment (git-ignored)
│   ├── Scripts/          # Windows executables
│   ├── bin/              # Unix executables  
│   ├── lib/              # Python packages
│   └── pyvenv.cfg        # Environment config
├── setup.bat             # Windows setup script
├── setup.sh              # Unix setup script
├── activate.bat          # Windows quick activation
└── activate.sh           # Unix quick activation
```

## Development Workflow

### 1. Environment Setup
```bash
# First time setup
./setup.sh  # or setup.bat on Windows

# Daily activation
source ./activate.sh  # or activate.bat on Windows
```

### 2. Running the Application
```bash
# With virtual environment active
hwinfo-tui --help
hwinfo-tui ai-docs/sensors.CSV "CPU Temperature" "GPU Temperature"
```

### 3. Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=hwinfo_tui

# Run specific test file
pytest tests/test_sensors.py

# Run with verbose output
pytest -v

# PowerShell enhanced testing
.\test.ps1                    # Run all tests
.\test.ps1 -Coverage          # Run with coverage
.\test.ps1 -Verbose           # Run with verbose output
.\test.ps1 tests\test_sensors.py  # Run specific test
```

### 4. Code Quality
```bash
# Format code
black src/ tests/

# Lint code  
ruff src/ tests/

# Type checking
mypy src/hwinfo_tui/
```

### 5. Development Dependencies

The project includes development dependencies in `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0", 
    "black>=22.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
    "pre-commit>=2.20.0",
]
```

## Project Structure

```
hwinfo-tui/
├── src/hwinfo_tui/           # Main package
│   ├── data/                 # Data models and CSV handling
│   ├── display/              # UI components (charts, tables)
│   ├── utils/                # Utilities (stats, units, config)
│   ├── cli.py                # CLI interface  
│   └── main.py               # Application entry point
├── tests/                    # Test suite
├── config.toml               # Default configuration
├── pyproject.toml            # Package configuration
├── setup.bat/.sh/.ps1        # Setup scripts (Batch/Shell/PowerShell)
├── activate.bat/.sh/.ps1     # Quick activation scripts
└── test.ps1                  # Enhanced PowerShell test runner
```

## Configuration

The project uses `pyproject.toml` for all configuration:

- **Package metadata**: name, version, dependencies
- **Build system**: setuptools configuration  
- **Development tools**: black, ruff, mypy, pytest settings
- **Entry points**: CLI command registration

## Testing with Real Data

Use the included sample CSV file for testing:

```bash
# List available sensors
hwinfo-tui list-sensors ai-docs/sensors.CSV

# Test temperature monitoring
hwinfo-tui ai-docs/sensors.CSV "Core Temperatures (avg)" "CPU Package"

# Test mixed units
hwinfo-tui ai-docs/sensors.CSV "Total CPU Usage" "Core Temperatures (avg)"
```

## Debugging

Enable debug logging:

```bash
# Set environment variable
export HWINFO_TUI_LOG_LEVEL=DEBUG  # Linux/macOS
set HWINFO_TUI_LOG_LEVEL=DEBUG     # Windows

# Run with debug output
hwinfo-tui ai-docs/sensors.CSV "CPU Temperature" 2>debug.log
```

## Performance Testing

Monitor resource usage:

```bash
# Memory usage
python -m memory_profiler src/hwinfo_tui/main.py

# CPU usage  
python -m cProfile -o profile.stats src/hwinfo_tui/main.py
```

## Contributing

1. **Fork** the repository
2. **Create** a feature branch from `main`
3. **Setup** development environment with `setup.sh`/`setup.bat`
4. **Make** your changes
5. **Test** thoroughly with `pytest`
6. **Format** code with `black` and `ruff`
7. **Submit** a pull request

### Pre-commit Hooks

Setup pre-commit hooks for automatic code quality:

```bash
# Install pre-commit
pre-commit install

# Run on all files
pre-commit run --all-files
```

## Common Issues

### Virtual Environment Not Found
```bash
# Delete and recreate
rm -rf venv  # Linux/macOS
rmdir /s venv  # Windows

# Run setup again
./setup.sh  # or setup.bat
```

### Import Errors
```bash
# Ensure virtual environment is active
which python  # Should show venv path

# Reinstall in development mode
pip install -e .
```

### Permission Errors (Unix)
```bash
# Make scripts executable
chmod +x setup.sh activate.sh
```

## Release Process

1. Update version in `src/hwinfo_tui/__init__.py`
2. Update `CHANGELOG.md`
3. Run full test suite: `pytest`
4. Build package: `python -m build`
5. Test installation: `pip install dist/hwinfo_tui-*.whl`
6. Create git tag: `git tag v1.0.0`
7. Push to repository: `git push --tags`