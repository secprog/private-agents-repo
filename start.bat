@echo off
echo ====================================
echo   Agent Platform - Quick Start
echo ====================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not in PATH
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM Check if Docker is running
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running
    echo Please start Docker Desktop
    pause
    exit /b 1
)

echo [1/5] Checking environment configuration...
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo IMPORTANT: Please edit .env file with your API keys before continuing!
    notepad .env
    pause
)

echo [2/5] Generating SSL certificates...
if not exist nginx\ssl (
    mkdir nginx\ssl
)

REM Generate SSL certificates using PowerShell
powershell -Command "& {if (!(Test-Path backend\cert.pem)) { Write-Host 'Generating certificates...'; docker run --rm -v ${PWD}:/work -w /work alpine/openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem -subj '/C=US/ST=State/L=City/O=Organization/CN=localhost' }}"

echo [3/5] Building Docker images...
docker-compose build

echo [4/5] Starting services...
docker-compose up -d

echo [5/5] Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo.
echo ====================================
echo   Agent Platform is running!
echo ====================================
echo.
echo Frontend:           http://localhost:3000
echo Orchestrator API:   https://localhost:8000
echo CyberSecurity:      https://localhost:8001
echo DevOps Agent:       https://localhost:8002
echo.
echo To view logs:       docker-compose logs -f
echo To stop services:   docker-compose down
echo.

REM Open browser
start http://localhost:3000

echo Press any key to view logs (Ctrl+C to exit)...
pause >nul
docker-compose logs -f
