# ozonslj 开发云服务器上下文

> 本文只记录可复用部署事实和路径，不记录密码、私钥内容、数据库口令、Ozon 凭据、ACR 令牌或 Fernet 密钥内容。实际部署事实源来自已部署工作树的同名文档与 `DEPLOYMENT.md`。

## 1. 服务器与连接

- 开发云服务器：`root@8.148.215.217`。
- SSH 身份文件：`C:\Users\ashi7\.ssh\ozonslj_server`；自动化检查使用 `BatchMode=yes` 和 `IdentitiesOnly=yes`。
- 规格：Linux，2 核 CPU、2GB 内存、约 4GB Swap；Swap 仅作突发保护。
- 项目目录：`/opt/ozonslj/app`；Compose 入口：`/opt/ozonslj/app/deploy`。
- 公网只开放 Nginx 80；当前开发节点使用公网 IP + HTTP，正式数据进入前配置域名、HTTPS 和正式认证。

## 2. 已存在的服务与资源预算

| 服务 | 上限 | 已有约束 |
|---|---:|---|
| PostgreSQL 16 | 512MB | `max_connections=30`、`shared_buffers=128MB` |
| Redis 7.4 | 128MB | 数据上限 96MB、`noeviction` |
| API | 320MB | 单 Uvicorn Worker |
| Worker | 192MB | 单进程 |
| Nginx/Web | 64MB | 静态资源与反向代理 |

PostgreSQL 和 Redis 仅接入 Compose 内部网络。PostgreSQL 只把宿主机 `127.0.0.1:15432` 用于 SSH 隧道；Redis 不映射宿主机端口。

## 3. 已处理的数据库、Secret 与备份

- PostgreSQL 已是唯一业务数据库，API 与 Worker 使用同一套版本化迁移。
- `schema_migrations` 已记录版本和 SHA-256，历史迁移禁止修改；不要在本仓库重复设计第二套迁移账本。
- PostgreSQL 密码通过 Compose Secret 注入。
- Ozon Api-Key 已使用独立 Fernet 主密钥加密；密钥只读挂载到 API/Worker 的 `/run/secrets/ozon_credential_key`，不得与数据库密码复用。
- 备份目录：`/opt/ozonslj/backups`。
- 已有 `backup_postgres.sh`、`restore_postgres_drill.sh`、03:15 cron 模板和日志轮转模板；恢复演练创建隔离临时数据库，禁止覆盖运行库。
- 2026-08-04 只读核验发现：脚本和模板存在、备份目录中有 2026-07-31 与 2026-08-03 两份备份、cron 服务运行，但 `/etc/cron.d` 和 root crontab 尚未安装 ozonslj 任务。因此“每日自动备份”当前不能标记为生效；应安装已有模板后再观察下一次执行和日志轮转。

## 4. 只读检查顺序

登录服务器后先执行：

```bash
cd /opt/ozonslj/app/deploy
docker compose --env-file .env config --quiet
docker compose --env-file .env ps
curl -fsS http://127.0.0.1/api/health/live
curl -fsS http://127.0.0.1/api/health/ready
```

任何部署、迁移或容器重建前都必须先完成只读检查。不得输出 Secret，不得直接执行未进入版本化迁移的 DDL。

## 5. 发布方式

- 镜像由阿里云 ACR 构建，服务器只拉取，禁止在 2GB 节点本地构建。
- 发布顺序：本地检查 → 提交推送 → 等待 ACR → Compose 配置校验 → 拉取镜像 → 仅重建变更服务 → 健康、镜像摘要和日志核验。
- API/Worker 使用同一应用镜像；未修改 PostgreSQL、Redis、Nginx 时不得重建这些服务。

当前仓库新增开发不得重复设计平行迁移账本、备份体系或凭据密钥方案。状态判断必须区分“代码/模板已存在”“服务器已安装”“实际执行已验证”；当前仅备份定时任务安装仍有缺口。
## 2026-08-09 开发状态同步

- 云端部署继续沿用现有 PostgreSQL + Redis Compose 基线，不引入第二套数据库或 SaaS 组织开发任务。
- 当前需要外部授权的验证项是只读 Seller 账号、官方接口契约，以及 Worker/Scheduler 和备份恢复的只读 SSH 检查；Secret 不通过聊天传输。
- 已有备份方案优先复用；只有缺失项才按本项目文档补齐，恢复验证必须使用隔离数据库，不覆盖运行库。
