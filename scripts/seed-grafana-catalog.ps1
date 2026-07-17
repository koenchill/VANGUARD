# Seed Local Grafana Playlists / Library panels / Snapshots / Public dashboards
# with real Mission BI content (clears empty-state pages).
param(
    [string]$BaseUrl = "http://127.0.0.1:33000"
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "# Creating .venv first..."
    & ".\scripts\ensure-venv.ps1"
}

Write-Host "# Seeding Grafana catalog at $BaseUrl"
& ".\.venv\Scripts\python.exe" ".\tools\seed_grafana_local_catalog.py" --base-url $BaseUrl
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "# Done. Refresh:"
Write-Host "#   $BaseUrl/playlists"
Write-Host "#   $BaseUrl/library-panels"
Write-Host "#   $BaseUrl/dashboard/snapshots"
Write-Host "#   $BaseUrl/dashboard/public-dashboards"
