$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonBin = Join-Path $projectRoot ".venv\Scripts"

& (Join-Path $pythonBin "python.exe") -m pytest
& (Join-Path $pythonBin "ruff.exe") check backend scripts
& (Join-Path $pythonBin "mypy.exe") backend\app
# PostgreSQL schema 的迁移与约束契约由 backend/tests/test_postgresql_bootstrap.py
# 等测试覆盖；旧的 SQLite schema 校验脚本已删除，不再在总检查中调用。

& (Join-Path $pythonBin "python.exe") (Join-Path $projectRoot "scripts\validate_schema.py")
$env:CI = "true"
pnpm typecheck
pnpm build
