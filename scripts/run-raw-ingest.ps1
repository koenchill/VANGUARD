# Raw data ingest Local demo + integration gates (via .venv).
#
# Usage:
#   .\scripts\run-raw-ingest.ps1
#   .\scripts\run-raw-ingest.ps1 -TestsOnly
#   .\scripts\run-raw-ingest.ps1 -DemoOnly

param(
    [switch]$ForceVenv,
    [switch]$TestsOnly,
    [switch]$DemoOnly
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

if (-not $TestsOnly) {
    Write-Host "# raw-ingest: demo bulk + ongoing + quarantine"
    & $Py tools/demo_raw_ingest.py
    if ($LASTEXITCODE -ne 0) { $failed = 1 }
}

if (-not $DemoOnly) {
    Write-Host "# raw-ingest: pytest tests/integration/test_enterprise_ingestion.py"
    & $Py -m pytest tests/integration/test_enterprise_ingestion.py -v --tb=short
    if ($LASTEXITCODE -ne 0) { $failed = 1 }
}

if ($failed -eq 0) {
    Write-Host "# raw-ingest: PASS"
} else {
    Write-Host "# raw-ingest: FAIL"
}
exit $failed
