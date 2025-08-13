# PowerShell activation script for HWInfo TUI
param(
    [switch]$Help
)

if ($Help) {
    Write-Host @"
HWInfo TUI Activation Script

USAGE:
    .\activate.ps1 [-Help]

This script activates the virtual environment and provides helpful commands.

EXAMPLES:
    .\activate.ps1        # Activate environment
    .\activate.ps1 -Help  # Show this help
"@
    exit 0
}

# Check if virtual environment exists
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "✗ Virtual environment not found." -ForegroundColor Red
    Write-Host "Run setup first: .\setup.ps1" -ForegroundColor Yellow
    exit 1
}

# Check execution policy
$executionPolicy = Get-ExecutionPolicy
if ($executionPolicy -eq "Restricted") {
    Write-Host "⚠️  Warning: PowerShell execution policy is Restricted." -ForegroundColor Yellow
    Write-Host "You may need to run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
    Write-Host ""
}

# Activate virtual environment
Write-Host "⚡ Activating virtual environment..." -ForegroundColor Cyan
try {
    & "venv\Scripts\Activate.ps1"
    Write-Host "✓ Virtual environment activated!" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to activate virtual environment: $_" -ForegroundColor Red
    Write-Host "Try running: .\setup.ps1 -Force" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "🚀 Development environment ready!" -ForegroundColor Green
Write-Host ""
Write-Host "AVAILABLE COMMANDS:" -ForegroundColor Cyan
Write-Host "  hwinfo-tui --help                    Show application help" -ForegroundColor White
Write-Host "  hwinfo-tui list-sensors sensors.csv  List available sensors" -ForegroundColor White
Write-Host "  pytest                               Run tests" -ForegroundColor White
Write-Host "  pytest --cov=hwinfo_tui             Run tests with coverage" -ForegroundColor White
Write-Host "  black src/ tests/                    Format code" -ForegroundColor White
Write-Host "  ruff src/ tests/                     Lint code" -ForegroundColor White
Write-Host "  mypy src/hwinfo_tui/                 Type checking" -ForegroundColor White
Write-Host "  deactivate                           Exit virtual environment" -ForegroundColor White
Write-Host ""
Write-Host "QUICK TEST:" -ForegroundColor Cyan
Write-Host "  hwinfo-tui ai-docs\sensors.CSV ""Core Temperatures"" ""Total CPU Usage""" -ForegroundColor Yellow
Write-Host ""

# Check if sample data exists
if (Test-Path "ai-docs\sensors.CSV") {
    Write-Host "✓ Sample data found: ai-docs\sensors.CSV" -ForegroundColor Green
} else {
    Write-Host "⚠️  Sample data not found: ai-docs\sensors.CSV" -ForegroundColor Yellow
}

Write-Host ""