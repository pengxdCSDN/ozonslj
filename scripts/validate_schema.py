"""静态校验 PostgreSQL 迁移链、核心结构与中文知识注释。"""

import re
from pathlib import Path

MIGRATION_NAME_PATTERN = re.compile(r"^(?P<version>\d{4})_[a-z0-9_]+\.sql$")
REQUIRED_TABLES = {
    "operators",
    "seller_accounts",
    "store_workspaces",
    "product_offers",
    "stock_positions",
    "customer_orders",
    "postings",
    "posting_items",
    "sync_jobs",
    "sync_checkpoints",
    "seller_operations",
    "workspace_memberships",
    "user_sessions",
}
REQUIRED_INDEXES = {
    "idx_product_offers_workspace_position",
    "idx_stock_positions_workspace_quantity",
    "idx_orders_workspace_status_time",
    "idx_postings_workspace_status_shipment",
    "idx_posting_items_posting",
    "idx_sync_jobs_one_active_workspace",
    "idx_operations_workspace_time",
    "operators_email_unique_idx",
    "workspace_memberships_workspace_idx",
    "user_sessions_operator_active_idx",
}
FORBIDDEN_TERMS = {"Api-Key明文", "Client-Id明文"}


def main() -> None:
    """验证唯一 PostgreSQL SQL 来源具备连续迁移和可供 RAG 使用的中文说明。"""

    project_root = Path(__file__).resolve().parent.parent
    migrations_path = project_root / "database" / "postgres" / "migrations"
    migration_files = sorted(migrations_path.glob("*.sql"))
    if not migration_files:
        raise RuntimeError("未找到 PostgreSQL 迁移文件")

    versions: list[int] = []
    combined_sql_parts: list[str] = []
    for migration_file in migration_files:
        match = MIGRATION_NAME_PATTERN.fullmatch(migration_file.name)
        if match is None:
            raise RuntimeError(f"PostgreSQL 迁移文件名不合法：{migration_file.name}")
        versions.append(int(match.group("version")))
        sql = migration_file.read_text(encoding="utf-8")
        if "COMMENT ON" not in sql:
            raise RuntimeError(f"迁移缺少 PostgreSQL 中文知识注释：{migration_file.name}")
        if not _contains_chinese(sql):
            raise RuntimeError(f"迁移缺少简体中文业务说明：{migration_file.name}")
        combined_sql_parts.append(sql)

    expected_versions = list(range(1, len(versions) + 1))
    if versions != expected_versions:
        raise RuntimeError(
            f"PostgreSQL 迁移版本必须从 0001 连续递增：actual={versions!r}"
        )

    combined_sql = "\n".join(combined_sql_parts)
    _assert_named_objects(combined_sql, "TABLE", REQUIRED_TABLES)
    _assert_named_objects(combined_sql, "INDEX", REQUIRED_INDEXES)
    missing_table_comments = {
        table
        for table in REQUIRED_TABLES
        if f"COMMENT ON TABLE {table} IS" not in combined_sql
    }
    if missing_table_comments:
        raise RuntimeError(f"数据表缺少中文职责注释：{sorted(missing_table_comments)!r}")
    for forbidden_term in FORBIDDEN_TERMS:
        if forbidden_term in combined_sql:
            raise RuntimeError(f"SQL 中出现禁止内容：{forbidden_term}")

    print(
        f"PostgreSQL Schema v{versions[-1]} 静态校验通过："
        f"{len(REQUIRED_TABLES)} 张核心表，{len(REQUIRED_INDEXES)} 个关键索引"
    )


def _contains_chinese(value: str) -> bool:
    return any("\u4e00" <= character <= "\u9fff" for character in value)


def _assert_named_objects(sql: str, object_type: str, names: set[str]) -> None:
    missing = {
        name
        for name in names
        if f"CREATE {object_type} {name}" not in sql
        and f"CREATE UNIQUE {object_type} {name}" not in sql
    }
    if missing:
        raise RuntimeError(f"PostgreSQL 缺少 {object_type}：{sorted(missing)!r}")


if __name__ == "__main__":
    main()
