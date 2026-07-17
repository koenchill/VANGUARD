# Local E2E: raw enterprise ingest -> promote -> Grafana Mission BI contract (.venv).
#
# Usage:
#   .\scripts\run-ingest-to-grafana.ps1
#   .\scripts\run-ingest-to-grafana.ps1 -WithPytest

param(
    [switch]$ForceVenv,
    [switch]$WithPytest
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$ensureArgs = @()
if ($ForceVenv) { $ensureArgs += "-Force" }
$Py = & "$PSScriptRoot\ensure-venv.ps1" @ensureArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:PYTHONPATH = "$RepoRoot"
$failed = 0

Write-Host "# ingest-to-grafana: raw enterprise ingest through Grafana contract"
& $Py tools/demo_ingest_to_grafana.py
if ($LASTEXITCODE -ne 0) { $failed = 1 }

if ($WithPytest) {
    Write-Host "# ingest-to-grafana: related integration suites"
    & $Py -m pytest `
        tests/integration/test_enterprise_ingestion.py `
        tests/integration/test_promotion_controller.py `
        tests/integration/test_bi_dual_path.py `
        -q --tb=line
    if ($LASTEXITCODE -ne 0) { $failed = 1 }
}

if ($failed -eq 0) {
    Write-Host "# ingest-to-grafana: PASS - docs/validation/ingest-to-grafana-report.md"
} else {
    Write-Host "# ingest-to-grafana: FAIL"
}
exit $failed
