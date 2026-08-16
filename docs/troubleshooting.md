# Troubleshooting

## 2026-08-11：开发云服务器发布故障复盘与可复用流程

### 适用范围

本节适用于 PostgreSQL、Redis、FastAPI API、后台 Worker 和 Nginx 静态 Web 组成的开发云服务器发布。目标是在不输出凭据、不在低内存服务器本地构建、也不重建无关基础设施的前提下，完成可验证、可恢复的发布。

### 本次故障链与根因

| 现象 | 根因 | 修复与验证 |
|---|---|---|
| API/Worker 更新后登录返回 500 | 应用代码依赖新身份表，但镜像构建上下文仍打包旧迁移目录，数据库迁移账本与代码不一致 | 修正镜像迁移来源；在隔离数据库演练旧基线升级；生产执行迁移前备份，迁移后核对账本、表和字段注释 |
| 登录接口恢复后，工作区页面读取 `undefined.length` | 前端把 `/v1/store-workspaces` 数组响应误当成 `{items: [...]}` | 以前端集中 API 类型为准修正解析；类型检查、Web 构建及真实接口返回结构同时验证 |
| HTTP 页面登录时报 `crypto.randomUUID is not a function` | `randomUUID` 只在安全上下文稳定可用，开发服务器使用 HTTP | 集中实现请求 ID 生成器；优先 `randomUUID`，回退到 `getRandomValues` 生成 RFC 4122 v4，不得使用 `Math.random` |
| 刷新后再次出现登录页并显示 `Failed to fetch` | Web 包未注入云端 API 地址，回退请求浏览器本机 `127.0.0.1:8000` | HTTP(S) Web 页面默认使用同源 `/api`，Chrome 扩展环境才回退本机地址；验证 `/api/v1/auth/me` 能到达服务端 |
| 高级功能入口散落到主画布 | 大量入口是 `.app-shell` 的直接子节点，被 CSS Grid 自动放置 | 页面只保留一个侧栏导航和一个主内容画布；低频能力按业务阶段折叠分组 |
| 折叠菜单显示浏览器默认大字号和三角 | 样式写入未被入口加载的 CSS 文件 | 修改前先从 `main.tsx` 核对真实 CSS 导入链；构建后检查产物包含目标选择器 |
| 店铺选择器展开为系统蓝色菜单 | 使用原生 `select`，弹出层样式由操作系统控制 | 改为具备 `listbox`/`option` 语义的项目内选择器，保留键盘焦点、状态和选中反馈 |
| 点击选品或广告入口看似无响应 | 当前店铺为非 `active` 状态；菜单状态已切换，但所有页面共享同一个“已停用”面板 | 不绕过凭据校验；空状态标题随当前入口变化，明确说明不可用原因并提供店铺连接入口 |
| GitHub 推送连续失败 | 外部网络连接重置或不可达，不是代码错误 | 同一种推送方式最多尝试两次；记录本地提交，必要时仅临时发布静态产物，并在网络恢复后补推，避免服务器长期偏离 Git 历史 |

### 标准发布流程

#### 1. 发布前固定基线

1. 执行 `git status --short`，记录并保留用户已有改动。
2. 记录待发布提交、远端分支和预期镜像标签；不得用可变标签替代提交证据。
3. 立即检查服务器 API、Worker、PostgreSQL、Redis、Web 状态和 API 健康端点。
4. 如果 API/Worker 异常，先恢复交接记录中的旧健康镜像，再调查新镜像；不要让故障版本持续占用服务窗口。
5. 发布前创建 PostgreSQL 逻辑备份并记录恢复位置；不得通过重建 PostgreSQL 容器代替迁移。

#### 2. 核对镜像构建证据

- 核对 ACR 实际构建分支、提交、Dockerfile 和构建上下文。
- 从镜像内部或构建产物确认目标提交对应的修复文件真实存在，不能只依据镜像标签或流水线“成功”状态。
- API 和 Worker 必须使用同一应用镜像摘要，避免代码与任务处理逻辑版本漂移。
- 2GB 开发服务器只拉取镜像和运行容器，不执行 Python/Node 依赖安装或本地镜像构建。

#### 3. 数据库迁移闸门

1. 在隔离数据库从服务器旧基线演练到当前版本。
2. 检查迁移编号、名称和 SHA-256；历史迁移不可被静默改写。
3. 正式迁移前备份，迁移过程使用咨询锁，失败时 API 不得进入就绪状态。
4. 迁移后核对：迁移账本版本、关键表、约束、索引、表中文注释和字段中文注释。
5. 数据库结构只由权威 schema 与版本化迁移维护，禁止为解除 500 临时手工建表。

#### 4. 前端构建与契约检查

在仓库根目录执行类型检查，在 `extension` 目录执行 Vite；不要混用工作目录：

