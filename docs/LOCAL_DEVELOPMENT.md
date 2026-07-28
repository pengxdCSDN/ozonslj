# 本地开发与调试说明

## 1. 所需软件

- Python 3.12+
- Node.js LTS
- pnpm
- Chrome
- 推荐使用 VS Code

项目不需要 Docker 或独立数据库服务。

## 2. 首次安装

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e . pytest pytest-asyncio ruff mypy
pnpm install
```

复制 `.env.example` 为 `.env`。默认配置使用 Stub 模式和 `data/ozonslj.db`，无需填写真实 Ozon 凭据。

## 3. 启动后端

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-backend.ps1
```

验证：

- 接口文档：`http://127.0.0.1:8000/docs`
- 存活检查：`http://127.0.0.1:8000/health/live`
- 就绪检查：`http://127.0.0.1:8000/health/ready`

## 4. 启动扩展

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
| `local-stub` | 本地 FastAPI | `data/ozonslj.db` | 确定性模拟数据 |
| `local-live` | 本地 FastAPI | `data/ozonslj.db` | 真实 Seller API |
| `test` | pytest 进程 | 临时 SQLite 文件 | Mock/契约夹具 |

默认使用 `local-stub`。`local-live` 必须显式配置，自动化测试禁止使用真实账户。

## 6. 配置项

```dotenv
APP_ENV=local
APP_HOST=127.0.0.1
APP_PORT=8000
DATABASE_PATH=data/ozonslj.db
OZON_MODE=stub
OZON_BASE_URL=https://api-seller.ozon.ru
OZON_CLIENT_ID=
OZON_API_KEY=
LOG_LEVEL=DEBUG
```

真实凭据只能放在未提交的 `.env` 中，不得放入扩展环境文件。

## 7. 调试

- 后端：使用 `.vscode/launch.json` 中的 `Backend: FastAPI`。
- 侧边栏：从 `chrome://extensions` 打开侧边栏检查器。
- Service Worker：点击扩展的 Service Worker 检查入口。
- 网络：通过请求编号关联扩展请求和后端日志。
- SQLite：使用任意 SQLite 客户端查看 `data/ozonslj.db`。
- Ozon 错误：优先使用 Stub 场景复现，再考虑真实凭据。

## 8. 完整检查

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

检查包括 pytest、Ruff、mypy、TypeScript 类型检查和 Vite 生产构建。
