"""说明本模块的职责、边界和主要协作对象。"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg import sql

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_BASE_SCHEMA_PATH = _PROJECT_ROOT / "database" / "postgresql_schema.sql"
_MIGRATIONS_PATH = _PROJECT_ROOT / "database" / "migrations"

# 2026-08-11 云端旧基线的已登记校验和。只有精确匹配该账本时才允许进入兼容路径，
# 避免把未知数据库误判为旧版本并重命名身份表；这些摘要不包含凭据或业务数据。
LEGACY_BASELINE: dict[int, str] = {
    1: "1a01277233c3a926cad706d98c15876c6e9ffe7aef03a2bd8b013fbf76606cc2",
    2: "2c61be3480da0d0072d20922682efcb1d0ab2328d6ee38cf959786ba610599b4",
}

_TRANSACTION_CONTROL_RE = re.compile(r"(?im)^\s*(?:BEGIN|COMMIT);\s*$")

# 这些表在早期迁移中以试验版结构创建，后续迁移又用同名表承载正式的组织级模型。
# PostgreSQL 的 CREATE TABLE IF NOT EXISTS 不会补齐字段，因此执行正式迁移前把旧结构完整移入
# legacy_archive schema。表、索引、约束和历史数据都会保留，且不会与 public 中的新结构重名。
_SUPERSEDED_TABLES_BY_SOURCE_VERSION: dict[int, str] = {
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

_LEGACY_PRESERVE_SQL = """
ALTER TABLE workspace_memberships RENAME TO legacy_workspace_memberships;
ALTER TABLE user_sessions RENAME TO legacy_user_sessions;
"""

_LEGACY_BACKFILL_SQL = """
INSERT INTO users (
    id, email, display_name, password_hash, status, email_verified_at
)
SELECT id, lower(btrim(email)), display_name, password_hash, 'active', CURRENT_TIMESTAMP
FROM operators
WHERE is_active = true AND email IS NOT NULL AND password_hash IS NOT NULL
ON CONFLICT (id) DO NOTHING;

INSERT INTO organization_members (organization_id, user_id, role, status)
SELECT
    'legacy-bootstrap',
    operator_account.id,
    CASE operator_account.role
        WHEN 'admin' THEN 'admin'
        WHEN 'supervisor' THEN 'operations_manager'
        WHEN 'finance' THEN 'finance'
        WHEN 'readonly_analyst' THEN 'readonly_analyst'
        ELSE 'operator'
    END,
    'active'
FROM operators AS operator_account
JOIN users AS user_account ON user_account.id = operator_account.id
ON CONFLICT (organization_id, user_id) DO NOTHING;

INSERT INTO workspace_memberships (
    organization_id, workspace_id, user_id, access_level
)
SELECT
    workspace.organization_id,
    legacy_membership.workspace_id,
    legacy_membership.operator_id,
    CASE operator_account.role
        WHEN 'admin' THEN 'manage'
        WHEN 'supervisor' THEN 'manage'
        WHEN 'operator' THEN 'operate'
        ELSE 'read'
    END