```powershell
.\extension\node_modules\.bin\tsc.CMD -b extension\tsconfig.json --pretty false

Set-Location .\extension
.\node_modules\.bin\vite.CMD build `
    --mode web `
    --configLoader runner `
    --outDir ..\deploy\web
```

构建后至少检查：

- `index.html` 引用的新 JS/CSS 文件真实存在。
- Web 包在 HTTP(S) 页面使用同源 `/api`，不能意外固定为 `127.0.0.1`。
- 登录、会话恢复、工作区列表的前端类型与后端 JSON 顶层结构一致。
- HTTP 开发站点所需能力有兼容路径，例如请求 ID 不只依赖 `crypto.randomUUID`。
- 从 `main.tsx` 核对实际 CSS 导入链，避免把修复写进未加载文件。

#### 5. 最小化部署

- API/Worker 只有在新镜像内容、摘要和迁移兼容性都确认后才重建。
- PostgreSQL、Redis、Nginx 未发生配置或镜像变更时不得重建。
- Web 使用只读绑定静态目录时，只更新已构建产物即可；更新后核对首页引用的新哈希资源。
- 直接上传静态文件只能作为 GitHub 暂时不可用时的应急措施。必须保留本地提交，并在网络恢复后补推和让服务器 Git 工作树重新对齐。

#### 6. 发布后验证

按由内到外的顺序验证，避免只看容器为 `Up`：

1. 容器：API `healthy`，Worker、Web、PostgreSQL、Redis 运行中。
2. 服务内：健康端点成功；未携带会话访问 `/api/v1/auth/me` 返回 401 而不是网络错误或 500。
3. 公网：首页、新哈希 JS/CSS 均返回 200。
4. 业务：错误凭据返回 401；有效会话刷新后能够恢复；工作区接口返回契约规定的顶层结构。
5. 数据库：迁移账本为目标版本，关键表存在，中文注释无缺失。
6. 浏览器：强制刷新后检查登录、店铺切换、导航反馈、空状态和窄屏布局。

### 回滚原则

- 回滚前先区分镜像故障、数据库迁移故障和静态资源故障，选择最小回滚面。
- API/Worker 可回到已记录的旧健康镜像摘要；不要凭标签猜测旧版本。
- 向前不兼容的数据库变更必须在迁移设计阶段提供分阶段方案；不要在故障现场直接删字段或还原整个数据库。
- 静态资源回滚应恢复匹配的 `index.html` 与其哈希资源组合，不能只替换其中一个文件。
- 回滚后重复完整的内外健康检查，并记录实际运行的提交、镜像摘要和迁移版本。

### 可复制的发布检查单

- [ ] 工作树和用户改动已确认。
- [ ] 待发布提交、分支、镜像摘要和构建上下文一致。
- [ ] 旧健康镜像摘要可用，恢复命令已知。
- [ ] PostgreSQL 已备份，迁移已在隔离环境演练。
- [ ] API/Worker 新镜像包含目标修复，且使用同一摘要。
- [ ] TypeScript、Vite Web 构建和 `git diff --check` 通过。
- [ ] Web API 地址、响应顶层结构和 HTTP 浏览器兼容性已检查。
- [ ] 仅重建必要服务；未重建 PostgreSQL、Redis、Nginx。
- [ ] API 健康、Worker 运行、公网首页和哈希资源均可访问。
- [ ] 登录、会话恢复、工作区、导航不可用反馈已人工验证。
- [ ] 数据库迁移账本、关键结构和中文注释已核对。
- [ ] 提交已推送；若临时直传静态文件，已登记补推和 Git 对齐事项。

## 2026-08-11：发布后登录返回 HTTP 500

### 现象

API、Worker、PostgreSQL 和 Redis 均健康，但登录接口返回 500；API 日志显示
`relation "users" does not exist`。

### 原因判断

应用镜像已包含当前身份代码，却仍只打包早期 `database/postgres/migrations`。服务器迁移账本
停留在 `0001 initial`、`0002 identity_sessions`，API 启动也没有执行权威迁移，因此代码和
数据库结构不一致。

### 恢复办法与预防措施

- 镜像只打包 `database/postgresql_schema.sql` 与 `database/migrations/`。
- PostgreSQL 连接池开放前执行带咨询锁的版本化迁移；失败时不允许服务进入就绪状态。
- 旧云端账本仅在名称和 SHA-256 精确匹配时走受控兼容路径，禁止手工建表、修改历史校验和或
  直接把当前 `0002` 覆盖到已占用版本。
- 发布前使用隔离数据库演练旧基线升级，并确认运营人员、工作区授权和会话表映射完成。

本文件记录可复现或高成本的开发环境故障。每条记录包含现象、原因判断、恢复办法和预防措施。

## 2026-07-31：前端验证异常等待约 47 分钟

### 现象

在 Windows Codex 工作区内验证扩展前端时，一次组合命令长时间没有返回。工具记录该执行单元耗时 `2803.5` 秒（约 46 分 43 秒），但随后读取结果时显示命令本身只用了约 `2.5` 秒并正常退出。同期还出现：

- `pnpm typecheck` / `pnpm build` 因无交互终端触发 `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`。
- 从仓库根目录直接调用 Vite 时找不到 `sidepanel.html`。
- Vite 清空 `extension/dist/assets` 时因 Windows 文件占用或权限限制报 `EPERM`。
- Playwright 通过 npx 启动时，npm 缓存目录创建临时文件报 `EPERM`。

### 原因判断

主要耗时不是 TypeScript 编译或文件清理，而是 Codex 工具执行单元、子进程状态或结果回传出现异常等待。依据是工具显示约 47 分钟墙钟时间，而同一执行单元最终报告的实际命令时间只有约 2.5 秒。

放大因素包括：

1. 把类型检查、构建和清理组合在同一命令中，无法快速判断具体卡点。
2. pnpm 检测到现有 `node_modules` 与当前运行环境不一致，尝试进行需要交互确认的目录处理。
3. Vite 命令工作目录错误，入口文件相对于错误目录解析。
4. `extension/dist` 或 npm 缓存被其他进程占用，触发 Windows `EPERM`。
5. 对失败命令进行多轮串行重试，累计增加等待时间。

### 解决办法

将验证步骤拆开，并给每一步设置独立、较短的超时时间：

```powershell
# 在仓库根目录执行类型检查
.\extension\node_modules\.bin\tsc.CMD -b extension\tsconfig.json --pretty false

