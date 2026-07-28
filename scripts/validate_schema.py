"""验证 SQLite 建库脚本可以从空数据库完整执行。"""

import sqlite3
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    schema = (project_root / "database" / "schema.sql").read_text(encoding="utf-8")
    with sqlite3.connect(":memory:") as connection:
        connection.executescript(schema)
        table_count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = ?",
            ("table",),
        ).fetchone()
    if table_count != (10,):
        raise RuntimeError(f"数据库表数量不正确：{table_count}")
    print("SQLite 建库脚本校验通过：10 张业务表。")


if __name__ == "__main__":
    main()
