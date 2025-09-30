@echo off
echo 🚀 Setting up shared virtual environment for agent platform...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python is not installed or not in PATH
    echo Please install Python 3.11+ and try again
    pause
    exit /b 1
)

REM Run the setup script
python setup_simple_venv.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Setup completed successfully!
    echo.
    echo 📋 Next steps:
    echo   1. Activate virtual environment: activate.bat
    echo   2. Start services with: docker-compose up
    echo.
) else (
    echo.
    echo ❌ Setup failed! Please check the error messages above.
    echo.
)

pause
