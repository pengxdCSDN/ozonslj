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
- `secrets/postgres_password`：仅包含 PostgreSQL 强随机密码，属主组为 `root:10001`，权限 `640`；
  组编号与容器内非 root 应用用户一致。
- `secrets/ozon_credential_key`：仅包含 Fernet 主密钥，供 API/Worker 加密 Ozon Api-Key；权限和属主组与
  PostgreSQL Secret 一致。该文件不得进入 Git、镜像、`.env` 或日志，也不得与数据库密码复用。

首次部署卖家账号功能前，在服务器的部署目录生成密钥文件：

```bash
cd /opt/ozonslj/app/deploy
install -d -m 700 secrets
docker compose --env-file .env run --rm --no-deps api \
  python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' \
  > secrets/ozon_credential_key
chown root:10001 secrets/ozon_credential_key
chmod 640 secrets/ozon_credential_key
```

生成后只检查文件存在、权限和非空，不要把密钥内容打印到终端或交接记录。`.env` 中的
`OZON_CREDENTIAL_KEY_VERSION` 初始为 `1`；后续轮换必须先设计旧版本解密与数据重加密流程，不能直接覆盖文件。

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

### 模型供应商凭据目录

模型供应商页面提交的 API Key 不进入 PostgreSQL，而是写入部署主机的
`secrets/rag-providers` 目录。首次启用模型供应商功能前，需要创建目录并授权给容器内
的 `appuser`（UID 10001）；API 与 Worker 必须同时挂载该目录。

```bash
cd /opt/ozonslj/app/deploy
install -d -m 700 secrets/rag-providers
chown 10001:10001 secrets/rag-providers
docker compose --env-file .env config --quiet
docker compose --env-file .env up -d --no-deps api worker
```

不要把该目录、其中的 `.key` 文件或 API Key 提交到 Git、写入镜像或输出到日志。


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
使用以下脚本执行自定义格式备份与隔离恢复演练：

```bash
bash /opt/ozonslj/app/deploy/scripts/backup_postgres.sh
bash /opt/ozonslj/app/deploy/scripts/restore_postgres_drill.sh \
  /opt/ozonslj/backups/ozonslj-YYYYMMDDTHHMMSSZ.dump
```

备份先写入临时文件并通过 `pg_restore --list` 验证，再原子改名；恢复演练创建独立临时
数据库，验证迁移和表数量后立即删除，绝不覆盖运行中的 `ozonslj` 数据库。

服务器安装 `deploy/cron/ozonslj-backup` 后，每天 03:15（Asia/Shanghai）执行一次互斥备份；
`deploy/logrotate/ozonslj-backup` 每周轮转任务日志并保留 8 份。定时任务只负责备份，恢复
演练仍应在结构升级前或至少每月人工执行并核对结果。

## 创建首个管理员账号

系统不提供公网注册入口。部署并完成数据库迁移后，在服务器上通过 API 容器交互式创建或更新管理员账号：

```bash
cd /opt/ozonslj/app/deploy
docker compose --env-file .env exec api \
  python /app/scripts/create_operator.py \
  --email admin@example.com \
  --display-name 管理员 \
  --role admin
```

密码至少 12 位，并在终端中隐藏输入。未指定 `--workspace` 时，`admin` 自动获得全部已启用工作区权限。

如果旧应用镜像尚未包含 `/app/scripts/create_operator.py`，可先从服务器仓库临时复制脚本，再执行同一命令：

```bash
docker compose cp ../scripts/create_operator.py api:/tmp/create_operator.py
docker compose --env-file .env exec -e PYTHONPATH=/app api \
  python /tmp/create_operator.py \
  --email admin@example.com \
  --display-name 管理员 \
  --role admin
```

该临时文件会随容器重建消失；后续镜像必须通过 Dockerfile 将脚本复制到 `/app/scripts/create_operator.py`。

## 发布流程

1. 代码检查通过后推送 Git 分支或发布标签。
2. 阿里云 ACR 使用仓库根目录 `Dockerfile` 从指定 Git 引用构建应用镜像。
3. 服务器只从 ACR 拉取镜像，不在 2GB 服务器本地构建。
4. 先执行 `docker compose config`，再拉取并启动。
5. 验证健康检查、数据库迁移、容器日志和外部 HTTP 访问。

