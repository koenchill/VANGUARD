# Mimic production-like Local evidence for VANGUARD (G-001 portfolio — not ATO).
#
# Usage:
#   .\scripts\mimic-prod.ps1
#   .\scripts\mimic-prod.ps1 -Quick
#   .\scripts\mimic-prod.ps1 -SkipGateway -SkipK6
#   .\scripts\mimic-prod.ps1 -KeepGateway

param(
    [switch]$SkipDeps,
    [switch]$SkipGateway,
    [switch]$SkipK6,
    [switch]$SkipWalkthrough,
    [switch]$Quick,
    [switch]$KeepGateway
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot
$env:PYTHONPATH = "$RepoRoot"

$argsList = @()
if ($SkipDeps) { $argsList += "--skip-deps" }
if ($SkipGateway) { $argsList += "--skip-gateway" }
if ($SkipK6) { $argsList += "--skip-k6" }
if ($SkipWalkthrough) { $argsList += "--skip-walkthrough" }
if ($Quick) { $argsList += "--quick" }
if ($KeepGateway) { $argsList += "--keep-gateway" }

Write-Host "VANGUARD mimic-prod → python tools/run_mimic_prod.py $($argsList -join ' ')"
& python tools/run_mimic_prod.py @argsList
exit $LASTEXITCODE
