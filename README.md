# ozonslj

面向 Ozon 跨境卖家的 Chrome/Web 运营系统。项目由 React/TypeScript 扩展、Python FastAPI 后端、PostgreSQL 与 Redis 组成，并支持 Linux Docker Compose 节点。

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
- [架构设计 V4（待架构评审）](./docs/ARCHITECTURE_V4.md)
- [项目需求](./docs/REQUIREMENTS.md)
- [项目需求 V3（待确认）](./docs/REQUIREMENTS_V3.md)
- [项目需求 V4（已确认）](./docs/REQUIREMENTS_V4.md)
- [数据库设计](./docs/DATABASE.md)
- [接口文档](./docs/API.md)
- [前后端开发规范](./docs/DEVELOPMENT_STANDARDS.md)
- [本地开发与调试](./docs/LOCAL_DEVELOPMENT.md)
- [开发计划](./docs/PROJECT_PLAN.md)
- [Linux 部署](./docs/DEPLOYMENT.md)

## 完整检查

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```