# 在 extension 目录执行 Vite
Set-Location .\extension
.\node_modules\.bin\vite.CMD build `
    --configLoader runner `
    --outDir ..\verify-dist `
    --emptyOutDir false
```

构建成功后，只清理经过绝对路径校验的临时目录：

```powershell
$verifyPath = (Resolve-Path -LiteralPath '..\verify-dist').Path
if ($verifyPath -eq 'D:\learn\gpt\ozonslj\verify-dist') {
    Remove-Item -LiteralPath $verifyPath -Recurse -Force
}
```

如果必须使用 pnpm，在无交互环境中先设置：

```powershell
$env:CI = 'true'
pnpm typecheck
pnpm build
```

## 2026-08-14：浏览器拒绝执行前端模块脚本

### 现象

浏览器控制台提示 `Failed to load module script`，并显示服务器返回 `text/html`，页面为空白。

### 原因与修复

Web 发布目录中的 `index.html` 引用了不存在的哈希 JS/CSS 文件。Nginx 的 `try_files` 将缺失的
静态资源回退到 `/index.html`，导致模块请求收到 HTML，触发浏览器的严格 MIME 检查。
构建 Web 版本时必须使用 `vite build --mode web`，并将生成的 `index.html` 与整个 `assets/`
目录成套同步到 `deploy/web`；不能只替换 HTML 或只上传单个资源。发布后逐一检查首页、哈希
JS/CSS 均返回 200，且 JS 的 `Content-Type` 为 JavaScript 类型。

如果 npm 或 Playwright 缓存仍报 `EPERM`，先确认没有遗留的 Node、Vite 或浏览器自动化进程，再使用已批准的非沙箱执行权限；不要循环重试同一个失败命令。

### 预防措施

- 不把类型检查、生产构建、截图和临时目录清理放进同一个长命令。
- 首次无输出超过合理时间时终止并分步诊断，不等待几十分钟。
- Vite 始终从 `extension` 目录运行，或显式提供正确的 root/入口。
- 被占用的 `dist` 不作为验证输出目录；使用工作区内独立的 `verify-dist`。
- Playwright 在一个浏览器会话内完成导航与多张截图，减少重复 npx 和浏览器启动。
- 记录每条验证命令的退出码；超时或被终止的命令不得计为通过。
## 2026-08-14：API 重建后登录返回 HTTP 502

### 现象

API 容器显示 `healthy`，但登录、`/api/v1/auth/*` 或健康检查经过 Nginx 返回 502。

### 原因判断

Compose 重建 API 后，API 容器的网络 IP 发生变化；Nginx 已启动进程仍缓存旧 upstream IP，因此连接被拒绝。该问题不是 API 代码或数据库故障。

### 恢复办法与预防措施

```bash
docker compose --env-file .env restart web
docker compose --env-file .env ps
curl -fsS http://127.0.0.1/api/health/live
curl -fsS http://127.0.0.1/api/health/ready
```

以后每次执行 `up -d --no-deps api worker` 后，必须同步重启 `web` 并验证登录/关键 API；发布脚本不得只更新 API/Worker 而跳过 Web upstream 刷新。若仍为 502，检查 `docker logs ozonslj-web-1` 中的 `connect() failed` 和 upstream 地址，再确认 API 容器监听 `8000` 且状态为 healthy。

