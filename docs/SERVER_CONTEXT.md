# ozonslj 云服务器上下文

> 用途：供后续 Codex 会话恢复云端部署上下文。本文禁止记录密码、私钥、数据库口令、Ozon 凭据、ACR 令牌或密钥文件内容。

## 事实来源

- 当前已确认需求：`docs/REQUIREMENTS_V4.md`
- 当前架构评审稿：`docs/ARCHITECTURE_V4.md`
- 部署操作说明：`docs/DEPLOYMENT.md`
- PostgreSQL 事实结构：`database/postgres/migrations/`
- 交接文件：`C:\Users\ashi7\AppData\Local\Temp\ozonslj-handoff-2026-08-03.md`

## 正确开发基线

- 工作树：`C:\Users\ashi7\.codex\worktrees\1c6c\ozonslj`
- 分支：`codex/deployment-base-images`
- 交接时提交：`5b8ee1f`（`ops: 配置数据库定时备份与日志轮转`）
- PostgreSQL 是唯一业务数据库；禁止恢复 SQLite 运行链路或维护第二套 DDL。
- 继续开发前必须检查工作树状态并保留所有未提交修改。

## 服务器与部署

- 运行环境：Linux 云服务器，2 核 CPU、2GB 内存，已有约 4GB Swap。
- 部署方式：Docker Compose。
- 服务器项目目录：`/opt/ozonslj/app`。
- PostgreSQL 备份目录：`/opt/ozonslj/backups`。
- 主机密钥目录：`/opt/ozonslj/secrets`，权限应保持为 `700`。
- 应用部署目录还包含未纳入 Git 的 `deploy/secrets/ozon_credential_key`，由 Compose 只读挂载到
  API/Worker 的 `/run/secrets/ozon_credential_key`；只记录路径、权限和版本，不记录密钥内容。
- Compose 入口：`/opt/ozonslj/app/deploy`。
- 当前开发节点通过公网 IP + HTTP 访问；内部试用或正式数据进入前必须配置域名、HTTPS 和正式认证。

## 容器组成与资源预算

| 服务 | 资源上限 | 说明 |
|---|---:|---|
| PostgreSQL 16 | 512MB | `max_connections=30`，`shared_buffers=128MB` |
| Redis 7.4 | 128MB | 数据上限 96MB，`noeviction` |
| API | 320MB | 单 Uvicorn Worker |
| Worker | 192MB | 单进程，后续执行同步任务 |
| Nginx/Web | 64MB | 静态资源与反向代理 |

## 网络与安全边界

- 公网只开放 Nginx 的 80 端口。
- PostgreSQL 和 Redis 只接入 Compose 内部网络，不开放公网。
- PostgreSQL 的宿主机 `127.0.0.1:15432` 只用于 SSH 隧道。
- Redis 不映射宿主机端口。
- API 与 Worker 可访问外部网络，以便后续调用 Ozon API。
- PostgreSQL 密码通过 Compose Secret 文件注入，不进入仓库、镜像或普通环境变量。
- Ozon Api-Key 使用独立 Fernet 主密钥加密；主密钥同样通过 Compose Secret 文件注入，禁止与 PostgreSQL
  密码复用，禁止输出到命令日志或交接文档。
- 不在命令输出、交接或日志中记录服务器密码、数据库密码、私钥路径内容或业务凭据。

## 常用只读验证

登录服务器后：

```bash
cd /opt/ozonslj/app/deploy
docker compose --env-file .env config --quiet
docker compose --env-file .env ps
curl -fsS http://127.0.0.1/api/health/live
curl -fsS http://127.0.0.1/api/health/ready
```

运行任何变更命令前，先完成以上只读检查。不得直接在生产数据库执行未经迁移文件记录的 DDL。

## 迁移、备份与恢复

- API 与 Worker 使用同一套版本化 PostgreSQL 迁移。
- `schema_migrations` 保存版本和校验和；历史迁移禁止修改。
- 结构升级前必须创建备份并验证。
- 每天 03:15（Asia/Shanghai）执行 PostgreSQL 自定义格式备份。
- 本地备份保留 14 天；开发阶段接受服务器与备份同时丢失的单点风险。
- 恢复演练必须创建隔离临时数据库，不得覆盖运行中的 `ozonslj` 数据库。

```bash
bash /opt/ozonslj/app/deploy/scripts/backup_postgres.sh
bash /opt/ozonslj/app/deploy/scripts/restore_postgres_drill.sh \
  /opt/ozonslj/backups/ozonslj-YYYYMMDDTHHMMSSZ.dump
```

## 发布约束

- 镜像由阿里云 ACR 从指定 Git 引用构建；2GB 服务器不本地构建镜像。
- 使用不可变版本标签或镜像摘要；`dev` 仅用于开发节点。
- 发布顺序：代码检查 → 构建/推送镜像 → Compose 配置校验 → 拉取 → 重建 → 健康检查 → 迁移/日志核验。
- 部署前核对运行镜像是否包含提交 `d8f364d` 之后的金额格式修复。

## SSH 连接入口

服务器连接命令：

```bash
ssh -i C:\Users\ashi7\.ssh\ozonslj_server root@8.148.215.217
```

已授权公钥文件为 `C:\Users\ashi7\.ssh\ozonslj_server.pub`。优先使用
`BatchMode=yes` 和 `IdentitiesOnly=yes` 执行自动化检查。不要在本文记录密码、私钥内容或带凭据的 URL。
