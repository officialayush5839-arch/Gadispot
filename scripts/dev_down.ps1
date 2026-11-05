# ==============================================================================
# Gadispot Developer Local Stack Teardown Script (PowerShell / Windows)
# Gracefully stops Docker Compose containers with optional persistent volume purge.
# Usage:
#   .\scripts\dev_down.ps1              # Stop containers gracefully
#   .\scripts\dev_down.ps1 -Volumes     # Stop containers and wipe volumes
#   .\scripts\dev_down.ps1 -v           # Stop containers and wipe volumes
# ==============================================================================

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [switch]$Volumes,

    [Parameter(Mandatory=$false)]
    [Alias("v")]
    [switch]$v
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

Set-Location $RepoRoot

$WipeVolumes = $Volumes -or $v

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "          Stopping Gadispot Local Engineering Environment             " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

if ($WipeVolumes) {
    Write-Host "[!] Stopping containers and PURGING persistent volumes..." -ForegroundColor Yellow
    docker compose down -v --remove-orphans
    Write-Host "[✓] Containers stopped and volumes wiped successfully." -ForegroundColor Green
} else {
    Write-Host "[+] Stopping containers gracefully (preserving data volumes)..." -ForegroundColor Yellow
    docker compose down --remove-orphans
    Write-Host "[✓] Containers stopped. (Data volumes preserved; pass -Volumes or -v to wipe)." -ForegroundColor Green
}
Write-Host "======================================================================" -ForegroundColor Cyan
