# ozonslj

面向 Ozon 跨境卖家的 Chrome 运营插件。项目由 React/TypeScript 扩展、Python FastAPI 后端、PostgreSQL 业务数据库和 Redis 缓存/任务基础设施组成。

当前已支持多个卖家工作区、Fernet + Secret 版本化凭据加密、独立凭据验证、
工作区切换与商品缓存隔离。浏览器仅保存当前工作区 ID，不保存 Ozon 凭据。

模型供应商页面支持按用途维护 Embedding 与文本模型池、优先级和自动降级链。编辑
已有供应商时 API Key 不会回显，留空表示复用服务器凭据；“测试连接”会实际调用
外部模型接口，并显示请求是否发出、目标主机、HTTP 状态和模型响应结果。占位 Key、
示例地址和不符合供应商域名约束的地址会在本地校验阶段拒绝。

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

## 云端部署

生产/开发服务器使用 Docker Compose，应用镜像由阿里云 ACR 构建，服务器只拉取镜像，
不在 2GB 节点本地安装依赖或构建镜像。完整流程见 [Linux 部署](./docs/DEPLOYMENT.md)。

发布前完成检查、提交并推送目标分支；服务器执行 Compose 配置校验后，仅重建变更的
API/Worker 服务。Web 静态资源使用服务器 `deploy/web` 挂载目录发布，更新后需核对
首页及其哈希 JS/CSS 文件均返回 HTTP 200。凭据文件、`.env`、数据库和诊断日志不得
提交到 GitHub。

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
- [前后端可复用修复基线](./docs/FRONTEND_REUSABLE_FIXES.md)

## 完整检查

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```
