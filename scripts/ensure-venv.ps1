# Ensure repo-local .venv exists and return its python path.
# Usage:  $Py = & .\scripts\ensure-venv.ps1
#         & $Py -m pytest ...

param(
    [switch]$Force,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$ensureArgs = @()
if ($Force) { $ensureArgs += "--force" }
if ($SkipInstall) { $ensureArgs += "--skip-install" }

# Bootstrap with py -3.11 when available; ensure_venv.py creates the venv.
# Discard tool stdout so callers that capture this script only get the venv path.
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.11 tools/ensure_venv.py @ensureArgs | Out-Null
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python tools/ensure_venv.py @ensureArgs | Out-Null
    } else {
        throw "Python not found. Install Python 3.11+ (or the Windows py launcher)."
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    $ErrorActionPreference = $prevEap
}

$Py = (Join-Path $RepoRoot ".venv\Scripts\python.exe")
if (-not (Test-Path $Py)) {
    throw "Expected venv python missing: $Py"
}
# Single success-stream line for `$Py = & .\scripts\ensure-venv.ps1`
$Py
