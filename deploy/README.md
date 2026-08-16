# 云端 RAG 部署说明

`chroma.compose.yml` 只负责 Chroma 运行时，不在开发服务器本地构建镜像。发布流程应在外部构建节点完成镜像签名/扫描后，由服务器拉取固定版本运行。

## 运行边界

- Chroma 仅绑定 `127.0.0.1:8000`，API/Worker 通过内网访问；不直接暴露公网。
- `chroma_data` 是持久卷，删除前必须先执行备份和索引对账。
- 健康检查失败时停止新索引任务，保留查询降级和撤回能力；不得重建 PostgreSQL、Redis 或 Nginx。
- 2GB 开发服务器只运行容器，不执行前端、Python 或 Chroma 镜像构建。

## 发布前检查

1. 在外部构建节点固定 `chromadb/chroma:0.5.23`，完成漏洞扫描和镜像签名。
2. 云端仅执行 `docker compose -f deploy/chroma.compose.yml pull` 和受控重启。
3. 验证 `/api/v1/heartbeat`、卷挂载和 API/Worker 连接；失败则回滚到上一镜像标签。

## 应用切换检查

- `deploy/compose.yaml` 为 API/Worker 注入 `APP_ENV=production`、`CHROMA_URL=http://chroma:8000` 和固定组织 ID。
- 首次使用知识 RAG 前确认数据库已应用 `0090_rag_knowledge_governance.sql` 与 `0091_rag_keyword_search.sql`；RLS 连接上下文由 API/Worker 每个事务设置。
- 通过来源创建 → 版本创建 → 摄取切片 → 发布版本的顺序写入。未发布切片只在 PostgreSQL 草稿区，不会出现在 Chroma。
- Chroma 故障时不得使用演示数据或内存索引伪造生产回答；查询只能返回无证据/不可用提示，并保留 PostgreSQL 事实与撤回能力。

## 发布后可观测性门禁

应用镜像发布后，在 `deploy` 目录执行 `bash scripts/post_release_gate.sh`。该脚本只检查本机回环接口的 `live`、`ready`、`ops` 和聚合 `/metrics`，不会打印业务响应或凭据。门禁失败默认停止并保留现场；仅在明确提供 `PREVIOUS_APP_IMAGE_TAG` 且设置 `ROLLBACK_ON_FAILURE=1` 时回滚应用进程，数据库和基础镜像不回滚。
