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
- [需求文档 V5（已确认）](./docs/project-baseline/07-ozonslj需求文档-V5-已确认.md)
- [数据库设计](./docs/DATABASE.md)
- [接口文档](./docs/API.md)
- [前后端开发规范](./docs/DEVELOPMENT_STANDARDS.md)
- [本地开发与调试](./docs/LOCAL_DEVELOPMENT.md)
- [开发计划](./docs/PROJECT_PLAN.md)
- [Linux 部署](./docs/DEPLOYMENT.md)
- [前后端可复用修复基线](./docs/FRONTEND_REUSABLE_FIXES.md)
- [自动化优先设计](./docs/AUTOMATION_FIRST_DESIGN.md)

### 最新项目文档基线（Obsidian 00–25）

- [00 项目文档索引](./docs/project-baseline/00-ozonslj项目文档索引.md)
- [01 需求文档](./docs/project-baseline/01-ozonslj需求文档.md)
- [02 架构设计文档](./docs/project-baseline/02-ozonslj架构设计文档.md)
- [03 需求文档 V2（待确认）](./docs/project-baseline/03-ozonslj需求文档-V2-待确认.md)
- [04 需求文档 V4（已确认）](./docs/project-baseline/04-ozonslj需求文档-V4-已确认.md)
- [05 架构设计 V4（待评审）](./docs/project-baseline/05-ozonslj架构设计文档-V4-待评审.md)
- [06 架构设计 V5（已定档）](./docs/project-baseline/06-ozonslj架构设计文档-V5-已定档.md)
- [07 需求文档 V5（待确认）](./docs/project-baseline/07-ozonslj需求文档-V5-待确认.md)
- [07 需求文档 V5（已确认）](./docs/project-baseline/07-ozonslj需求文档-V5-已确认.md)
- [08 架构设计 V6（待确认）](./docs/project-baseline/08-ozonslj架构设计文档-V6-待确认.md)
- [08 架构设计 V6（已定档）](./docs/project-baseline/08-ozonslj架构设计文档-V6-已定档.md)
- [09 全功能点与开发状态清单](./docs/project-baseline/09-ozonslj全功能点与开发状态清单.md)
- [10 当前需求开发基线](./docs/project-baseline/10-ozonslj当前需求开发基线.md)
- [11 当前架构开发基线](./docs/project-baseline/11-ozonslj当前架构开发基线.md)
- [12 API 接口文档](./docs/project-baseline/12-ozonslj-API接口文档.md)
- [13 PostgreSQL 数据库文档](./docs/project-baseline/13-ozonslj-PostgreSQL数据库文档.md)
- [14 项目开发计划](./docs/project-baseline/14-ozonslj项目开发计划.md)
- [15 Seller 同步接口文档](./docs/project-baseline/15-ozonslj-Seller同步接口文档.md)
- [16 云服务器上下文](./docs/project-baseline/16-ozonslj云服务器上下文.md)
- [17 故障排查与发布恢复](./docs/project-baseline/17-ozonslj故障排查与发布恢复.md)
- [18 RAG 需求文档](./docs/project-baseline/18-ozonslj-RAG需求文档.md)
- [19 RAG 技术架构](./docs/project-baseline/19-ozonslj-RAG技术架构.md)
- [20 RAG 知识治理与数据模型](./docs/project-baseline/20-ozonslj-RAG知识治理与数据模型.md)
- [21 RAG 检索质量设计](./docs/project-baseline/21-ozonslj-RAG检索质量设计.md)
- [22 RAG 目标 API](./docs/project-baseline/22-ozonslj-RAG目标API.md)
- [23 RAG 实施计划](./docs/project-baseline/23-ozonslj-RAG实施计划.md)
- [24 ADR-0010 Chroma 向量索引决策](./docs/project-baseline/24-ozonslj-ADR-0010-Chroma向量索引决策.md)
- [25 自动化优先设计](./docs/project-baseline/25-ozonslj自动化优先设计.md)

## 完整检查

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```
