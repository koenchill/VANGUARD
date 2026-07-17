# Stream live enterprise CDC-style events into Local Grafana (integrated-source assumption).
#
# Prerequisites: .\scripts\run-grafana-local.ps1
#
# Usage:
#   .\scripts\run-data-stream.ps1
#   .\scripts\run-data-stream.ps1 -Interval 1 -Count 30

param(
    [double]$Interval = 1.5,
    [int]$Count = 0,
    [switch]$ForceVenv,
    [switch]$SkipBrowser
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$running = docker ps --filter "name=vanguard-grafana-pg" --format "{{.Names}}"
if (-not $running) {
    Write-Host "# data-stream: starting Local Grafana/Postgres first"
    & "$PSScriptRoot\run-grafana-local.ps1" -SkipBrowser
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$ensureArgs = @()
if ($ForceVenv) { $ensureArgs += "-Force" }
$Py = & "$PSScriptRoot\ensure-venv.ps1" @ensureArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:PYTHONPATH = "$RepoRoot"

# Ensure live dashboard is present (copy already in repo; refresh provisioning scan)
Write-Host "# data-stream: open Grafana live dashboard (refresh 2s)"
Write-Host "#   http://127.0.0.1:33000/d/live_enterprise_stream"
Write-Host "#   login admin / vanguard"
Write-Host "# data-stream: printing CDC events here; Ctrl+C to stop"

if (-not $SkipBrowser) {
    Start-Process "http://127.0.0.1:33000/d/live_enterprise_stream/live-enterprise-stream-local?orgId=1&refresh=2s"
}

$argsList = @("--interval", "$Interval")
if ($Count -gt 0) { $argsList += @("--count", "$Count") }

& $Py tools/stream_local_source.py @argsList
exit $LASTEXITCODE
