# ACR 稳定构建与发布流程

本文是 `ozonslj` 的唯一可复用构建流程。目标是确保：一次代码发布只构建需要的应用镜像，构建源明确，镜像内容与目标提交一致，云端只在全部证据通过后重建服务。

## 一、构建对象先分层

| 对象 | 镜像/规则 | 触发方式 | 代码提交是否应自动触发 |
|---|---|---|---|
| 应用后端 | `ozonslj-api-dev`，仓库根目录 `/Dockerfile` | `codex/deployment-base-images` 分支的应用构建规则 | 是 |
| PostgreSQL 基础镜像 | `postgres-16-alpine` | 基础镜像专用 Tag/分支或手动构建 | 否 |
| Redis 基础镜像 | `redis-7.4-alpine` | 基础镜像专用 Tag/分支或手动构建 | 否 |
| Nginx、Python、Node、Chroma 基础镜像 | 对应 `deploy/base-images/*/Dockerfile` | 基础镜像专用 Tag/分支或手动构建 | 否 |

截图中多个基础镜像规则都绑定开发分支，导致一次应用提交触发整组构建。这会制造排队和误判，后续必须将基础镜像规则改为手动或独立引用；在规则未调整前，不要点击“立即构建”整页规则，只构建应用规则。

2026-08-16 已在 GitHub 创建并推送以下基础镜像专用 Tag，均指向提交 `afd375a`：

```text
base-postgres-v1
base-redis-v1
base-nginx-v1
base-python-v1
base-node-v1
base-chroma-v1
```

ACR 页面中分别填写为 `tags:base-postgres-v1`、`tags:base-redis-v1`、`tags:base-nginx-v1`、`tags:base-python-v1`、`tags:base-node-v1`、`tags:base-chroma-v1`。Tag 是基础镜像构建基线，不随应用分支后续提交变化。

## 二、发布前固定门禁

在本地项目目录执行：

```powershell
git branch --show-current
git status --short
git rev-parse HEAD
git log -1 --oneline
git diff --check
```

必须同时满足：

1. 当前分支是 `codex/deployment-base-images`。
2. 目标提交已经推送到 `origin/codex/deployment-base-images`。
3. 工作树没有未提交的受控代码/文档改动；未跟踪的诊断和构建目录不得清理、不得加入提交。
4. 前端有改动时，已在 `extension` 单独执行 `vite build --mode web`，并确认完整 `index.html + assets/` 产物。
5. 后端有改动时，已完成对应 pytest、TypeScript 检查和必要的 Vite 构建。

## 三、ACR 构建规则核对

在 ACR 控制台选择应用规则时，必须逐项核对：

| 项目 | 应为 |
|---|---|
| Git 仓库 | `https://github.com/pengxdCSDN/ozonslj` |
| Source branch/tag | `codex/deployment-base-images` |
| 构建上下文 | `/` |
| Dockerfile | `Dockerfile` |
| 目标镜像 | `ozonslj-api-dev` |
| 构建参数 | 应传入目标提交作为 `RELEASE_REVISION`；若控制台不支持，必须以构建记录 source commit 作为同等证据 |

不要以服务器工作树作为 ACR 构建源。服务器只负责拉取和运行，服务器上的 `git checkout` 不能证明 ACR 使用了相同提交。

## 四、等待与验收 ACR 构建

构建记录必须保存四项信息：`build_id`、`source_commit`、`image_digest`、`created_at`。只有构建状态成功还不够，必须通过以下门禁：

1. `source_commit` 等于本地已推送目标提交。
2. 新 digest 与云端当前运行 digest 不同。
3. 镜像创建时间晚于目标提交推送/构建开始时间。
4. 镜像内 `OZONSLJ_RELEASE_REVISION` 等于目标提交；若仍是 `development`，必须额外用镜像内关键文件和 ACR source commit 双重核对，不能直接验收。
5. 镜像内存在本次变更的关键文件，并能成功导入或执行最小检查。例如：

