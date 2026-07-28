$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Python virtual environment is missing. Run: python -m venv .venv"
}

& $pythonPath -m uvicorn backend.app.main:app `
    --reload `
    --host 127.0.0.1 `
    --port 8000