正式发布应使用不可变版本标签或镜像摘要；`dev` 标签仅用于当前开发节点。

### 推送并重建 API/Worker

云服务器为 2 核 2 GB，应用镜像统一由阿里云 ACR 自动构建；服务器只拉取镜像，不在本机执行 Docker 构建。一次可复现的发布顺序如下：

1. 本地完成检查、提交并推送目标分支。
2. 登录服务器，确认 `/opt/ozonslj/app` 工作树干净，再执行 `git pull --ff-only`。
3. 在 `/opt/ozonslj/app/deploy` 执行 `docker compose --env-file .env config --quiet`。
4. 等待 ACR 自动构建完成，然后执行 `docker compose --env-file .env pull api worker`。
5. 不要只根据可变的 `dev` 标签判断发布成功。使用 `docker image inspect` 核对镜像创建时间和摘要，并在镜像内检查本次发布的关键文件；若仍是旧镜像，等待 ACR 构建结束后重新拉取。
6. 重建应用进程：`docker compose --env-file .env up -d --no-deps api worker`。API 容器重建后可能获得新的 Compose 网络 IP，必须随后执行 `docker compose --env-file .env restart web`，让 Nginx 重新解析 API upstream；不能只重建 API/Worker。
7. 核对 API 与 Worker 的镜像摘要一致，并验证容器状态、`/api/health/live`、`/api/health/ready`、登录/关键 API、启动日志和公网静态资源。健康检查失败或出现 502 时，先检查 Web 容器日志中的 upstream 地址，再重启 Web 刷新解析。

推荐的服务器命令：

```bash
cd /opt/ozonslj/app
git status --short
git pull --ff-only

cd deploy
docker compose --env-file .env config --quiet
docker compose --env-file .env pull api worker
docker image inspect "$APP_IMAGE" --format '{{.Id}} {{.Created}}'
docker compose --env-file .env run --rm --no-deps api test -f /app/path/to/release-marker.py
docker compose --env-file .env up -d --no-deps api worker
docker compose --env-file .env restart web
docker compose --env-file .env ps
docker inspect -f '{{.Config.Image}} {{.Image}}' ozonslj-api-1 ozonslj-worker-1
curl -fsS http://127.0.0.1/api/health/live
curl -fsS http://127.0.0.1/api/health/ready
docker compose --env-file .env logs --tail=100 api worker
```

其中 `$APP_IMAGE` 使用 `.env` 中的应用镜像完整地址；`release-marker.py` 替换为本次版本必然包含的关键文件。发布结束后还应请求公网首页，核对 HTML 引用的新 JS/CSS 哈希文件均返回 `200`。
## Web 静态资源发布防复发规则

2026-08-14 黑屏故障的直接原因是首页引用了新的哈希 JS 文件，但 Nginx 实际目录没有该文件；Nginx 的 `try_files` 将缺失的 JS 回退成 `index.html`，浏览器收到 `text/html` 后拒绝执行模块脚本。另一个易错点是 Docker Web 容器绑定了宿主机目录，普通 `restart` 不会修复错误的目录切换。

发布 Web 时必须遵守以下顺序：

1. 使用 `vite build --mode web` 生成完整目录，不能只上传 `index.html` 或单个 assets 文件。
2. 将整个构建目录上传到 `web.next`，先检查 `index.html` 引用的每一个 `/assets/*` 文件都存在。
3. 保留当前目录作为带时间戳的回滚目录，再将 `web.next` 原子改名为 `web`；不要依赖“目录已存在”的条件判断，否则失败后会留下未切换的暂存目录。
4. 执行 `docker compose --env-file .env up -d --force-recreate --no-deps web`，让绑定目录在容器内明确刷新。
5. 发布后必须同时验证首页引用的 JS/CSS：状态码为 `200`，JS 为 `application/javascript`，CSS 为 `text/css`；任一资源返回 `text/html` 都视为发布失败并立即回滚。

本次线上已恢复为当前构建版本，并保留上一版目录用于回滚。浏览器端如仍显示旧错误，使用 `Ctrl+F5` 清除旧的首页缓存后重新打开。