```bash
docker run --rm --entrypoint sh "$APP_IMAGE" -lc \
  'test -f /app/backend/app/domain/<本次关键文件>.py && echo release-files=ok'
docker run --rm --entrypoint python "$APP_IMAGE" -c \
  'from backend.app.main import app; print("app-import=ok")'
```

如果出现“digest 变化但关键文件不存在”“source commit 不一致”或“revision 仍是旧值”，状态必须是“构建源错误/未验收”。不得重启服务、不得报告发布完成；重新触发正确规则后重新核对全部证据。

## 五、云服务器发布顺序

服务器执行前先做只读检查：

```bash
cd /opt/ozonslj/app
git fetch origin codex/deployment-base-images
git show -s --format='server-source=%H' origin/codex/deployment-base-images
cd deploy
docker compose --env-file .env config --quiet
docker compose --env-file .env ps
```

确认 ACR 证据通过后，只拉取和重建变更服务：

```bash
docker compose --env-file .env pull api worker scheduler
docker compose --env-file .env up -d --no-deps api worker scheduler
docker compose --env-file .env restart web
```

基础服务 PostgreSQL、Redis、Chroma、Nginx 不因普通后端代码提交重建。应用镜像摘要必须满足：

```bash
docker inspect --format='{{.Image}}' \
  ozonslj-api-1 ozonslj-worker-1 ozonslj-scheduler-1
```

三者完全一致后，再检查：

```bash
curl -fsS http://127.0.0.1/api/health/live
curl -fsS http://127.0.0.1/api/health/ready
docker compose --env-file .env logs --tail=100 api worker scheduler
```

Web 是独立发布对象。前端改动必须完整同步 `deploy/web`，检查首页引用的所有 JS/CSS 均为 `200`，且 JS/CSS 不能返回 `text/html`。API 健康不能代替 Web 验收。

## 六、失败处理与回滚

| 现象 | 处理 |
|---|---|
| ACR 多个基础镜像排队 | 不等待整组；取消无关基础镜像任务，保留应用构建；后续修改规则触发方式 |
| 构建成功但 source commit 不对 | 标记构建源错误，不拉取、不重启，重新触发应用规则 |
| digest 未变化 | 不重启、不验收，继续等待或检查构建规则 |
| API/Worker/Scheduler 摘要不一致 | 停止验收，重新拉取同一 digest 后再重建 |
| API ready 通过但 Web 资源 404/返回 HTML | 回滚 Web 静态目录，完整同步上一版 `index.html + assets/` 后原子切换 |
| 新容器启动失败 | 保留旧镜像摘要，查看日志，使用上一版摘要重建变更服务；不得在 2GB 服务器本地构建替代 |

## 七、发布记录模板

每次发布至少记录：

```text
发布分支:
目标提交:
ACR 构建规则:
ACR build_id:
ACR source_commit:
镜像 digest:
镜像 created_at:
镜像内 release revision:
API/Worker/Scheduler 摘要:
API live/ready:
Web 入口 JS/CSS:
迁移最高版本:
回滚摘要:
结论: 已发布 / 未验收 / 构建源错误 / 已回滚
```

禁止记录凭据、Token、私钥、`.env` 内容或密钥文件内容。

## 八、GitHub Actions 长期自动发布

为避免依赖阿里云控制台登录态，仓库新增 `.github/workflows/deploy.yml`。它只监听
`codex/deployment-base-images`，在 GitHub Runner 完成后端回归、前端类型检查和 Web 构建，
再使用 ACR Docker 凭据推送 `ozonslj-api-dev`，最后通过 SSH 只更新 API、Worker、Scheduler
和 Web 静态目录。

仓库 Settings → Secrets and variables → Actions → Repository secrets 必须配置：

| Secret | 用途 | 注意 |
|---|---|---|
| `ACR_USERNAME` | ACR Docker 用户名 | 使用 ACR 页面显示的阿里云账户全名，不是控制台密码 |
| `ACR_PASSWORD` | ACR 固定密码 | 使用 ACR“设置固定密码”设置的密码，不是阿里云登录密码 |
| `DEPLOY_SSH_KEY` | 云服务器 SSH 私钥 | 粘贴完整 OpenSSH 私钥，不得提交到仓库或发送到聊天 |

