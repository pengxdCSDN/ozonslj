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

### 应用镜像与 Web 前端的分工

- `ozonslj-api-dev` 只承载 API、Worker 和 Scheduler 的 Python 代码；后端代码变更只需要触发该应用镜像构建。
- Web 服务通过 `./web:/usr/share/nginx/html:ro` 挂载 `deploy/web` 静态目录；前端页面不会因为 API 镜像更新而自动出现。
- 前端页面或样式变更必须在 `extension` 执行 `vite build --mode web`，将生成的 `index.html` 与完整 `assets/` 目录同步到 `deploy/web`，提交并推送后在服务器执行 Web 静态目录更新和 `--force-recreate --no-deps web`。
- ACR 基础镜像规则不应与应用代码提交绑定。应用分支自动构建只保留 `ozonslj-api-dev`；PostgreSQL、Redis、Nginx、Python、Node、Chroma 基础镜像改为独立分支/Tag 或手动构建。
- 发布验收必须分别检查 API 镜像摘要和 Web 首页引用的 JS/CSS 哈希；只验证 API 健康不能证明新增前端页面已发布。
## Web 静态资源发布防复发规则

2026-08-14 黑屏故障的直接原因是首页引用了新的哈希 JS 文件，但 Nginx 实际目录没有该文件；Nginx 的 `try_files` 将缺失的 JS 回退成 `index.html`，浏览器收到 `text/html` 后拒绝执行模块脚本。另一个易错点是 Docker Web 容器绑定了宿主机目录，普通 `restart` 不会修复错误的目录切换。

发布 Web 时必须遵守以下顺序：

1. 使用 `vite build --mode web` 生成完整目录，不能只上传 `index.html` 或单个 assets 文件。
2. 将整个构建目录上传到 `web.next`，先检查 `index.html` 引用的每一个 `/assets/*` 文件都存在。
3. 保留当前目录作为带时间戳的回滚目录，再将 `web.next` 原子改名为 `web`；不要依赖“目录已存在”的条件判断，否则失败后会留下未切换的暂存目录。
4. 执行 `docker compose --env-file .env up -d --force-recreate --no-deps web`，让绑定目录在容器内明确刷新。
5. 发布后必须同时验证首页引用的 JS/CSS：状态码为 `200`，JS 为 `application/javascript`，CSS 为 `text/css`；任一资源返回 `text/html` 都视为发布失败并立即回滚。

本次线上已恢复为当前构建版本，并保留上一版目录用于回滚。浏览器端如仍显示旧错误，使用 `Ctrl+F5` 清除旧的首页缓存后重新打开。

## 2026-08-16 RAG 正式调用发布记录

- 本地提交 `0bf82d6` 已推送到 `codex/deployment-base-images`；后端 501 项测试、前端类型检查和 Vite 构建通过。
- 云端 API、Worker、Scheduler 运行正常，`ready/live` 均返回 200；但 ACR `ozonslj-api-dev` 多次拉取仍为旧摘要 `sha256:c3a75f06bd6c...`，未包含 `0bf82d6`。
- 服务器上的 `aliyun` CLI 默认配置状态为 `Invalid`，当前无法从服务器触发 ACR 构建；禁止在 2GB 服务器本地构建替代。新功能的云端发布验收须在 ACR 构建任务恢复后，以新摘要重拉镜像并重新执行本节验收。

## 2026-08-16 严重发布事故与防复发规则

本次事故根因不是应用代码，而是发布控制面未锁定：开发提交只推送到
`codex/deployment-base-images`，但未先确认 ACR 构建规则实际跟踪的 Git 分支；随后错误地将开发分支快进到
`main`，并在未确认 ACR 摘要变化的情况下重复拉取旧镜像。该误操作已恢复，`main` 回到 `709b39d`，开发提交仍只保留在 `codex/deployment-base-images`。

今后发布必须满足以下硬门禁：

