# Production-simulation (mission-alpha Local gate) using repo .venv.
#
# Usage:
#   .\scripts\run-prod-simulation.ps1
#   .\scripts\run-prod-simulation.ps1 -ForceVenv

param(
    [switch]$ForceVenv
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$ensureArgs = @()
if ($ForceVenv) { $ensureArgs += "-Force" }
$Py = & "$PSScriptRoot\ensure-venv.ps1" @ensureArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:PYTHONPATH = "$RepoRoot"
Write-Host "VANGUARD prod-simulation -> $Py -m pytest tests/production-simulation -v --tb=short"
& $Py -m pytest tests/production-simulation -v --tb=short
exit $LASTEXITCODE
