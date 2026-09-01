$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $RepoRoot "src"

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -m unittest discover -s (Join-Path $RepoRoot "tests") -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & py -3 (Join-Path $RepoRoot "scripts\laptop1_acceptance.py")
    exit $LASTEXITCODE
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.10 or newer is required."
}
& python -m unittest discover -s (Join-Path $RepoRoot "tests") -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& python (Join-Path $RepoRoot "scripts\laptop1_acceptance.py")
exit $LASTEXITCODE
