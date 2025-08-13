# PowerShell test script for HWInfo TUI
param(
    [string]$TestPath = "",
    [switch]$Coverage,
    [switch]$Verbose,
    [switch]$Watch,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
HWInfo TUI Test Script

USAGE:
    .\test.ps1 [TestPath] [-Coverage] [-Verbose] [-Watch] [-Help]

PARAMETERS:
    TestPath    Specific test file or directory to run (optional)
    -Coverage   Run tests with coverage report
    -Verbose    Run tests with verbose output
    -Watch      Run tests in watch mode (requires pytest-xdist)
    -Help       Show this help message

EXAMPLES:
    .\test.ps1                           # Run all tests
    .\test.ps1 -Coverage                 # Run with coverage
    .\test.ps1 tests\test_sensors.py     # Run specific test file
    .\test.ps1 -Verbose                  # Run with verbose output
    .\test.ps1 -Coverage -Verbose        # Run with coverage and verbose
"@
    exit 0
}

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "⚠️  Virtual environment not activated." -ForegroundColor Yellow
    Write-Host "Run: .\activate.ps1" -ForegroundColor Cyan
    Write-Host ""
    
    # Try to activate automatically
    if (Test-Path "venv\Scripts\Activate.ps1") {
        Write-Host "🔄 Attempting to activate virtual environment..." -ForegroundColor Cyan
        & "venv\Scripts\Activate.ps1"
    } else {
        Write-Host "✗ Virtual environment not found. Run: .\setup.ps1" -ForegroundColor Red
        exit 1
    }
}

# Build pytest command
$pytestArgs = @()

if ($TestPath) {
    $pytestArgs += $TestPath
}

if ($Coverage) {
    $pytestArgs += "--cov=hwinfo_tui"
    $pytestArgs += "--cov-report=html"
    $pytestArgs += "--cov-report=term-missing"
}

if ($Verbose) {
    $pytestArgs += "-v"
}

if ($Watch) {
    $pytestArgs += "-f"  # pytest-xdist watch mode
}

# Run tests
Write-Host "🧪 Running tests..." -ForegroundColor Cyan
if ($pytestArgs.Count -gt 0) {
    Write-Host "Command: pytest $($pytestArgs -join ' ')" -ForegroundColor Gray
    & pytest @pytestArgs
} else {
    & pytest
}

$exitCode = $LASTEXITCODE

# Results
Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "✅ All tests passed!" -ForegroundColor Green
    
    if ($Coverage) {
        Write-Host ""
        Write-Host "📊 Coverage report generated:" -ForegroundColor Cyan
        Write-Host "  HTML: htmlcov\index.html" -ForegroundColor White
        
        # Try to open coverage report
        if (Test-Path "htmlcov\index.html") {
            $response = Read-Host "Open coverage report in browser? (y/N)"
            if ($response -eq "y" -or $response -eq "Y") {
                Start-Process "htmlcov\index.html"
            }
        }
    }
} else {
    Write-Host "❌ Some tests failed!" -ForegroundColor Red
    Write-Host "Exit code: $exitCode" -ForegroundColor Gray
}

Write-Host ""
exit $exitCode