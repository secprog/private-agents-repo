# Setup script for OpenMemory - automatically clones mem0 repository and copies API files
# Usage: .\setup-openmemory.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "OpenMemory Setup Script" -ForegroundColor Cyan
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
$TempClone = Join-Path $env:TEMP "mem0-clone"
$OpenMemoryApi = Join-Path $ScriptDir "api"

Write-Host "Step 1: Cloning mem0 repository..." -ForegroundColor Yellow
Write-Host ""

# Remove existing temp clone if it exists
if (Test-Path $TempClone) {
    Write-Host "Removing existing temporary clone..." -ForegroundColor Gray
    Remove-Item -Recurse -Force $TempClone -ErrorAction SilentlyContinue
}

# Clone the repository
try {
    git clone https://github.com/mem0ai/mem0.git $TempClone
    if ($LASTEXITCODE -ne 0) {
        throw "Git clone failed"
    }
} catch {
    Write-Host "ERROR: Failed to clone mem0 repository." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 2: Copying API files..." -ForegroundColor Yellow
Write-Host ""

# Check if api directory exists in the clone
$SourceApi = Join-Path $TempClone "openmemory\api"
if (-not (Test-Path $SourceApi)) {
    Write-Host "ERROR: openmemory/api directory not found in cloned repository." -ForegroundColor Red
    Remove-Item -Recurse -Force $TempClone -ErrorAction SilentlyContinue
    exit 1
}

# Create api directory if it doesn't exist
if (-not (Test-Path $OpenMemoryApi)) {
    New-Item -ItemType Directory -Path $OpenMemoryApi | Out-Null
}

# Copy files
Write-Host "Copying files from mem0/openmemory/api to openmemory/api..." -ForegroundColor Gray
try {
    Copy-Item -Path "$SourceApi\*" -Destination $OpenMemoryApi -Recurse -Force
} catch {
    Write-Host "ERROR: Failed to copy API files." -ForegroundColor Red
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
Write-Host "OpenMemory API files have been copied to: $OpenMemoryApi" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Set OPENAI_API_KEY in your .env file" -ForegroundColor White
Write-Host "2. Run: docker-compose up -d openmemory" -ForegroundColor White
Write-Host ""

