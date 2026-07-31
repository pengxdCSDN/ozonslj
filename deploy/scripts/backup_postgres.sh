#!/usr/bin/env bash
set -euo pipefail

# PostgreSQL 备份固定写入服务器受控目录，避免变量错误扩大清理范围。
readonly app_dir="/opt/ozonslj/app/deploy"
readonly backup_dir="/opt/ozonslj/backups"
readonly timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
readonly final_file="${backup_dir}/ozonslj-${timestamp}.dump"
readonly temporary_file="${final_file}.tmp"

install -d -m 700 "${backup_dir}"
cd "${app_dir}"

# 先写临时文件并验证目录，成功后再原子改名，避免保留看似有效的不完整备份。
docker compose --env-file .env exec -T postgres \
  pg_dump --username ozonslj --dbname ozonslj --format=custom >"${temporary_file}"
docker compose --env-file .env exec -T postgres \
  pg_restore --list <"${temporary_file}" >/dev/null
chmod 600 "${temporary_file}"
mv "${temporary_file}" "${final_file}"

# 仅清理固定备份目录中超过七天且符合项目命名规则的转储文件。
find "${backup_dir}" -maxdepth 1 -type f -name 'ozonslj-*.dump' -mtime +7 -delete
echo "PostgreSQL 备份完成：${final_file}"
