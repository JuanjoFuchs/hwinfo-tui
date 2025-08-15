#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build script for HWInfo TUI - creates PyPI packages and Windows executable

.DESCRIPTION
    This script builds the HWInfo TUI project following the packaging specification.
    It creates both PyPI packages (sdist + wheel) and a Windows standalone executable.

.PARAMETER Clean
    Clean dist/ directory before building

.PARAMETER SkipTests
    Skip running tests before building

.PARAMETER SkipExe
    Skip building Windows executable

.PARAMETER Publish
    Publish to PyPI (requires TWINE_USERNAME and TWINE_PASSWORD environment variables)

.EXAMPLE
    .\build.ps1
    Build packages and executable

.EXAMPLE
    .\build.ps1 -Clean -Publish
    Clean, build, and publish to PyPI
#>

[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$SkipTests,
    [switch]$SkipExe,
    [switch]$Publish
)

# Error handling
$ErrorActionPreference = "Stop"

# Colors for output
function Write-Info { param($Message) Write-Host "[INFO] $Message" -ForegroundColor Green }
function Write-Warning { param($Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }

try {
    Write-Host "HWInfo TUI Build Script" -ForegroundColor Cyan
    Write-Host "======================" -ForegroundColor Cyan
    
    # Check if we're in a virtual environment
    if (-not $env:VIRTUAL_ENV) {
        Write-Warning "No virtual environment detected. Activating..."
        if (Test-Path ".\activate.ps1") {
            & ".\activate.ps1"
            Write-Info "Virtual environment activated"
        } else {
            Write-Error "No activate.ps1 found. Please activate your virtual environment first."
            exit 1
        }
    } else {
        Write-Info "Virtual environment: $env:VIRTUAL_ENV"
    }
    
    # Get version from pyproject.toml
    $pyproj = Get-Content pyproject.toml -Raw
    if ($pyproj -match 'version\s*=\s*"([^"]+)"') {
        $version = $Matches[1]
        Write-Info "Building version: $version"
    } else {
        Write-Error "Could not find version in pyproject.toml"
        exit 1
    }
    
    # Clean dist directory if requested
    if ($Clean -and (Test-Path "dist")) {
        Write-Info "Cleaning dist/ directory..."
        Remove-Item -Recurse -Force "dist"
    }
    
    # Install/upgrade build dependencies
    Write-Info "Installing build dependencies..."
    python -m pip install --upgrade pip
    pip install -e .[dev]
    
    # Run tests unless skipped
    if (-not $SkipTests) {
        Write-Info "Running linting..."
        ruff check .
        if ($LASTEXITCODE -ne 0) { throw "Linting failed" }
        
        Write-Info "Running type checking..."
        mypy src
        if ($LASTEXITCODE -ne 0) { throw "Type checking failed" }
        
        Write-Info "Running tests..."
        pytest -q
        if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
    } else {
        Write-Warning "Skipping tests"
    }
    
    # Build Python packages
    Write-Info "Building Python packages (sdist + wheel)..."
    python -m build
    if ($LASTEXITCODE -ne 0) { throw "Package build failed" }
    
    # Check package metadata
    Write-Info "Checking package metadata..."
    python -m twine check dist/*.whl dist/*.tar.gz
    if ($LASTEXITCODE -ne 0) { throw "Package check failed" }
    
    # Build Windows executable unless skipped
    if (-not $SkipExe) {
        Write-Info "Building Windows executable..."
        pyinstaller --name hwinfo-tui --onefile --console --paths src src/hwinfo_tui/main.py
        if ($LASTEXITCODE -ne 0) { throw "Executable build failed" }
        
        # Rename executable with version
        $exeName = "hwinfo-tui-$version-windows-x64.exe"
        Rename-Item -Path "dist/hwinfo-tui.exe" -NewName $exeName
        Write-Info "Created executable: dist/$exeName"
        
        # Test executable
        Write-Info "Testing executable..."
        $exePath = "dist/$exeName"
        & $exePath --help | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Executable test failed" }
        & $exePath --version | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Executable version test failed" }
        Write-Info "Executable tests passed"
    } else {
        Write-Warning "Skipping executable build"
    }
    
    # List built artifacts
    Write-Info "Build artifacts:"
    Get-ChildItem dist/ | ForEach-Object {
        $size = if ($_.Length -gt 1MB) { "{0:N2} MB" -f ($_.Length / 1MB) } else { "{0:N0} KB" -f ($_.Length / 1KB) }
        Write-Host "  - $($_.Name) ($size)" -ForegroundColor Blue
    }
    
    # Publish to PyPI if requested
    if ($Publish) {
        Write-Info "Publishing to PyPI..."
        
        if (-not $env:TWINE_USERNAME) {
            Write-Error "TWINE_USERNAME environment variable not set"
            exit 1
        }
        if (-not $env:TWINE_PASSWORD) {
            Write-Error "TWINE_PASSWORD environment variable not set"
            exit 1
        }
        
        twine upload dist/*.whl dist/*.tar.gz
        if ($LASTEXITCODE -ne 0) { throw "PyPI upload failed" }
        Write-Info "Successfully published to PyPI"
    }
    
    Write-Host ""
    Write-Host "Build completed successfully!" -ForegroundColor Green
    Write-Host "Version: $version" -ForegroundColor Cyan
    
    if (-not $Publish) {
        Write-Host ""
        Write-Warning "To publish to PyPI, set TWINE_USERNAME and TWINE_PASSWORD then run:"
        Write-Host "  .\build.ps1 -Publish" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host ""
    Write-Error "Build failed: $_"
    exit 1
}