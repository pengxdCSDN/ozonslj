# ozonslj

面向 Ozon 跨境卖家的 Chrome 运营插件。项目由 React/TypeScript 扩展、Python FastAPI 后端、PostgreSQL 业务数据库和 Redis 缓存/任务基础设施组成。

当前已支持多个卖家工作区、Fernet + Secret 版本化凭据加密、独立凭据验证、
工作区切换与商品缓存隔离。浏览器仅保存当前工作区 ID，不保存 Ozon 凭据。

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e . pytest pytest-asyncio ruff mypy
pnpm install
powershell -ExecutionPolicy Bypass -File .\scripts\dev-backend.ps1
```

另开终端执行：

```powershell
pnpm dev
```

然后在 `chrome://extensions` 中加载 `extension/dist`。

## 项目文档

- [统一领域语言](./CONTEXT.md)
- [架构设计](./docs/ARCHITECTURE.md)
- [项目需求](./docs/REQUIREMENTS.md)
- [数据库设计](./docs/DATABASE.md)
- [接口文档](./docs/API.md)
- [前后端开发规范](./docs/DEVELOPMENT_STANDARDS.md)
- [本地开发与调试](./docs/LOCAL_DEVELOPMENT.md)
- [开发计划](./docs/PROJECT_PLAN.md)

## 完整检查

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```
