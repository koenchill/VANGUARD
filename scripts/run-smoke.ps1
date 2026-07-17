# Live gateway smoke (CI-parity unit/integration + container probes) via .venv.
#
# Usage:
#   .\scripts\run-smoke.ps1
#   .\scripts\run-smoke.ps1 -KeepGateway
#   .\scripts\run-smoke.ps1 -ForceVenv

param(
    [switch]$KeepGateway,
    [switch]$ForceVenv,
    [int]$GatewayPort = 0
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

function Test-PortFree([int]$Port) {
    -not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

if ($GatewayPort -le 0) {
    if (Test-PortFree 8000) {
        $GatewayPort = 8000
    } else {
        $GatewayPort = 18010
        Write-Host "# smoke: host port 8000 busy; VANGUARD_GATEWAY_PORT=$GatewayPort"
    }
}
$env:VANGUARD_GATEWAY_PORT = "$GatewayPort"

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

Write-Host "# smoke: $Py tools/run_mimic_prod.py $($mimicArgs -join ' ') gateway_port=$GatewayPort"
& $Py tools/run_mimic_prod.py @mimicArgs
if ($LASTEXITCODE -eq 0) {
    Write-Host "# smoke: PASS - see docs/validation/mimic-prod-report.md"
} else {
    Write-Host "# smoke: FAIL - exit $LASTEXITCODE"
}
exit $LASTEXITCODE
