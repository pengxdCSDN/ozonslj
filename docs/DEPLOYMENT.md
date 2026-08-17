# ozonslj Linux 部署说明

稳定构建流程见 [`ACR_STABLE_BUILD_FLOW.md`](./ACR_STABLE_BUILD_FLOW.md)。本文件保留运行时部署细节；ACR 规则、源码一致性和失败门禁以稳定流程为准。

基础镜像规则已准备独立 Git Tag：`base-postgres-v1`、`base-redis-v1`、`base-nginx-v1`、`base-python-v1`、`base-node-v1`、`base-chroma-v1`，均指向 `afd375a`；ACR 中分别使用 `tags:` 前缀引用。

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

## 2026-08-17：RAG 评测结果页发布记录

- 目标分支：`codex/deployment-base-images`
- 应用提交：`15ffee8`
- ACR 应用镜像摘要：`sha256:c90d073561c9fc6c4c8691f9952abde586724d1080b38618a479900943b95860`
- API、Worker、Scheduler 已统一该摘要并处于运行状态。
- Web 静态资源：`index-UodWbXQk.js`、`index-CBpUfkUt.css`，HTTPS 资源均返回 200。
- `/api/health/live`、`/api/health/ready` 返回 200；应用导入检查通过；结果 API 未登录时正确返回 401。
- 本次包含 PostgreSQL 迁移 `0103_rag_evaluation_results.sql`，用于保存评测运行进度和脱敏指标快照。
- 服务器 ACR CLI 曾返回无效 AccessKey；本次由 GitHub 分支自动构建生成新摘要，未在云服务器本地构建镜像。

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

## 2026-08-17 OCR 扫描 PDF 分流与部署流程

- 应用提交：本次 OCR 功能提交以 Git 记录为准；发布前必须确认分支为 `codex/deployment-base-images`。
- 普通文本层 PDF 不调用 OCR；扫描 PDF 仅在配置 PaddleOCR HTTPS 端点时调用 `paddleocr-doc-parsing` 适配器，未配置时返回 `ocr_required`。
- OCR 供应商令牌只通过运行时 Secret 或 `PADDLEOCR_ACCESS_TOKEN_FILE` 注入；不得写入仓库、镜像、前端或日志。
- ACR 构建完成后核对 source commit、镜像 digest、镜像内 `backend/app/infrastructure/ocr/paddleocr_document_parser.py` 和 API/Worker/Scheduler 摘要一致，再执行云端健康检查。
- 云端验收至少覆盖：文本层 PDF 不调用 OCR、扫描 PDF 配置缺失阻断、OCR 成功/超时/429/403、切片预览和发布门禁。没有真实 OCR 凭据时，不能报告“真实 OCR 调用通过”，只能报告检测与安全阻断通过。

## 2026-08-16 第五组 RAG 供应商能力验收

- 应用提交：`59588c5`；ACR 应用镜像摘要：`sha256:6663533ac2da95bdb36f658ad1241c9d485ea58bb09bf7047efaaafb2d951d0c`。
- 已验证容器内 `timeout-class=ok`、`pypdf=ok`；API `ready=200`；API/Worker/Scheduler 统一该摘要。
- Web 入口保持 `index-DvaBd6Db.js`，Nginx 配置检查通过。
- 本阶段完成无真实凭据可验收的适配器、维度、错误分类、主备降级、预算/usage 和故障注入闭环；真实供应商账号接入后只需补真实调用验收。

## 2026-08-16 第四组知识管理功能最终验收

- 应用提交：`1bf19d7`；ACR 应用镜像摘要：`sha256:9670cfba1069f0ede6d2c59e0e1dcbb05547fd4370415cc78c3e3a72b575eedd`。
- API、Worker、Scheduler 已统一该摘要；容器内 `pypdf` 依赖验证通过，索引重建路由存在。
- API `ready=200`、`live=200`；Web 入口为 `index-DvaBd6Db.js`；Nginx 配置检查通过。
- 第四组功能已完成发布：来源筛选、版本详情、Markdown/SQL/TXT/PDF 文本层导入、解析切片预览、质量门禁、发布/撤回/删除/重建、任务轮询、取消/重试和版本内容一致性校验。

## 2026-08-16 第六组选品与 Listing 开发验收记录

