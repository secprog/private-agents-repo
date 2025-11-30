# Setup script for CaviraOSS OpenMemory - automatically clones repository and copies backend files
# Usage: .\setup-openmemory.ps1
# See: https://github.com/CaviraOSS/OpenMemory

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CaviraOSS OpenMemory Setup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if git is available
try {
    $null = Get-Command git -ErrorAction Stop
} catch {
    Write-Host "ERROR: Git is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Git from https://git-scm.com/" -ForegroundColor Red
    exit 1
}

# Set paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$TempClone = Join-Path $env:TEMP "openmemory-cavira-clone"

Write-Host "Step 1: Cloning CaviraOSS OpenMemory repository..." -ForegroundColor Yellow
Write-Host ""

# Remove existing temp clone if it exists
if (Test-Path $TempClone) {
    Write-Host "Removing existing temporary clone..." -ForegroundColor Gray
    Remove-Item -Recurse -Force $TempClone -ErrorAction SilentlyContinue
}

# Clone the repository
try {
    git clone https://github.com/CaviraOSS/OpenMemory.git $TempClone
    if ($LASTEXITCODE -ne 0) {
        throw "Git clone failed"
    }
} catch {
    Write-Host "ERROR: Failed to clone CaviraOSS OpenMemory repository." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 2: Copying backend files..." -ForegroundColor Yellow
Write-Host ""

# Check if backend directory exists in the clone
$SourceBackend = Join-Path $TempClone "backend"
if (-not (Test-Path $SourceBackend)) {
    Write-Host "ERROR: backend directory not found in cloned repository." -ForegroundColor Red
    Remove-Item -Recurse -Force $TempClone -ErrorAction SilentlyContinue
    exit 1
}

# Copy backend files directly to openmemory directory (not to a subfolder)
Write-Host "Copying files from OpenMemory/backend to openmemory/..." -ForegroundColor Gray
try {
    Copy-Item -Path "$SourceBackend\*" -Destination $ScriptDir -Recurse -Force
} catch {
    Write-Host "ERROR: Failed to copy backend files." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Remove-Item -Recurse -Force $TempClone -ErrorAction SilentlyContinue
    exit 1
}

Write-Host ""
Write-Host "Step 3: Cleaning up temporary files..." -ForegroundColor Yellow
Write-Host ""

# Remove the temporary clone
Remove-Item -Recurse -Force $TempClone -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "CaviraOSS OpenMemory backend files have been copied to: $ScriptDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Set required environment variables in your .env file (check CaviraOSS OpenMemory docs)" -ForegroundColor White
Write-Host "2. Run: docker-compose up -d openmemory" -ForegroundColor White
Write-Host ""
Write-Host "For more information, see: https://github.com/CaviraOSS/OpenMemory" -ForegroundColor Cyan
Write-Host ""
