# 本地开发与调试说明

> 本文只描述开发与测试环境，文档职责见 [项目文档索引](./README.md)。本地、测试、集成和云端均只使用 PostgreSQL；Redis 只承担可恢复协调状态。真实 Ozon 数据处理器和云端进程仍须单独验收。

## 1. 所需软件

- Python 3.12+
- Node.js LTS
- pnpm
- Chrome
- PostgreSQL 16
- Redis 7.4
- Chroma 0.5.23（知识 RAG 本地/集成模式必需；通过独立容器运行）
- 推荐使用 VS Code

开发者必须提供隔离的 PostgreSQL/Redis，可使用仓库后续提供的 Compose 开发栈或明确配置的独立实例。仓库尚未提供完整 Compose 开发栈和 PostgreSQL 适配器前，本地数据库闭环处于未完成状态，不得增加替代数据库规避该缺口。

## 2. 首次安装

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e . pytest pytest-asyncio ruff mypy
pnpm install
```

复制 `.env.example` 为 `.env`，为本地环境填写隔离 PostgreSQL 和 Redis 连接；使用 Ozon Stub 时无需真实 Ozon 凭据。`.env.example` 中的地址和密码仅是占位示例，不得直接用于共享或生产环境。

## 3. 启动后端

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-backend.ps1
```

验证：

- 接口文档：`http://127.0.0.1:8000/docs`
- 存活检查：`http://127.0.0.1:8000/health/live`
- 就绪检查：`http://127.0.0.1:8000/health/ready`

### 3.1 启动同步进程

同步任务以 PostgreSQL 为事实源、Redis Stream 为可重建队列。启动前必须配置
`DATABASE_URL` 和 `REDIS_URL`。本地 `OZON_MODE=stub` 时分别运行：

```powershell
.\.venv\Scripts\ozonslj-sync-scheduler.exe
.\.venv\Scripts\ozonslj-sync-worker.exe
```

Scheduler 默认每 5 秒扫描一次到期任务；Worker 默认单并发执行。`OZON_MODE=live`
但真实 Ozon 处理器尚未配置时，Worker 会拒绝启动，避免把 Stub 结果误记为真实同步成功。

## 4. 启动扩展

扩展通过 Vite 的 `VITE_API_BASE_URL` 连接后端：本地留空时默认访问
`http://127.0.0.1:8000`；云端构建必须注入实际 HTTPS API 地址。该变量只包含地址，
不得包含 Client ID、Api-Key、会话令牌或其他凭据。

登录会话使用 HttpOnly Cookie；本地开发允许指定的本地前端源携带凭据，生产环境应由
反向代理提供同源 HTTPS 访问。扩展前端不会把 Ozon 凭据写入浏览器存储。

```powershell
pnpm dev
```

然后：

1. 等待生成 `extension/dist/manifest.json`。
2. 打开 `chrome://extensions`。
3. 开启“开发者模式”。
4. 点击“加载已解压的扩展程序”。
5. 选择项目中的 `extension/dist`。
6. 构建更新后，在扩展管理页点击重新加载。
7. 打开扩展侧边栏。

## 5. 本地模式

| 模式 | 后端 | 数据库 | Ozon |
|---|---|---|---|
| `local-stub` | 本地 FastAPI | 隔离 PostgreSQL | 确定性模拟数据 |
| `local-live` | 本地 FastAPI | 隔离 PostgreSQL | 真实 Seller API |
| `test` | pytest 进程 | 每次测试隔离的 PostgreSQL schema/database | Mock/契约夹具 |
| `integration` | 本地或容器 FastAPI/Worker | 隔离 PostgreSQL + Redis | Stub/Mock；禁止真实账号 |
| `production` | 云端 Compose | PostgreSQL + Redis | 按已授权账户访问真实服务 |

默认使用 `local-stub`。`local-live` 必须显式配置，自动化测试禁止使用真实账户。PostgreSQL 业务适配器、Redis 队列和同步进程入口已经具备；真实 Seller 数据处理器及云端进程运行验证尚未完成。

## 6. 配置项

```dotenv
APP_ENV=local
APP_HOST=127.0.0.1
APP_PORT=8000
DATABASE_URL=postgresql://ozonslj:replace-me@postgres:5432/ozonslj
REDIS_URL=redis://redis:6379/0
# APP_ENV=production 时必填；local/test 可省略
CHROMA_URL=http://chroma:8000
OZON_MODE=stub
OZON_BASE_URL=https://api-seller.ozon.ru
LOG_LEVEL=DEBUG
```

真实凭据只能通过账户连接用例提交到后端，经凭据保护端口执行应用级信封加密后写入 PostgreSQL。加密主密钥通过本地 Secret 文件或 Compose Secret 注入，不得把真实凭据放入 `.env`、扩展环境文件、命令行、日志或测试夹具。机器绑定的历史密文不能直接迁移，用户需要在新运行时重新授权或替换凭据。

### 创建首个组织所有者

系统不提供公网注册入口。首次引导必须使用独立的 `BOOTSTRAP_DATABASE_URL`，其数据库角色需要 `BYPASSRLS` 或超级用户能力；普通 API `DATABASE_URL` 会被工具拒绝。密码通过隐藏交互输入，不得放入参数或环境变量：

```powershell
$env:BOOTSTRAP_DATABASE_URL = "<仅在当前受控终端注入，不写入仓库>"
python -m scripts.create_organization_owner `
  --organization-id org-initial `
  --organization-name "初始组织" `
  --email owner@example.com `
  --display-name "组织所有者"
```

工具只用于离线引导或受控重置：它原子写入组织、用户和 owner 成员关系，并撤销该用户旧会话。执行后立即清除当前终端中的 `BOOTSTRAP_DATABASE_URL`；API、Worker 和浏览器均不得持有该连接。

## 7. 调试

- 后端：使用 `.vscode/launch.json` 中的 `Backend: FastAPI`。
- 侧边栏：从 `chrome://extensions` 打开侧边栏检查器。
- Service Worker：点击扩展的 Service Worker 检查入口。
- 网络：通过请求编号关联扩展请求和后端日志。
- PostgreSQL/RLS：必须在隔离集成环境验证，查询前确认事务已设置组织与用户上下文。
- Redis：只检查队列、锁和短期状态；不得人工写入或依赖其恢复业务事实。
- Ozon 错误：优先使用 Stub 场景复现，再考虑真实凭据。

## 8. 完整检查

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

检查包括 pytest、Ruff、mypy、TypeScript 类型检查和 Vite 生产构建。