- 发布分支固定为 `codex/deployment-base-images`；本阶段只更新应用代码和 Web 静态资源，不重建 PostgreSQL、Redis、Chroma 等基础镜像。
- 已完成可脱离真实 Seller 凭据开发的功能：商品机会评分与筛选条件、关键词库、Listing 草稿建议、风险检测、版本差异和人工确认门禁。
- Explore 新增最低机会分、最低搜索量、最低转化率和自有覆盖缺口筛选；筛选发生在确定性评分之后，保存结果仍保留估算标记和理由。
- 受控发布仍是 Stub/审核链路：必须有审核状态和幂等键，只记录命令及回读；真实 Seller 写接口、字段契约和真实店铺发布验收不得在无店铺凭据时伪造。
- 验证：第六组后端 API/领域回归 8 项通过；前端 TypeScript 检查通过；Vite Web 构建通过，入口为 `index-f8CZ4J6r.js`，样式为 `index-DxjgRheu.css`。
- ACR 发布前门禁：提交并推送后必须等待 ACR 使用本分支生成新应用镜像，核对新 digest、镜像内 revision、API/Worker/Scheduler 一致性，再执行云端验收；digest 未变化时不得报告发布完成。

## 2026-08-16 第六组最终云端验收

- 目标提交：`d4416ed2f43a126913fcc2061904251b4adc821a`；服务器工作树已同步到 `origin/codex/deployment-base-images`。
- ACR 第二次构建摘要：`sha256:9f02f4c007fffc74257dbf8904e1a96460da9e8461de3a9b6f3214e6a25f88ec`；第一次构建虽有新摘要但仍为旧源码，已按门禁拒绝验收。
- 镜像内已确认 `ExploreFilters`、`min_search_count` 和 `filter_opportunities` 存在；容器内 `/v1/selection/explore/run` 实测按 `min_search_count=900` 与 `coverage_gap_only=true` 只返回覆盖缺口候选。
- API、Worker、Scheduler 均运行且统一上述摘要；API health 为 `healthy`，容器内 `health/ready=200`；Web 已重建，入口为 `index-f8CZ4J6r.js`，资源在容器内存在，`nginx -t` 通过。
- PostgreSQL、Redis、Chroma 等基础服务未重建。公网 HTTPS 由服务器外层入口负责，服务器本机无 443 映射，因此本机 HTTPS 回环状态为 000；这不是应用容器故障，公网入口需从浏览器侧确认。

## 2026-08-16 第七组受控写入验收

- 本阶段没有新增应用代码，复用已发布应用镜像完成验收；因此未重复构建基础镜像。
- 本地第七组回归 32 项通过：差异预览、新鲜度、人工审批、权限、幂等、批量限制、涨跌幅、利润线、分项结果、回读和审计均通过。
- 云端镜像内 `validate_approval_request`、`build_diff_preview`、`summarize_execution` 和 `create_audit_event` 导入检查通过；API `ready=200`。
- API、Worker、Scheduler 统一使用 `sha256:629976c612d2afd5bc057e531d55ac23aafde7fe60e8232554c5ae11db65f893`。
- 真实 Seller 写入仍未执行；当前验收证明的是审批、门禁、幂等、审计和 Stub 命令闭环，不代表真实 Ozon 写入已完成。

## 2026-08-16 第八组智能分析与 Agent 验收

- 本阶段无新增应用代码，复用已验收应用镜像；不重复构建 PostgreSQL、Redis、Chroma 或应用镜像。
- 本地第八组回归 44 项通过，覆盖只读运营分析、商品/库存/订单/广告联合分析、竞品/选品分析、汇总报告、RAG 引用与无证据拒答、Agent 编排、权限拒绝、高风险工具拒答、触发器和审计。
- 云端容器内 Agent 编排、权限、触发和通知预览模块导入检查通过；API `ready=200`。
- API、Worker、Scheduler 统一使用 `sha256:629976c612d2afd5bc057e531d55ac23aafde7fe60e8232554c5ae11db65f893`。
- 外部通知仅完成配置校验与预览闭环，未配置真实渠道凭据，因此没有执行真实发送；Seller 实时数据分析和真实通知发送待外部授权后验收。
- 后续发布必须继续遵守：先核对发布分支和源码提交，再核对镜像摘要/镜像内 revision，最后检查 API、Worker、Scheduler 一致性；摘要未变化不得宣称新版本发布。

## 2026-08-16 第九组 Performance 广告 Stub/只读验收

- 本地第九组后端回归 33 项通过；前端 TypeScript 检查通过，Vite Web 构建通过，入口为 `index-AseVkSlj.js`，样式为 `index-DxjgRheu.css`。
- 已完成广告活动、关键词/否定词、指标导入、指标计算、异常诊断、30 天建议日历、阈值版本和只读边界。
- 新增广告预算只读分析 API：按预算周期计算利用率、预计消耗和风险状态，禁止自动修改预算、出价或关键词。
- Performance OAuth 错误已区分 `performance_oauth_failed` 与 `performance_permission_denied`；凭据状态保持与 Seller 凭据隔离，令牌和密钥不回显。
- 本阶段需要代码镜像和 Web 静态资源更新；发布前必须使用 `codex/deployment-base-images` 触发 ACR，等待新摘要，核对镜像内源码提交、API/Worker/Scheduler 一致性和 Web 哈希资源后再验收。真实 Performance 授权仍待外部账号权限。

