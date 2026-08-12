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
