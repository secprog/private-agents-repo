@echo off
REM Setup script for OpenMemory - automatically clones mem0 repository and copies API files
REM Usage: setup-openmemory.cmd

setlocal enabledelayedexpansion

echo ========================================
echo OpenMemory Setup Script
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
set "TEMP_CLONE=%TEMP%\mem0-clone"
set "OPENMEMORY_API=%SCRIPT_DIR%api"

echo Step 1: Cloning mem0 repository...
echo.

REM Remove existing temp clone if it exists
if exist "%TEMP_CLONE%" (
    echo Removing existing temporary clone...
    rmdir /s /q "%TEMP_CLONE%" 2>nul
)

REM Clone the repository
git clone https://github.com/mem0ai/mem0.git "%TEMP_CLONE%"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to clone mem0 repository.
    exit /b 1
)

echo.
echo Step 2: Copying API files...
echo.

REM Check if api directory exists in the clone
if not exist "%TEMP_CLONE%\openmemory\api" (
    echo ERROR: openmemory/api directory not found in cloned repository.
    rmdir /s /q "%TEMP_CLONE%" 2>nul
    exit /b 1
)

REM Create api directory if it doesn't exist
if not exist "%OPENMEMORY_API%" mkdir "%OPENMEMORY_API%"

REM Copy files (exclude .git and other unnecessary files)
echo Copying files from mem0/openmemory/api to openmemory/api...
xcopy /E /I /Y "%TEMP_CLONE%\openmemory\api\*" "%OPENMEMORY_API%\" >nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to copy API files.
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
echo OpenMemory API files have been copied to: %OPENMEMORY_API%
echo.
echo Next steps:
echo 1. Set OPENAI_API_KEY in your .env file
echo 2. Run: docker-compose up -d openmemory
echo.
pause

