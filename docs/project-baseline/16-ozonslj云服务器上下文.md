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

## 2026-08-15 前后端部署操作手册

本节是当前项目的标准发布闭环，适用于前端静态资源和后端 API/Worker 镜像一起发布。所有命令均不得把密码、API Key、访问令牌或 `.env` 内容复制到聊天、日志或 GitHub。

### A. 发布前：本地代码与文档

1. 确认工作树和目标提交：`git status --short`、`git log -1 --oneline`；只处理本次变更，不覆盖用户已有未跟踪目录。
2. 执行前端类型检查和 Web 构建：
   - `extension\node_modules\.bin\tsc.CMD -b extension\tsconfig.json --pretty false`
   - `Set-Location extension; .\node_modules\.bin\vite.CMD build --mode web --configLoader runner --outDir ..\deploy\web --emptyOutDir true`
3. 执行后端相关测试、Ruff/mypy、schema 校验和 `git diff --check`；构建失败不得发布。
4. 检查 `deploy/web/index.html` 引用的 JS/CSS 文件确实存在，避免静态入口引用旧哈希文件。
5. 提交代码、`docs/` 项目基线和必要的 `deploy/web` 产物；明确排除 `.env`、凭据、数据库、诊断日志和临时构建目录。
6. 推送目标分支并核对远端 SHA：`git ls-remote origin refs/heads/main refs/heads/codex/deployment-base-images`。

### B. 前端静态资源发布

1. 服务器发布前先执行第 4 节的 Compose 配置和健康检查。
2. 将 `deploy/web/index.html` 上传到 `/opt/ozonslj/app/deploy/web/`，将 `deploy/web/assets/` 内容上传到对应 assets 目录；上传后设置目录 `755`、文件 `644`。
3. 用 `curl -I http://127.0.0.1/` 检查入口，用 `curl -I http://127.0.0.1/assets/<实际文件名>.js` 检查 JS 返回 `Content-Type: application/javascript`，CSS 返回 `text/css`。
4. 浏览器执行强制刷新，检查控制台无 MIME、模块加载和资源 404；再回归首页、登录、模型供应商和模型额度页面。

### C. 后端 ACR 镜像发布

1. 代码推送后等待 ACR 完成目标镜像构建，记录镜像 tag/digest；服务器不在 2GB 节点本地构建镜像。
2. 登录服务器后执行：`cd /opt/ozonslj/app/deploy`，再执行 `docker compose --env-file .env config --quiet` 和 `docker compose --env-file .env ps`。
3. 只拉取并重建变更的 API/Worker/Scheduler：`docker compose --env-file .env pull api worker scheduler`，随后 `docker compose --env-file .env up -d --no-deps api worker scheduler`。未变更的 PostgreSQL、Redis、Nginx 不重建。
4. 等待容器稳定后依次检查 `/api/health/live`、`/api/health/ready` 和 `/api/health/rag`，再查看脱敏日志：`docker compose logs --tail=100 api worker scheduler`。
5. 若健康检查失败，先保留失败日志和镜像 digest，停止继续发布；按上一版已验证镜像回滚并重新执行健康检查，不直接删除数据库或卷。

### D. 发布后验收与回滚

- 前端：入口 200、JS/CSS MIME 正确、无模块加载错误、首次进入不弹操作提示、按钮成功/失败 Toast 正常。
- 后端：live/ready 均返回 `status=ok`，API/Worker 容器为 running，数据库迁移版本与代码兼容。
- 联调：登录、配置模型、测试外部模型、刷新配置和模型额度页面至少各回归一次；真实外部凭据只在服务器安全配置中使用。
- 回滚：恢复上一版 `index.html` 与 assets，后端恢复上一版镜像 tag/digest，重新执行 C/D 两节验收；不得使用 `git reset --hard` 覆盖开发工作树。

### E. 2026-08-15 云端验收记录

- API `live` 和 `ready`：HTTPS 访问均返回 `{"status":"ok"}`；HTTP 入口 301 到 HTTPS 属于当前网关策略。
- Chroma：`/api/health/rag` 返回 `healthy`，容器健康检查通过，API 与 Chroma 位于可用的 Compose 网络。
- PostgreSQL/Redis/API/Web/Worker：容器均运行；API、PostgreSQL、Redis 健康，Worker 进程为 `python -m backend.app.worker`。
- 备份：最新备份 `ozonslj-20260811T073627Z.dump` 为 PostgreSQL CUSTOM 格式，`pg_restore --list` 成功；恢复到临时数据库成功后已删除临时数据库和临时副本。
- 前端：线上入口已切换到最新 `index-DLCnFVSL.js`，JS 返回 HTTP 200 和 `application/javascript`。
- 修复项：Compose 增加独立 `scheduler` 服务，避免只有 Worker 而没有到期任务投递进程；Scheduler 使用同一应用镜像但通过 `SERVICE_ROLE=scheduler` 启动，只挂载 PostgreSQL Secret，不读取模型或 Seller 凭据。
- Scheduler 验收：ACR 新镜像已拉取，服务端 Compose 已显式补齐 PostgreSQL、Redis 和调度参数；Scheduler 已连续运行并确认进程为 `scheduler_main`，无启动 traceback。
- 2026-08-15 闭环结果：API/Worker/Scheduler/PostgreSQL/Redis/Web/Chroma 均运行；HTTPS `live`、`ready` 返回 `status=ok`，`/api/health/rag` 返回 `healthy`。API/Worker 仍沿用既有健康容器，未因缺失的可选 RAG Secret 强行重建；不得伪造模型 Secret 或把生产环境降级为 local。
- 尚未具备的真实能力：当前云端同步处理器在 `stub` 模式；真实 Seller API 只读授权和供应商真实模型调用仍需单独授权与验收，不能标记为真实业务闭环完成。
