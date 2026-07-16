# Live gateway smoke (CI-parity unit/integration + container probes) via .venv.
#
# Usage:
#   .\scripts\run-smoke.ps1
#   .\scripts\run-smoke.ps1 -KeepGateway
#   .\scripts\run-smoke.ps1 -ForceVenv

param(
    [switch]$KeepGateway,
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
$mimicArgs = @(
    "--skip-deps",
    "--skip-k6",
    "--skip-resilience",
    "--skip-prod-sim",
    "--skip-walkthrough"
)
if ($KeepGateway) { $mimicArgs += "--keep-gateway" }

Write-Host "VANGUARD smoke -> $Py tools/run_mimic_prod.py $($mimicArgs -join ' ')"
& $Py tools/run_mimic_prod.py @mimicArgs
exit $LASTEXITCODE
