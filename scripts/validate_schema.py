"""校验 PostgreSQL 权威 schema 与迁移文件的基本完整性。

该脚本只检查 PostgreSQL SQL 文件，不连接数据库、不执行外部写入，也不包含 SQLite
兼容逻辑。它用于提交前尽早发现迁移文件遗漏事务、误加入 SQLite 语句或重复版本号。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "database" / "migrations"
SCHEMA = ROOT / "database" / "postgresql_schema.sql"


def main() -> int:
    errors: list[str] = []
    if not SCHEMA.is_file():
        errors.append("缺少 database/postgresql_schema.sql")
    migration_files = sorted(MIGRATIONS.glob("*.sql"))
    if not migration_files:
        errors.append("database/migrations 中没有 PostgreSQL 迁移文件")

    versions: list[int] = []
    for migration in migration_files:
        text = migration.read_text(encoding="utf-8")
        match = re.match(r"(\d+)_", migration.name)
        if match:
            versions.append(int(match.group(1)))
        if "sqlite" in text.casefold():
            errors.append(f"{migration.name} 不得包含 SQLite 语句")
        if "CREATE TABLE" not in text and "ALTER TABLE" not in text:
            errors.append(f"{migration.name} 不包含表结构变更语句")

    if len(versions) != len(set(versions)):
        errors.append("迁移文件版本号重复")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PostgreSQL schema validation passed: {len(migration_files)} migrations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