FROM legacy_workspace_memberships AS legacy_membership
JOIN operators AS operator_account ON operator_account.id = legacy_membership.operator_id
JOIN users AS user_account ON user_account.id = legacy_membership.operator_id
JOIN store_workspaces AS workspace ON workspace.id = legacy_membership.workspace_id
ON CONFLICT (workspace_id, user_id) DO NOTHING;
"""


class PostgresMigrationError(RuntimeError):
    """PostgreSQL 结构无法安全升级到当前程序版本。"""


@dataclass(frozen=True, slots=True)
class Migration:
    """一条将写入迁移账本的不可变迁移。"""

    version: int
    name: str
    sql: str
    checksum: str
    source_version: int | None = None


def build_migration_plan(applied: dict[int, str]) -> tuple[Migration, ...]:
    """根据空库或已核验旧基线生成不可覆盖历史的迁移计划。"""
    authoritative = _load_authoritative_migrations()
    base_sql = _BASE_SCHEMA_PATH.read_text(encoding="utf-8")
    if not applied:
        return (_migration(1, "initial", base_sql, source_version=1), *authoritative)

    if all(applied.get(version) == checksum for version, checksum in LEGACY_BASELINE.items()):
        legacy_complete = _build_legacy_migration_plan(authoritative)
        expected_legacy = {
            **LEGACY_BASELINE,
            **{migration.version: migration.checksum for migration in legacy_complete},
        }
        if all(expected_legacy.get(version) == checksum for version, checksum in applied.items()):
            return tuple(
                migration for migration in legacy_complete if migration.version not in applied
            )
        raise PostgresMigrationError("旧版数据库迁移账本包含未知或已修改的迁移，已停止自动升级")

    complete = (_migration(1, "initial", base_sql, source_version=1), *authoritative)
    expected = {migration.version: migration.checksum for migration in complete}
    if all(expected.get(version) == checksum for version, checksum in applied.items()):
        return tuple(migration for migration in complete if migration.version not in applied)
    raise PostgresMigrationError("数据库迁移账本属于未知或已修改的基线，已停止自动升级")


def migrate_postgres(dsn: str) -> None:
    """在单个事务与咨询锁内执行迁移；任一步失败都会完整回滚。"""
    try:
        with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext('ozonslj_schema_migrations'))")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version integer PRIMARY KEY CHECK (version > 0),
                    name text NOT NULL CHECK (length(btrim(name)) > 0),
                    checksum text NOT NULL CHECK (length(btrim(checksum)) > 0),
                    applied_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
            cursor.execute("LOCK TABLE schema_migrations IN EXCLUSIVE MODE")
            cursor.execute("SELECT version, checksum FROM schema_migrations ORDER BY version")
            applied = {int(row[0]): str(row[1]) for row in cursor.fetchall()}
            for migration in build_migration_plan(applied):
                _archive_superseded_table(cursor, migration.source_version)
                # 历史 SQL 文件可能自带 BEGIN/COMMIT；若直接执行会提前提交外层迁移事务。
                # 仅移除独立行的事务控制语句，SQL 校验和仍基于原文件，历史审计不变。
                try:
                    cursor.execute(_without_transaction_control(migration.sql))
                except psycopg.Error as error:
                    raise PostgresMigrationError(
                        f"PostgreSQL 迁移 v{migration.version} {migration.name!r} 执行失败"
                    ) from error
                cursor.execute(
                    """
                    INSERT INTO schema_migrations (version, name, checksum)
                    VALUES (%s, %s, %s)
                    """,
                    (migration.version, migration.name, migration.checksum),
                )
    except (OSError, psycopg.Error) as error:
        raise PostgresMigrationError("PostgreSQL 结构迁移失败，事务已回滚") from error


def _load_authoritative_migrations() -> tuple[Migration, ...]:
    """执行内部步骤 _load_authoritative_migrations，供同一模块的公开流程复用。"""
    migrations: list[Migration] = []
    for path in sorted(_MIGRATIONS_PATH.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        version_text, _, name_with_suffix = path.name.partition("_")
        source_version = int(version_text)
        sql = path.read_text(encoding="utf-8")
        migrations.append(
            _migration(
                source_version,
                name_with_suffix.removesuffix(".sql"),
                sql,
                source_version=source_version,
            )
        )
    if not migrations or migrations[0].source_version != 2:
        raise PostgresMigrationError("权威 PostgreSQL 迁移必须从版本 0002 开始")
    return tuple(migrations)


def _migration(
    version: int,
    name: str,
    sql: str,
    *,
    source_version: int | None = None,
) -> Migration:
    """执行内部步骤 _migration，供同一模块的公开流程复用。"""
    return Migration(
        version=version,
        name=name,
        sql=sql,
        checksum=hashlib.sha256(sql.encode("utf-8")).hexdigest(),
        source_version=source_version,
    )


def _build_legacy_migration_plan(
    authoritative: tuple[Migration, ...],
) -> tuple[Migration, ...]:
    """生成旧云端基线的稳定版本映射，后续启动可继续追加新迁移。"""
    modern_v2 = authoritative[0]
    later = tuple(
        _migration(
            migration.source_version + 3,
            migration.name,
            migration.sql,
            source_version=migration.source_version,
        )
        for migration in authoritative[1:]
        if migration.source_version is not None
    )
    return (
        _migration(3, "legacy_identity_tables_preserved", _LEGACY_PRESERVE_SQL),
        _migration(4, modern_v2.name, modern_v2.sql, source_version=2),
        _migration(5, "legacy_operator_backfill", _LEGACY_BACKFILL_SQL),
        *later,
    )


def _without_transaction_control(sql: str) -> str:
    """让迁移运行器独占事务边界，保证任一迁移失败时整批回滚。"""
    return _TRANSACTION_CONTROL_RE.sub("", sql)


def _archive_superseded_table(
    cursor: psycopg.Cursor[tuple[object, ...]], source_version: int | None
) -> None:
    """正式同名表创建前归档缺少 organization_id 的试验版结构。"""
    table_name = _SUPERSEDED_TABLES_BY_SOURCE_VERSION.get(source_version or -1)
    if table_name is None:
        return

    cursor.execute(
        """
        SELECT
            to_regclass(%s) IS NOT NULL,
            EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                  AND column_name = 'organization_id'
            )
        """,
        (f"public.{table_name}", table_name),
    )
    row = cursor.fetchone()
    if row is None or not bool(row[0]) or bool(row[1]):
        return

    cursor.execute("CREATE SCHEMA IF NOT EXISTS legacy_archive")
    cursor.execute(
        """
        COMMENT ON SCHEMA legacy_archive IS
        '迁移期间保留的旧版试验结构；仅供审计与人工数据核对，不作为当前业务查询来源。'
        """
    )
    cursor.execute(
        sql.SQL("ALTER TABLE public.{} SET SCHEMA legacy_archive").format(
            sql.Identifier(table_name)
        )
    )
