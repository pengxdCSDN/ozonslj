import hashlib
from dataclasses import dataclass
from pathlib import Path

import psycopg

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_MIGRATIONS_PATH = _PROJECT_ROOT / "database" / "postgres" / "migrations"


class PostgresMigrationError(RuntimeError):
    """PostgreSQL 结构无法安全升级到当前程序版本。"""


@dataclass(frozen=True)
class _Migration:
    version: int
    name: str
    sql: str
    checksum: str


def migrate_postgres(
    dsn: str,
    *,
    migrations_path: Path = _DEFAULT_MIGRATIONS_PATH,
) -> None:
    """按版本执行 PostgreSQL 迁移，并拒绝校验和发生变化的历史迁移。"""

    migrations = _load_migrations(migrations_path)
    try:
        with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
            # API 与 Worker 可能同时启动，事务级咨询锁用于串行化首次建表与后续迁移。
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
            cursor.execute(
                """
                COMMENT ON TABLE schema_migrations IS
                    'PostgreSQL 结构迁移登记表；每个版本只执行一次，已登记历史禁止修改。';
                COMMENT ON COLUMN schema_migrations.version IS
                    '从 1 开始连续递增的迁移版本号。';
                COMMENT ON COLUMN schema_migrations.name IS
                    '迁移文件去除版本前缀和扩展名后的稳定名称。';
                COMMENT ON COLUMN schema_migrations.checksum IS
                    '迁移 SQL 的 SHA-256 校验和，用于拒绝被修改的历史迁移。';
                COMMENT ON COLUMN schema_migrations.applied_at IS
                    '迁移事务成功登记的带时区时间。';
                """
            )
            cursor.execute("LOCK TABLE schema_migrations IN EXCLUSIVE MODE")
            cursor.execute("SELECT version, checksum FROM schema_migrations ORDER BY version")
            applied = {int(row[0]): str(row[1]) for row in cursor.fetchall()}
            _verify_checksums(applied, migrations)

            for migration in migrations:
                if migration.version in applied:
                    continue
                cursor.execute(migration.sql)
                cursor.execute(
                    """
                        INSERT INTO schema_migrations (version, name, checksum)
                        VALUES (%s, %s, %s)
                        """,
                    (migration.version, migration.name, migration.checksum),
                )
    except (OSError, psycopg.Error) as error:
        raise PostgresMigrationError("PostgreSQL 结构迁移失败，事务已回滚") from error


def _load_migrations(migrations_path: Path) -> tuple[_Migration, ...]:
    migrations: list[_Migration] = []
    for path in sorted(migrations_path.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        version_text, _, name_with_suffix = path.name.partition("_")
        sql = path.read_text(encoding="utf-8")
        migrations.append(
            _Migration(
                version=int(version_text),
                name=name_with_suffix.removesuffix(".sql"),
                sql=sql,
                checksum=hashlib.sha256(sql.encode("utf-8")).hexdigest(),
            )
        )
    if not migrations:
        raise PostgresMigrationError("未找到 PostgreSQL 迁移文件")
    return tuple(migrations)


def _verify_checksums(
    applied: dict[int, str],
    migrations: tuple[_Migration, ...],
) -> None:
    expected = {migration.version: migration.checksum for migration in migrations}
    unknown_versions = sorted(set(applied) - set(expected))
    if unknown_versions:
        raise PostgresMigrationError(f"数据库包含当前程序未知的迁移版本：{unknown_versions!r}")
    for version, actual_checksum in applied.items():
        if actual_checksum != expected[version]:
            raise PostgresMigrationError(f"PostgreSQL 迁移 v{version} 校验和与代码不一致")
