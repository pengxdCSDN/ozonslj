# ozonslj Linux 部署说明

## 部署边界

当前节点使用 Docker Compose 部署 PostgreSQL、Redis、API、Worker 与 Nginx/Web 骨架。
运行时和后续开发均以 PostgreSQL 为唯一关系数据库，不提供 SQLite 回退路径。

- 公网只开放 Nginx 的 `80` 端口。
- PostgreSQL 和 Redis 只接入 Compose 内部网络，不映射公网端口。
- API 与 Worker 额外接入出站网络，用于后续访问 Ozon API；PostgreSQL 和 Redis 不接入该网络。
- PostgreSQL 的 `15432` 仅绑定服务器 `127.0.0.1`，只允许通过 SSH 隧道访问。
- PostgreSQL 密码通过 Compose Secret 文件注入，不写入镜像、仓库或环境变量。
- 当前没有域名，暂时通过公网 IP 和 HTTP 访问；接入域名后再启用 HTTPS。
- Chroma、LangChain 和 LangGraph 在智能体切片开始时加入，不占用当前节点资源。

## 服务器目录

```text
/opt/ozonslj/
├── app/                    # 仓库检出目录
├── backups/                # PostgreSQL 备份
└── secrets/                # 主机密钥材料，权限 700
```

部署时在 `app/deploy` 下创建以下未纳入 Git 的文件：

- `.env`：镜像仓库前缀与应用镜像标签。
- `secrets/postgres_password`：仅包含 PostgreSQL 强随机密码，文件权限 `600`。

## 资源预算

| 服务 | 内存上限 | 说明 |
| --- | ---: | --- |
| PostgreSQL 16 | 512 MB | 连接数 30，共享缓冲区 128 MB |
| Redis 7.4 | 128 MB | 数据上限 96 MB，`noeviction` |
| API | 320 MB | 单 Uvicorn Worker |
| Worker | 192 MB | 单进程依赖检查骨架 |
| Nginx/Web | 64 MB | 静态页面与反向代理 |

服务器已有 4GB Swap，但 Swap 只作为突发保护，不作为常态容量。

## 启动与验证

```bash
cd /opt/ozonslj/app/deploy
docker compose --env-file .env config
docker compose --env-file .env pull
docker compose --env-file .env up -d
docker compose --env-file .env ps
curl -fsS http://127.0.0.1/api/health/live
curl -fsS http://127.0.0.1/api/health/ready
```

PostgreSQL 首次启动后，API 和 Worker 会执行同一套版本化迁移。迁移使用
`schema_migrations` 校验历史版本及校验和，并在事务失败时回滚。

## 备份与恢复

备份文件写入 `/opt/ozonslj/backups`，至少保留最近 7 份。正式业务数据进入系统前，
需要补充定时 `pg_dump --format=custom`、过期清理和恢复演练脚本。

## 发布流程

1. 代码检查通过后推送 Git 分支或发布标签。
2. 阿里云 ACR 使用仓库根目录 `Dockerfile` 从指定 Git 引用构建应用镜像。
3. 服务器只从 ACR 拉取镜像，不在 2GB 服务器本地构建。
4. 先执行 `docker compose config`，再拉取并启动。
5. 验证健康检查、数据库迁移、容器日志和外部 HTTP 访问。

正式发布应使用不可变版本标签或镜像摘要；`dev` 标签仅用于当前开发节点。