## 2026-08-14：SiliconFlow BAAI/bge-m3 返回 HTTP 400 参数无效

### 根因

OpenAI 兼容协议不代表所有供应商支持完全相同的可选字段。SiliconFlow 的 `BAAI/bge-m3` 请求必须使用 `/v1/embeddings`，不发送 `dimensions`；为避免网关对单条输入数组形态的差异，单条文本使用字符串，批量文本才使用字符串数组。供应商名称不能作为能力判断依据，必须结合实际请求域名。

### 可复用规则

- Embedding 请求默认只发送 `model` 和 `input`，供应商特有参数通过能力开关显式加入。
- `api.siliconflow.cn` 下的 `BAAI/bge-m3` 禁止发送 `dimensions`。
- 单条请求优先发送字符串；只有批量请求发送数组。
- 仅在明确的供应商兼容模式下，对 HTTP 400 做一次相反输入形态重试；禁止无界重试或把所有 400 自动重试。
- 上游错误只提取 `message`、`error_msg`、`detail`、`code` 等短摘要，不返回请求体、响应全文或 Authorization。
- 真实外部验证必须使用临时内存凭据；凭据不得写入文件、数据库、日志、测试夹具或 Git。凭据一旦在聊天、截图或日志中暴露，应立即轮换。

### 验证基线

```json
{
  "model": "BAAI/bge-m3",
  "input": "连接测试"
}
```

目标地址为 `https://api.siliconflow.cn/v1/embeddings`，应以真实 HTTP 200 和合法向量响应作为连通性成功条件，不能只依据本地参数校验成功。

## 2026-08-15：真实 Embedding 维度校验误用测试维度

生产主备 Embedding 与同一 Chroma 索引必须统一使用 1024 维。运行时路由器不得从
测试用 `DeterministicEmbedding` 继承 32 维作为真实供应商的期望维度；必须读取
`RAG_EMBEDDING_DIMENSION`（默认 1024）进行响应校验。若模型或维度变更，必须新建
索引版本并完整重建，禁止在同一 collection 混写不同维度向量。

## 2026-08-16：本地测试缺少数据库配置或旧依赖入口

认证单元测试不得读取开发数据库和 Redis；通过依赖覆盖固定测试组织、限流器和 Cookie 策略。Seller 账户历史测试通过兼容依赖适配到当前 `store_workspaces` 聚合，生产代码仍只使用统一 PostgreSQL 网关。迁移计划测试必须引用仓库当前最新 `source_version`，不能继续写死旧版本号。若完整测试失败，先区分测试基线断言/依赖收集错误与真实业务失败，再决定是否需要云端只读验收。
- **严重发布事故：ACR 仍为旧镜像或误推分支**：先停止重建和验收，核对 `git branch --show-current`、远端 source commit、ACR 构建规则、镜像 digest、创建时间和 `OZONSLJ_RELEASE_REVISION`。本项目固定使用 `codex/deployment-base-images`；禁止把开发分支直接推到 `main`，禁止在 2GB 服务器本地构建。若发生误推，使用已知远端旧提交和 `--force-with-lease` 恢复，并记录事故后再继续。
- **Worker 因迁移账本冲突重启**：先查看 `PostgresMigrationError`，核对 `database/migrations` 是否存在重复四位版本号。不得修改数据库 `schema_migrations` 或跳过校验；新增迁移必须使用下一个未占用的源版本，并同步更新旧基线映射测试后重新构建。
- **模型额度保存返回 500 且日志为 `Decimal` 与 `float` 运算错误**：PostgreSQL 的 `NUMERIC` 字段会由驱动返回 `Decimal`，策略金额和用量金额必须在 `PostgresModelBudgetGateway` 读取边界显式转换为 `float`；不得在领域预算计算中混用 `Decimal` 与 `float`。验证保存接口及 Decimal 回归测试后再重新构建镜像。
- **新增前端页面线上不可见**：Web 容器挂载的是服务器 `deploy/web` 静态目录，不会读取 `ozonslj-api-dev` 镜像内的前端源码。必须执行 `vite build --mode web`，完整同步 `index.html` 和 `assets/`，再重建 Web 容器并用 `curl` 校验首页引用的哈希资源为 200；浏览器仍缓存旧入口时使用 `Ctrl+F5`。
- **Web 重建后 Nginx 找不到 TLS 证书并反复重启**：若日志出现 `cannot load certificate /etc/nginx/tls/server.crt`，说明 Compose 漏挂服务器 `deploy/secrets/tls`。证书只能从服务器密钥目录只读挂载到 `/etc/nginx/tls`，禁止提交、输出或重新生成临时证书；补齐挂载后再执行 Web 重建并验证 HTTPS。