工作流同时推送 commit SHA 镜像标签，并将 `RELEASE_REVISION` 写入镜像环境变量；服务器部署前
拉取可变 `ozonslj-api-dev` 标签，但会检查服务容器使用同一镜像摘要。Web 先上传到
`web.next-<commit>` 临时目录，再原子切换并保留 `web.rollback-<commit>`，健康检查失败时不得
删除回滚目录。

这套流程不需要每次登录阿里云控制台。若 ACR 固定密码或服务器 SSH 密钥轮换，只需在 GitHub
Secrets 中更新对应值，不修改工作流和仓库代码。

## 九、本机 Git 推送与 GitHub Actions 构建发布标准路径

### 9.1 传输方式边界

本项目当前 GitHub 远端保持 HTTPS：

```text
origin = https://github.com/pengxdCSDN/ozonslj.git
```

本机 `git-remote-https.exe` 曾因 Windows Schannel 后端崩溃，导致推送失败。稳定处理是将
Git 的 HTTPS SSL 后端固定为 OpenSSL；这不会改变远端地址，也不会把凭据写入仓库：

```powershell
git config --global http.sslBackend openssl
git config --global --get http.sslBackend
```

第二条命令必须输出 `openssl`。推送前固定执行：

```powershell
git branch --show-current
git status --short
git rev-parse HEAD
git ls-remote --heads origin codex/deployment-base-images
git push origin codex/deployment-base-images
```

如果 Git 仍然出现 `git-remote-https.exe` 崩溃，先验证 OpenSSL 后端是否生效；不得反复重试
同一命令。必要时使用一次性诊断命令确认网络和 TLS 后端：

```powershell
git -c http.sslBackend=openssl ls-remote origin HEAD
```

若该命令成功，说明代码和远端没有问题，应保留全局 OpenSSL 配置并升级/重装 Git for Windows，
而不是改分支、改服务器源码或误判为 ACR 构建故障。

### 9.2 从推送到发布的唯一顺序

```text
本机 OpenSSL HTTPS 推送 → GitHub Actions 检查/构建 → ACR 推送镜像
→ Actions 通过 SSH 部署云服务器 → 摘要、健康检查和 Web 资源验收
```

本机不执行 ACR 登录、不在服务器本地构建镜像、不使用服务器工作树作为构建源。SSH 只存在于
GitHub Actions 到云服务器的部署阶段；它不是本机 GitHub 推送的替代方式。

### 9.3 每次发布操作清单

1. 确认当前分支为 `codex/deployment-base-images`，检查受控改动和 `git diff --check`。
2. 确认 `http.sslBackend` 为 `openssl`，推送该分支；不推送 `main`。
3. 在 GitHub Actions 查看同一 commit 的工作流结果；失败时先看失败步骤，不在 ACR 控制台重复点击构建。
4. 核对 ACR 镜像的 commit SHA 标签、digest 和 `RELEASE_REVISION`。
5. 由 Actions 通过 SSH 执行云端部署；服务器只拉取镜像，不执行 `docker build`。
6. 验证 API、Worker、Scheduler 使用同一 digest；前端变更另外核对 `index.html` 引用的 JS/CSS 均为 200。
7. 验收通过后保留构建记录、digest、服务状态和回滚目录；失败则保留现场并按第六节回滚。

### 9.4 不要再采用的方式

- 不要把 Git 远端改成 SSH 来绕过一次 HTTPS 崩溃；这会引入另一套密钥和端口问题，不能修复本机 Git 二进制。
- 不要在 `git-remote-https.exe` 崩溃时重复盲推；先检查 OpenSSL 后端。
- 不要为同一 commit 同时点击 ACR 自动构建和 GitHub Actions 构建，避免多个任务排队和来源混淆。
- 不要把 ACR 用户名/密码、SSH 私钥或 `.env` 内容写入日志、文档或聊天。
