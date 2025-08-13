@echo off
echo Setting up HWInfo TUI development environment...

:: Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

:: Create virtual environment
echo Creating virtual environment...
python -m venv venv

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

:: Install project in development mode
echo Installing HWInfo TUI in development mode...
pip install -e .

:: Install development dependencies
echo Installing development dependencies...
pip install -e ".[dev]"

echo.
echo ✅ Setup complete!
echo.
echo To activate the virtual environment:
echo   venv\Scripts\activate
echo.
echo To run HWInfo TUI:
echo   hwinfo-tui --help
echo.
echo To run tests:
echo   pytest
echo.
pause