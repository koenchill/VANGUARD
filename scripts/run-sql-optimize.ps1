# Local SQL optimization lab (EXPLAIN ANALYZE on Mission BI mart stand-in).
#
# Prerequisites: .\scripts\run-grafana-local.ps1  (Postgres on :15432)
#
# Usage:
#   .\scripts\run-sql-optimize.ps1

param([switch]$ForceVenv)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$running = docker ps --filter "name=vanguard-grafana-pg" --format "{{.Names}}"
if (-not $running) {
    Write-Host "# sql-optimize: starting Local Grafana/Postgres first"
    & "$PSScriptRoot\run-grafana-local.ps1" -SkipBrowser
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$ensureArgs = @()
if ($ForceVenv) { $ensureArgs += "-Force" }
$Py = & "$PSScriptRoot\ensure-venv.ps1" @ensureArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:PYTHONPATH = "$RepoRoot"
Write-Host "# sql-optimize: EXPLAIN ANALYZE lab on reporting.metric_series"
& $Py tools/run_sql_optimization.py
$code = $LASTEXITCODE
if ($code -eq 0) {
    Write-Host "# sql-optimize: PASS - docs/validation/sql-optimization-report.md"
} else {
    Write-Host "# sql-optimize: FAIL"
}
exit $code
