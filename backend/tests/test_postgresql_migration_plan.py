from pathlib import Path

import pytest

from backend.app.infrastructure.postgresql.migrations import (
    LEGACY_BASELINE,
    PostgresMigrationError,
    build_migration_plan,
)


def test_new_database_uses_authoritative_schema_and_migrations() -> None:
    """新数据库必须从权威 schema 开始，并保持仓库迁移版本不变。"""
    plan = build_migration_plan({})

    assert plan[0].version == 1
    assert plan[0].name == "initial"
    assert plan[1].version == 2
    assert plan[1].name == "multi_tenant_saas"
    assert plan[-1].source_version == 88


def test_legacy_database_gets_explicit_compatibility_steps() -> None:
    """旧云端账本不得覆盖历史版本，兼容步骤必须位于现代迁移之前。"""
    plan = build_migration_plan(dict(LEGACY_BASELINE))

    assert [migration.name for migration in plan[:3]] == [
        "legacy_identity_tables_preserved",
        "multi_tenant_saas",
        "legacy_operator_backfill",
    ]
    assert [migration.version for migration in plan[:3]] == [3, 4, 5]
    assert plan[3].source_version == 3
    assert plan[3].version == 6


def test_unknown_or_modified_legacy_baseline_is_rejected() -> None:
    """只有已核验的旧迁移校验和可以进入兼容升级路径。"""
    with pytest.raises(PostgresMigrationError, match="未知或已修改"):
        build_migration_plan({1: "modified", 2: LEGACY_BASELINE[2]})


def test_dockerfile_packages_only_authoritative_migration_sources() -> None:
    """发布镜像不得再次携带与权威迁移平行的旧目录。"""
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "COPY database/postgresql_schema.sql ./database/postgresql_schema.sql" in dockerfile
    assert "COPY database/migrations ./database/migrations" in dockerfile
    assert "COPY database/postgres " not in dockerfile
