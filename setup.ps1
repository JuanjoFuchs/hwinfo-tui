# PowerShell setup script for HWInfo TUI
param(
    [switch]$Force,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
HWInfo TUI Setup Script

USAGE:
    .\setup.ps1 [-Force] [-Help]

OPTIONS:
    -Force    Force recreation of virtual environment if it exists
    -Help     Show this help message

EXAMPLES:
    .\setup.ps1           # Normal setup
    .\setup.ps1 -Force    # Force recreate venv
"@
    exit 0
}

Write-Host "Setting up HWInfo TUI development environment..." -ForegroundColor Cyan

# Check execution policy
$executionPolicy = Get-ExecutionPolicy
if ($executionPolicy -eq "Restricted") {
    Write-Host "Warning: PowerShell execution policy is Restricted." -ForegroundColor Yellow
    Write-Host "You may need to run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
    Write-Host ""
}

# Check if Python is available
try {
    $pythonVersion = & python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    Write-Host "✓ Found Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Error: Python not found. Please install Python 3.8 or higher." -ForegroundColor Red
    Write-Host "Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Check Python version
try {
    $versionOutput = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1
    $version = [Version]$versionOutput
    $requiredVersion = [Version]"3.8"
    
    if ($version -lt $requiredVersion) {
        Write-Host "✗ Error: Python 3.8 or higher required. Found: $version" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Python version check passed: $version" -ForegroundColor Green
} catch {
    Write-Host "✗ Error checking Python version: $_" -ForegroundColor Red
    exit 1
}

# Handle existing virtual environment
if (Test-Path "venv") {
    if ($Force) {
        Write-Host "🗑️  Removing existing virtual environment..." -ForegroundColor Yellow
        Remove-Item -Path "venv" -Recurse -Force
    } else {
        Write-Host "Virtual environment already exists. Use -Force to recreate." -ForegroundColor Yellow
        Write-Host "To activate existing environment, run: .\activate.ps1" -ForegroundColor Cyan
        exit 0
    }
}

# Create virtual environment
Write-Host "📦 Creating virtual environment..." -ForegroundColor Cyan
try {
    & python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create virtual environment"
    }
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
} catch {
    Write-Host "✗ Error creating virtual environment: $_" -ForegroundColor Red
    exit 1
}

# Activate virtual environment
Write-Host "⚡ Activating virtual environment..." -ForegroundColor Cyan
try {
    & "venv\Scripts\Activate.ps1"
    Write-Host "✓ Virtual environment activated" -ForegroundColor Green
} catch {
    Write-Host "✗ Error activating virtual environment: $_" -ForegroundColor Red
    exit 1
}

# Upgrade pip
Write-Host "⬆️  Upgrading pip..." -ForegroundColor Cyan
try {
    & python -m pip install --upgrade pip --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to upgrade pip"
    }
    Write-Host "✓ Pip upgraded" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Warning: Failed to upgrade pip: $_" -ForegroundColor Yellow
}

# Install project in development mode
Write-Host "🔧 Installing HWInfo TUI in development mode..." -ForegroundColor Cyan
try {
    & pip install -e . --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install HWInfo TUI"
    }
    Write-Host "✓ HWInfo TUI installed" -ForegroundColor Green
} catch {
    Write-Host "✗ Error installing HWInfo TUI: $_" -ForegroundColor Red
    exit 1
}

# Install development dependencies
Write-Host "🛠️  Installing development dependencies..." -ForegroundColor Cyan
try {
    & pip install -e ".[dev]" --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install development dependencies"
    }
    Write-Host "✓ Development dependencies installed" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Warning: Failed to install development dependencies: $_" -ForegroundColor Yellow
}

# Success message
Write-Host ""
Write-Host "🎉 Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "  To activate the virtual environment:"
Write-Host "    .\activate.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "  To run HWInfo TUI:"
Write-Host "    hwinfo-tui --help" -ForegroundColor Yellow
Write-Host ""
Write-Host "  To run tests:"
Write-Host "    pytest" -ForegroundColor Yellow
Write-Host ""
Write-Host "  To test with sample data:"
Write-Host "    hwinfo-tui ai-docs\sensors.CSV ""Core Temperatures"" ""Total CPU Usage""" -ForegroundColor Yellow
Write-Host ""