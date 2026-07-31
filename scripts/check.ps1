$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonBin = Join-Path $projectRoot ".venv\Scripts"

& (Join-Path $pythonBin "python.exe") -m pytest
& (Join-Path $pythonBin "ruff.exe") check backend scripts
& (Join-Path $pythonBin "mypy.exe") backend\app
& (Join-Path $pythonBin "python.exe") -m scripts.validate_schema

$env:CI = "true"
pnpm typecheck
pnpm build
