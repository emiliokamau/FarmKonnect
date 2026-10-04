# Start FarmKonnect on Localhost
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Green
Write-Host "   Starting FarmKonnect on Localhost   " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $Root "backend"
$VenvDir = Join-Path $BackendDir "venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "Creating Python virtual environment in $VenvDir..." -ForegroundColor Yellow
    python -m venv $VenvDir
}

Write-Host "Checking dependencies..." -ForegroundColor Cyan
& $PythonExe -m pip install -r (Join-Path $BackendDir "requirements.txt") --quiet

Write-Host "Running database migrations..." -ForegroundColor Cyan
& $PythonExe (Join-Path $BackendDir "manage.py") migrate --noinput

Write-Host "Seeding initial reference data..." -ForegroundColor Cyan
& $PythonExe (Join-Path $BackendDir "manage.py") seed_data

Write-Host ""
Write-Host "FarmKonnect is starting at http://127.0.0.1:8000/" -ForegroundColor Green
Write-Host "Default login: 0701519479 / Admin1234" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server." -ForegroundColor Yellow
Write-Host ""

& $PythonExe (Join-Path $BackendDir "manage.py") runserver 127.0.0.1:8000
