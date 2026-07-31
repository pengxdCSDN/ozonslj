#!/usr/bin/env bash
set -euo pipefail

readonly app_dir="/opt/ozonslj/app/deploy"
readonly backup_file="${1:?请提供要验证的 PostgreSQL 自定义格式备份文件}"
readonly drill_database="ozonslj_restore_drill_$(date -u +%Y%m%d%H%M%S)"

if [[ ! -f "${backup_file}" ]]; then
  echo "备份文件不存在：${backup_file}" >&2
  exit 1
fi

cd "${app_dir}"

cleanup() {
  docker compose --env-file .env exec -T postgres \
    dropdb --username ozonslj --if-exists "${drill_database}" >/dev/null
}
trap cleanup EXIT

# 恢复到独立临时数据库，禁止覆盖正在运行的 ozonslj 业务库。
docker compose --env-file .env exec -T postgres \
  createdb --username ozonslj "${drill_database}"
docker compose --env-file .env exec -T postgres \
  pg_restore --username ozonslj --dbname "${drill_database}" <"${backup_file}"

migration_count="$(docker compose --env-file .env exec -T postgres \
  psql --username ozonslj --dbname "${drill_database}" --tuples-only --no-align \
  --command 'SELECT count(*) FROM schema_migrations;')"
table_count="$(docker compose --env-file .env exec -T postgres \
  psql --username ozonslj --dbname "${drill_database}" --tuples-only --no-align \
  --command 'SELECT count(*) FROM pg_tables WHERE schemaname=current_schema();')"

if [[ "${migration_count}" -lt 1 || "${table_count}" -lt 12 ]]; then
  echo "恢复后的迁移或数据表数量不完整。" >&2
  exit 1
fi

echo "PostgreSQL 恢复演练通过：迁移 ${migration_count} 条，数据表 ${table_count} 张。"