### 第九组当前发布阻塞记录

- 目标提交：`de90e07`，已推送到 `codex/deployment-base-images`。
- ACR 曾生成新摘要 `sha256:b0aee5f44831a62458339adb8fc5a070002ad82308becf4b42146399204eda4a`，但镜像内缺少 `backend/app/domain/advertising_budget.py`，`OZONSLJ_RELEASE_REVISION` 仍为 `development`，证明该构建未使用目标源码。
- 服务器当前已确认源码远端提交为 `de90e07`，但不能用服务器源码同步替代 ACR 构建证据；API/Worker/Scheduler 未以该错误镜像作为第九组验收结果。
- ACR 控制台读取超时、服务器 `aliyun` CLI 无有效权限；禁止在 2GB 服务器本地构建或继续重启旧摘要。下一步必须在 ACR 构建规则中手动确认 source branch=`codex/deployment-base-images`、source commit=`de90e07`，重新构建后再执行镜像内文件、revision、服务摘要和 API/Web 验收。

## 2026-08-16 第九组最终发布验收

- ACR 最新应用镜像摘要：`sha256:bbfaeca85483d0689b22faf2a869c2c4eaa5ee6e7024bee4193de6494d6032c0`，镜像内已确认 `advertising_budget.py` 存在。
- API、Worker、Scheduler 已统一切换到该摘要；API 容器内 `live=200`、`ready=200`，三项服务运行正常。
- Web 已完整同步 `index.html` 与 `assets/`，入口为 `index-AseVkSlj.js`，样式为 `index-DxjgRheu.css`；`nginx -t` 通过，静态文件在容器内存在。
- PostgreSQL、Redis 未重建；旧 Web 静态目录保留为 `web.rollback-group9-20260816`，可用于回滚。
- 服务器本机 HTTP 按配置返回 HTTPS 301，公网 TLS 由外层入口负责；本机无 443 映射，不将本机 HTTPS 000 误判为应用容器故障。

## 2026-08-16 第十组可观测性与运维验收

- API 已提供聚合 `/metrics`，覆盖请求状态/耗时、模型调用错误/耗时、Scheduler 投递、Seller/RAG Worker 处理量和内存/Swap/磁盘资源。
- `/health/ops` 作为资源检查端点；磁盘使用率达到 85% 只返回 `warning`，不阻断登录和只读运营页面。
- 新增 `deploy/scripts/post_release_gate.sh`：发布后检查 Compose 配置、live/ready/ops 和指标出口；失败默认保留现场，显式提供上一版应用标签并设置 `ROLLBACK_ON_FAILURE=1` 才执行应用回滚。
- 请求日志和指标只保留受控路由、状态和聚合数值，不记录查询参数、请求体、Cookie、令牌、模型提示词或响应正文。业务审计继续由 PostgreSQL 审计事件和归档流程负责。
- 本地可观测性与健康回归通过；全量云端验收需在新 ACR 镜像发布后执行上述门禁脚本。

## 2026-08-16 HTTPS 入口修复验收

- 根因：Nginx 配置已监听 443 并挂载服务器 TLS 证书，但 Compose 的 Web 服务长期只映射 `80:80`，导致 HTTP 301 跳转到没有宿主机监听的 HTTPS 端口。
- 修复提交：`b53c027`，Web 服务增加宿主机 `443:443` 映射；PostgreSQL、Redis、API、Worker、Scheduler 和基础镜像未重建。
- 云端已同步 `codex/deployment-base-images`，Web 容器已强制重建；宿主机 80/443 均监听，Nginx `-t` 通过。
- 本机 TLS 验收：首页 `200 text/html`，新 JS `200 application/javascript`，新 CSS `200 text/css`；阿里云安全组已有 TCP 443 放行规则。
- 历史上“HTTPS 可用”的前提是外层 TLS 入口或其他临时映射存在；当前 Compose 的明确配置现在与 Nginx TLS 配置一致，后续不得只检查安全组而忽略宿主机端口映射。

### 第十组云端最终验收

- ACR 新应用镜像摘要：`sha256:e2cde1e36edbf00876f6bba367f40cf2bc5534694ca9e40e46f6915b68d5367b`，创建时间晚于提交 `0a7fc44`；镜像内可导入可观测性模块。
- API、Worker、Scheduler 已统一该摘要并运行；API `live=200`、`ready=200`、`ops=200`。
- `/metrics` 已返回请求计数、请求耗时、磁盘使用率和内存可用量；Worker/Scheduler 可导入可观测性模块。
- 云端资源检查：磁盘使用率约 `45.15%`，内存和 Swap 可读，`ops.status=ok`；Nginx `-t` 通过，HTTPS 首页 `200 text/html`。
- PostgreSQL、Redis、Chroma 和基础镜像未重建；服务器既有 Web 静态回滚目录/工作树变更已保留，未强制 checkout 或清理。