1. 发布前打印并人工核对 `git branch --show-current`、远端分支和 `git rev-parse HEAD`；本项目发布分支固定为 `codex/deployment-base-images`，禁止把它直接推到 `main`。
2. ACR 构建触发必须使用该分支的构建规则；没有构建规则、有效 RAM 权限或构建记录时，立即停止，不把服务器 `git checkout` 当成镜像发布。
3. 拉取后必须核对镜像 digest、创建时间和镜像内 release revision；digest 未变化时禁止 `up -d`、禁止验收、禁止报告“已发布”。
4. 发布前后记录 `source_commit`、`image_digest`、`image_created_at`、API/Worker/Scheduler 状态；source commit 与镜像内 revision 不一致即失败关闭。
5. Git HTTPS 后端切换只能作为一次性受控命令，并在命令结束恢复原配置；禁止把认证失败误判为 ACR 构建失败。
6. 任何分支误推、旧摘要验收或未授权本地构建都视为严重发布事故，必须先恢复远端分支和服务，再更新本记录。

## 2026-08-16 RAG 正式调用最终发布验收

- ACR 应用镜像规则：`branches:codex/deployment-base-images` → `/Dockerfile` → `ozonslj-api-dev`。
- 最新镜像摘要：`sha256:c20547a493758ec73baf5e7104012444802e63002e8153e579012060be63e01b`。
- API、Worker、Scheduler 均运行；API/Worker 摘要一致，API healthy，Worker 不再重启。
- `ready=200`、`live=200`；`/api/health/rag` 返回 `state=healthy`。
- 数据库迁移最高版本 `105`；翻译预算迁移使用唯一源版本 `0102`，未修改历史迁移账本。

## 2026-08-16 知识管理页面增强发布验收

- 发布分支：`codex/deployment-base-images`；应用提交：`71d608d`。
- ACR 新应用镜像已生成并拉取，摘要：`sha256:c7550560d9f4c890f073c54e66f0644f9c1d99df00b5e07a9ce4d6ecbdca3608`。
- API、Worker、Scheduler 均已重建并统一使用该摘要；API 容器已确认包含 `rebuild_knowledge_version` 路由。
- API `ready=200`、`live=200`；API 状态 healthy；Web 静态入口引用 `index-DOqz1CRb.js`；Nginx `nginx -t` 通过。
- 本次只更新应用代码镜像和已构建 Web 静态资源，没有重建 PostgreSQL、Redis、Chroma 等基础服务。
- PDF 仍遵守安全门禁：当前支持隔离上传和结构校验；未配置杀毒服务时状态为 `quarantined`，不能宣称已完成二进制 PDF 自动解析。文本层 PDF 需先提取文本再进入知识解析流水线。

## 2026-08-16 PDF 安全上传状态流程发布验收

- 应用提交：`171c88d`；ACR 应用镜像摘要：`sha256:a182dc7ec8a10bc012d8202375d22a3f4bfd05a306e5798dcff4fc7e4ba93516`。
- API、Worker、Scheduler 已统一使用新摘要；API healthy，`ready=200`、`live=200`。
- Web 入口已更新为 `index-BDRFAGDq.js`；Web 容器运行正常，Nginx 配置检查通过。
- 页面现在会调用 PDF 隔离上传接口并展示结构检查、杀毒状态和阻断原因；未配置杀毒服务时保持 `quarantined`，禁止自动解析二进制 PDF。
- 应用镜像新增 Python 依赖时，Dockerfile 必须在安装项目后执行关键依赖 import 校验；依赖缺失必须使 ACR 构建失败，禁止把“健康但功能缺依赖”的镜像部署到云端。

## 2026-08-16 第四组知识管理功能最终验收

- 应用提交：`1bf19d7`；ACR 应用镜像摘要：`sha256:9670cfba1069f0ede6d2c59e0e1dcbb05547fd4370415cc78c3e3a72b575eedd`。
- API、Worker、Scheduler 已统一该摘要；容器内 `pypdf` 依赖验证通过，索引重建路由存在。
- API `ready=200`、`live=200`；Web 入口为 `index-DvaBd6Db.js`；Nginx 配置检查通过。
- 第四组功能已完成发布：来源筛选、版本详情、Markdown/SQL/TXT/PDF 文本层导入、解析切片预览、质量门禁、发布/撤回/删除/重建、任务轮询、取消/重试和版本内容一致性校验。
