@echo off
:: Quick activation script for Windows
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
echo Virtual environment activated!
echo.
echo Available commands:
echo   hwinfo-tui --help    - Show help
echo   pytest               - Run tests  
echo   deactivate           - Exit virtual environment
echo.