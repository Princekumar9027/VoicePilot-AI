$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKEND = Join-Path $ROOT "backend"
$FRONTEND = Join-Path $ROOT "frontend"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "        VoicePilot AI - STARTING" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# Check Node.js
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Node.js/npm is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# Create Python virtual environment if missing
if (-not (Test-Path (Join-Path $BACKEND ".venv"))) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv (Join-Path $BACKEND ".venv")
}

$PYTHON = Join-Path $BACKEND ".venv\Scripts\python.exe"

# Install backend dependencies if needed
Write-Host "Checking backend dependencies..." -ForegroundColor Yellow
& $PYTHON -m pip install -r (Join-Path $BACKEND "requirements.txt")

# Install frontend dependencies if node_modules is missing
if (-not (Test-Path (Join-Path $FRONTEND "node_modules"))) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location $FRONTEND
    npm install
    Pop-Location
}

# Start backend
Write-Host ""
Write-Host "Starting FastAPI backend..." -ForegroundColor Green

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$BACKEND'; & '$PYTHON' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
)

Start-Sleep -Seconds 3

# Start frontend
Write-Host "Starting React frontend..." -ForegroundColor Green

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$FRONTEND'; npm run dev"
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VoicePilot AI is starting..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend : http://127.0.0.1:8000" -ForegroundColor White
Write-Host "API Docs: http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Two terminal windows have been opened." -ForegroundColor Yellow
Write-Host "Keep them open while using VoicePilot AI." -ForegroundColor Yellow