# Mimic production-like Local evidence for VANGUARD (G-001 portfolio — not ATO).
# Always bootstraps repo .venv first (Python 3.11+).
#
# Usage:
#   .\scripts\mimic-prod.ps1
#   .\scripts\mimic-prod.ps1 -Quick
#   .\scripts\mimic-prod.ps1 -SkipGateway -SkipK6
#   .\scripts\mimic-prod.ps1 -KeepGateway
#   .\scripts\mimic-prod.ps1 -ForceVenv

param(
    [switch]$SkipDeps,
    [switch]$SkipGateway,
    [switch]$SkipK6,
    [switch]$SkipWalkthrough,
    [switch]$Quick,
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

$argsList = @("--skip-deps")  # ensure-venv already installed requirements
if ($SkipDeps) { } # kept for API compat; deps already applied via ensure-venv
if ($SkipGateway) { $argsList += "--skip-gateway" }
if ($SkipK6) { $argsList += "--skip-k6" }
if ($SkipWalkthrough) { $argsList += "--skip-walkthrough" }
if ($Quick) { $argsList += "--quick" }
if ($KeepGateway) { $argsList += "--keep-gateway" }

Write-Host "# mimic-prod: $Py tools/run_mimic_prod.py $($argsList -join ' ')"
& $Py tools/run_mimic_prod.py @argsList
exit $LASTEXITCODE
