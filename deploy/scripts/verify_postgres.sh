#!/usr/bin/env bash
set -euo pipefail

# 在隔离的临时 PostgreSQL 16 容器中验证基线迁移，不创建或修改正式数据卷。
readonly container_name="ozonslj-postgres-schema-verify"
readonly image="${POSTGRES_VERIFY_IMAGE:-crpi-vq6wc2wogtrd0ib9.cn-guangzhou.personal.cr.aliyuncs.com/kakapeng0927/pxd:postgres-16-alpine}"
readonly migration_file="${1:-/tmp/ozonslj-0001-verify.sql}"
password="$(openssl rand -hex 24)"

cleanup() {
  docker rm -f "${container_name}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

if docker container inspect "${container_name}" >/dev/null 2>&1; then
  echo "验证容器已存在，为避免误删未知进程，本次验证终止。" >&2
  exit 1
fi

docker run --detach --rm \
  --name "${container_name}" \
  --env POSTGRES_DB=ozonslj_verify \
  --env POSTGRES_USER=ozonslj_verify \
  --env POSTGRES_PASSWORD="${password}" \
  --mount "type=bind,source=${migration_file},target=/verify/0001_initial.sql,readonly" \
  "${image}" >/dev/null

for _ in $(seq 1 30); do
  if docker exec "${container_name}" \
    pg_isready --username ozonslj_verify --dbname ozonslj_verify >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

docker exec "${container_name}" \
  psql --username ozonslj_verify --dbname ozonslj_verify \
  --set ON_ERROR_STOP=1 --file /verify/0001_initial.sql >/dev/null

table_count="$(docker exec "${container_name}" psql --tuples-only --no-align \
  --username ozonslj_verify --dbname ozonslj_verify \
  --command "SELECT count(*) FROM pg_tables WHERE schemaname = 'public';")"
commented_table_count="$(docker exec "${container_name}" psql --tuples-only --no-align \
  --username ozonslj_verify --dbname ozonslj_verify \
  --command "SELECT count(*) FROM pg_class WHERE relnamespace = 'public'::regnamespace AND relkind = 'r' AND obj_description(oid) IS NOT NULL;")"
active_job_index_count="$(docker exec "${container_name}" psql --tuples-only --no-align \
  --username ozonslj_verify --dbname ozonslj_verify \
  --command "SELECT count(*) FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'idx_sync_jobs_one_active_workspace' AND indexdef LIKE '%WHERE (status = ANY%';")"
checkpoint_trigger_count="$(docker exec "${container_name}" psql --tuples-only --no-align \
  --username ozonslj_verify --dbname ozonslj_verify \
  --command "SELECT count(*) FROM pg_trigger WHERE tgname = 'trg_sync_checkpoints_success' AND NOT tgisinternal;")"

if [[ "${table_count}" != "11" ]]; then
  echo "核心业务表数量不正确：${table_count}" >&2
  exit 1
fi
if [[ "${commented_table_count}" != "11" ]]; then
  echo "存在缺少 COMMENT ON 的业务表：已注释 ${commented_table_count}/11" >&2
  exit 1
fi
if [[ "${active_job_index_count}" != "1" ]]; then
  echo "活动同步任务部分唯一索引缺失或条件不正确。" >&2
  exit 1
fi
if [[ "${checkpoint_trigger_count}" != "1" ]]; then
  echo "同步水位成功约束触发器缺失。" >&2
  exit 1
fi

echo "PostgreSQL 16 真实迁移验证通过：11 张业务表、11 个表注释、关键索引与水位触发器均有效。"
