#!/usr/bin/env bash
set -euo pipefail

# 发布门禁只检查本机回环地址，不把凭据、Cookie 或业务响应写入日志。
# 失败时默认只退出并保留现场；显式设置 ROLLBACK_ON_FAILURE=1 才会回滚应用镜像。
compose=(docker compose --env-file .env)
previous_tag="${PREVIOUS_APP_IMAGE_TAG:-}"

rollback() {
  if [[ "${ROLLBACK_ON_FAILURE:-0}" != "1" || -z "$previous_tag" ]]; then
    echo "release_gate=failed rollback=not_requested" >&2
    exit 1
  fi
  echo "release_gate=failed rollback=starting"
  APP_IMAGE_TAG="$previous_tag" "${compose[@]}" up -d --no-deps api worker scheduler
  "${compose[@]}" restart web
  echo "release_gate=failed rollback=completed tag=$previous_tag"
  exit 1
}

trap rollback ERR
"${compose[@]}" config --quiet
# API/Worker 重建后 Compose 可能为 API 分配新 IP；Nginx worker 会继续使用旧
# upstream 地址，导致浏览器登录和所有 /api 请求返回 502。每次发布门禁先刷新
# Web upstream，再执行 API 健康检查，避免把这个步骤依赖人工记忆。
"${compose[@]}" restart web
curl --fail --silent --show-error --output /dev/null http://127.0.0.1/
api_get() {
  local path="$1"
  "${compose[@]}" exec -T api python -c \
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000${path}', timeout=3).read()"
}
api_get /health/live
api_get /health/ready
api_get /health/ops
metrics="$("${compose[@]}" exec -T api python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/metrics', timeout=3).read().decode())")"
grep -q 'ozonslj_http_requests_total' <<<"$metrics"
grep -q 'ozonslj_disk_used_ratio' <<<"$metrics"
echo "release_gate=passed health=live,ready,ops metrics=present"
