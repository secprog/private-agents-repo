@echo off
REM Setup script for CaviraOSS OpenMemory - automatically clones repository and copies backend files
REM Usage: setup-openmemory.cmd
REM See: https://github.com/CaviraOSS/OpenMemory

setlocal enabledelayedexpansion

echo ========================================
echo CaviraOSS OpenMemory Setup Script
echo ========================================
echo.

REM Check if git is available
where git >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Git is not installed or not in PATH.
    echo Please install Git from https://git-scm.com/
    exit /b 1
)

REM Set paths
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\"
set "TEMP_CLONE=%TEMP%\openmemory-cavira-clone"

echo Step 1: Cloning CaviraOSS OpenMemory repository...
echo.

REM Remove existing temp clone if it exists
if exist "%TEMP_CLONE%" (
    echo Removing existing temporary clone...
    rmdir /s /q "%TEMP_CLONE%" 2>nul
)

REM Clone the repository
git clone https://github.com/CaviraOSS/OpenMemory.git "%TEMP_CLONE%"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to clone CaviraOSS OpenMemory repository.
    exit /b 1
)

echo.
echo Step 2: Copying backend files...
echo.

REM Check if backend directory exists in the clone
if not exist "%TEMP_CLONE%\backend" (
    echo ERROR: backend directory not found in cloned repository.
    rmdir /s /q "%TEMP_CLONE%" 2>nul
    exit /b 1
)

REM Copy backend files directly to openmemory directory (not to a subfolder)
echo Copying files from OpenMemory/backend to openmemory/...
xcopy /E /I /Y "%TEMP_CLONE%\backend\*" "%SCRIPT_DIR%\" >nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to copy backend files.
    rmdir /s /q "%TEMP_CLONE%" 2>nul
    exit /b 1
)

echo.
echo Step 3: Cleaning up temporary files...
echo.

REM Remove the temporary clone
rmdir /s /q "%TEMP_CLONE%" 2>nul

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo CaviraOSS OpenMemory backend files have been copied to: %SCRIPT_DIR%
echo.
echo Next steps:
echo 1. Set required environment variables in your .env file (check CaviraOSS OpenMemory docs)
echo 2. Run: docker-compose up -d openmemory
echo.
echo For more information, see: https://github.com/CaviraOSS/OpenMemory
echo.
pause
