# ==============================================================================
# Gadispot Developer Local Stack Startup Script (PowerShell / Windows)
# Automates environment initialization, container build/start, readiness polling,
# and Alembic database migration execution.
# ==============================================================================

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

Set-Location $RepoRoot

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "          Starting Gadispot Local Engineering Environment             " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Initialize environment configuration if absent
$EnvPath = Join-Path $RepoRoot ".env"
$EnvExamplePath = Join-Path $RepoRoot ".env.example"

if (-not (Test-Path $EnvPath)) {
    Write-Host "[+] Initializing .env configuration from .env.example..." -ForegroundColor Yellow
    Copy-Item $EnvExamplePath $EnvPath
    Write-Host "[✓] .env initialized successfully." -ForegroundColor Green
} else {
    Write-Host "[i] Using existing .env configuration." -ForegroundColor DarkGray
}

# 2. Build and launch Docker Compose services
Write-Host "[+] Building and launching Docker Compose services in background..." -ForegroundColor Yellow
docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Error "docker compose up failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

# 3. Wait for database and backend services to report healthy
Write-Host "[+] Waiting for services to attain HEALTHY state..." -ForegroundColor Yellow
$MaxAttempts = 30
$Attempt = 0
$BackendHealthy = $false

while ($Attempt -lt $MaxAttempts) {
    $Attempt++
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health/ready" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response -and $response.status -eq "READY") {
            $BackendHealthy = $true
            break
        }
    } catch {
        # Retry on connection failure or 503
    }

    Write-Host "    Attempt $Attempt/$MaxAttempts`: Backend readiness pending, retrying in 2s..." -ForegroundColor DarkGray
    Start-Sleep -Seconds 2
}

if (-not $BackendHealthy) {
    Write-Host "[!] Timed out waiting for backend service readiness. Checking container logs:" -ForegroundColor Red
    docker compose logs --tail 30 backend
    exit 1
}
Write-Host "[✓] Backend and dependent datastores (PostgreSQL + Redis) are HEALTHY." -ForegroundColor Green

# 4. Apply database migrations via Alembic inside backend container
Write-Host "[+] Applying latest database migrations (alembic upgrade head)..." -ForegroundColor Yellow
docker compose exec backend alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Error "Alembic database migration failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
Write-Host "[✓] Database schema is up to date." -ForegroundColor Green

# 5. Output Success Banner
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "         🚀 Gadispot Local Development Environment Ready!             " -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "  • Liveness Probe:     http://localhost:8000/health/live" -ForegroundColor White
Write-Host "  • Readiness Probe:    http://localhost:8000/health/ready" -ForegroundColor White
Write-Host "  • API Health Check:   http://localhost:8000/api/v1/health" -ForegroundColor White
Write-Host "  • Interactive Docs:   http://localhost:8000/docs" -ForegroundColor White
Write-Host "  • ReDoc Spec:         http://localhost:8000/redoc" -ForegroundColor White
Write-Host "  • PostgreSQL (PostGIS): localhost:5432 (DB: gadispot, User: postgres)" -ForegroundColor White
Write-Host "  • Redis Cache:        localhost:6379" -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "To shut down the stack gracefully, run: .\scripts\dev_down.ps1" -ForegroundColor Cyan
Write-Host "To shut down and wipe persistent volumes: .\scripts\dev_down.ps1 -Volumes" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Green
