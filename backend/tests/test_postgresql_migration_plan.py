from pathlib import Path

import pytest

from backend.app.infrastructure.postgresql.migrations import (
    _SUPERSEDED_TABLES_BY_SOURCE_VERSION,
    LEGACY_BASELINE,
    PostgresMigrationError,
    _without_transaction_control,
    build_migration_plan,
)


def test_new_database_uses_authoritative_schema_and_migrations() -> None:
    """新数据库必须从权威 schema 开始，并保持仓库迁移版本不变。"""
    plan = build_migration_plan({})

    assert plan[0].version == 1
    assert plan[0].name == "initial"
    assert plan[1].version == 2
    assert plan[1].name == "multi_tenant_saas"
    assert plan[-1].source_version == 89


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


def test_upgraded_legacy_database_can_receive_later_migrations() -> None:
    """旧基线升级后必须继续识别偏移版本账本，不能在下一次发布被判为未知。"""
    first_plan = build_migration_plan(dict(LEGACY_BASELINE))
    applied = {
        **LEGACY_BASELINE,
        **{migration.version: migration.checksum for migration in first_plan[:-1]},
    }

    remaining = build_migration_plan(applied)

    assert [migration.source_version for migration in remaining] == [89]
    assert [migration.version for migration in remaining] == [92]


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


def test_embedded_transaction_control_is_removed_before_execution() -> None:
    """历史 SQL 的事务语句不得提前提交迁移运行器的外层事务。"""
    sql = "BEGIN;\nCREATE TABLE example (id integer);\nCOMMIT;\n"

    executable = _without_transaction_control(sql)

    assert "BEGIN;" not in executable
    assert "COMMIT;" not in executable
    assert "CREATE TABLE example" in executable


def test_all_redeclared_tables_have_an_explicit_archive_boundary() -> None:
    """同名正式表上线前必须归档试验版结构，避免 IF NOT EXISTS 掩盖字段缺失。"""
    expected = {
        58: "listing_fabe_drafts",
        59: "listing_smart_search_reports",
        60: "listing_risk_reports",
        61: "listing_versions",
        62: "listing_publish_commands",
        64: "advertising_threshold_versions",
        67: "model_adapter_configs",
        74: "agent_triggers",
        76: "external_notification_configs",
    }

    assert expected == _SUPERSEDED_TABLES_BY_SOURCE_VERSION
