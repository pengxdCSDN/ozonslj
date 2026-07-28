$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonBin = Join-Path $projectRoot ".venv\Scripts"

& (Join-Path $pythonBin "python.exe") -m pytest
& (Join-Path $pythonBin "ruff.exe") check backend
& (Join-Path $pythonBin "mypy.exe") backend\app
& (Join-Path $pythonBin "python.exe") scripts\validate_schema.py

$env:CI = "true"
pnpm typecheck
pnpm build
