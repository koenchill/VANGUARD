# Local Grafana Mission BI (no cloud).
#
# Usage:
#   .\scripts\run-grafana-local.ps1
#   .\scripts\run-grafana-local.ps1 -Rebuild
#   .\scripts\run-grafana-local.ps1 -Down

param(
    [switch]$ForceVenv,
    [switch]$Rebuild,
    [switch]$Down,
    [switch]$SkipBrowser
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot
$Compose = "analytics/grafana/local/docker-compose.yaml"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is required for Local Grafana."
}

if ($Down) {
    docker compose -f $Compose down -v
    Write-Host "# grafana-local: stopped"
    exit 0
}

$ensureArgs = @()
if ($ForceVenv) { $ensureArgs += "-Force" }
$Py = & "$PSScriptRoot\ensure-venv.ps1" @ensureArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:PYTHONPATH = "$RepoRoot"

# Refresh ingest report used to seed mart snapshot (best-effort).
Write-Host "# grafana-local: refresh Local ingest->Grafana evidence"
& $Py tools/demo_ingest_to_grafana.py | Out-Null

Write-Host "# grafana-local: prepare seed + dashboards"
& $Py tools/prepare_grafana_local.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($Rebuild) {
    Write-Host "# grafana-local: rebuild containers (fresh DB volume)"
    docker compose -f $Compose down -v
}

Write-Host "# grafana-local: starting Grafana on http://127.0.0.1:33000"
docker compose -f $Compose up -d
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Wait for Grafana HTTP
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:33000/api/health" -UseBasicParsing -TimeoutSec 3
        if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $ready) {
    docker compose -f $Compose logs --tail 80
    throw "Grafana did not become healthy on :33000"
}

Write-Host "# grafana-local: READY"
Write-Host "#   URL:      http://127.0.0.1:33000"
Write-Host "#   User:     admin"
Write-Host "#   Password: vanguard"
Write-Host "#   Open:     Mission BI folder -> Curation Pipeline Health (Local)"

if (-not $SkipBrowser) {
    Start-Process "http://127.0.0.1:33000/d/curation_health/curation-pipeline-health-local"
}

exit 0
