# AGENTS.md

本文件规定 Codex 在 `ozonslj` 仓库中的默认工作方式。详细设计、接口和数据库说明以 `docs/` 中的专项文档为准。

## 如何工作

1. 开始前运行 `git status --short`，识别并保留用户已有改动。不要覆盖、回滚或顺手整理无关文件。
2. 根据任务读取最少必要上下文；实现前检查实际代码和测试，不只依赖文档推断当前行为。
3. 将请求转换为可观察结果，完成最小且完整的改动。诊断任务默认只报告原因；用户明确要求修复时才修改代码。
4. 使用 `CONTEXT.md` 中的统一领域术语。接口、数据库、架构或运行方式变化时同步更新对应文档。
5. 新行为应有测试；缺陷修复优先先添加可复现的回归测试。测试不得访问真实 Ozon 账户。
6. 先运行与改动直接相关的检查，再按风险决定是否执行完整检查。
7. 结束前检查 scoped diff 和 `git diff --check`，说明完成内容、验证结果、未验证项及剩余风险。
8. 新增或修改代码、SQL、schema、迁移脚本时，必须补充准确、详细的中文注释，说明用途、字段语义、约束原因、数据边界和不可违反的业务规则，便于后续 RAG 检索；注释不得泄露凭据或客户敏感数据。
9. 长任务暂停时创建 handoff；临时进度不要写入永久性规范。

## 命令执行与工具协作

为避免 Codex 与 PowerShell 互相竞争、无效重试和上下文/token 浪费，执行命令与文件操作必须遵守以下规则：

1. **简单系统命令**：目录查看、状态检查、单次搜索、单条测试命令等，直接使用 PowerShell，不绕路编写脚本。
2. **批量文件、中文编码、复杂路径或大文本**：优先编写一次性 Python 脚本处理，验证完成后立即删除；脚本不得成为项目运行时依赖，也不得写入敏感信息。
3. **同一种执行方式连续失败 2 次**：立即停止，不得盲目重复；先记录失败现象和退出信息，再判断是否需要更换工具或方案。
4. **先说明失败原因，再更换方案**：禁止仅反复修改路径、引号、转义或命令格式进行试错。每次重试必须有明确的新假设和对应验证方式。
5. **文件操作前后确认**：写入、删除、移动或覆盖前，必须核对目标绝对路径、文件存在性和操作范围；完成后必须检查目标结果、文件状态和必要的内容摘要。
6. **控制输出与 token**：搜索优先限定目录、文件类型和关键词；大文件先按相关行或范围读取；命令设置合理超时，避免输出无关依赖目录、构建产物和完整日志。
7. **工具职责单一**：一个命令只完成一个主要目的；不要把类型检查、构建、截图、清理或多个可能阻塞的步骤拼接成长命令。

## 项目技术栈

- 后端：Python 3.12+、FastAPI、Pydantic Settings、HTTPX、Uvicorn。
- 数据：PostgreSQL + Redis；PostgreSQL 保存业务事实，Redis 保存缓存、队列、锁和短期协调状态。
- 前端：React 19、TypeScript 5、Vite 6、Phosphor Icons。
- 客户端形态：Chrome Extension Manifest V3 侧边栏，并支持响应式 Web 布局。
- 包管理：pnpm 11 workspace。
- 测试与检查：pytest、pytest-asyncio、Ruff、mypy strict、TypeScript project build、Vite build。
- 外部集成：Ozon Seller API；默认开发模式使用 Stub。
- 凭据保护：Windows DPAPI；浏览器端只保存当前工作区 ID，不保存 Ozon 凭据。

## 目录结构

```text
backend/
  app/
    api/                # FastAPI 路由、协议转换、依赖注入
    domain/             # 领域模型、规则和端口
    infrastructure/     # PostgreSQL、Redis、Ozon HTTP、凭据保护等适配器
  tests/                # 后端单元、集成、契约与 API 测试
database/
  postgresql_schema.sql # PostgreSQL 权威结构定义
extension/
  public/               # manifest、service worker 等扩展静态文件
  src/                  # React UI、API 客户端、本地工作区选择状态
docs/                   # 架构、需求、接口、数据库、开发和故障文档
scripts/                # 开发启动、完整检查和 schema 验证脚本
.agents/skills/         # 本项目可复用 Codex 技能
CONTEXT.md              # 统一领域语言
```

依赖方向保持为：API/应用编排 → 领域端口 ← 基础设施适配器。领域层不得依赖 FastAPI、具体数据库驱动或 Ozon 传输模型；API 路由不得直接执行 SQL。

## 开发、测试和构建命令

首次安装：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e . pytest pytest-asyncio ruff mypy
pnpm install
```

启动后端：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-backend.ps1
```

启动扩展监听构建：

```powershell
pnpm dev
```

浏览器加载目录为 `extension/dist`。

常用检查：

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check backend
.\.venv\Scripts\mypy.exe backend\app
.\.venv\Scripts\python.exe scripts\validate_schema.py
pnpm typecheck
pnpm build
```

完整提交前检查：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

前端命令异常时应拆分执行并设置有限超时：

```powershell
.\extension\node_modules\.bin\tsc.CMD -b extension\tsconfig.json --pretty false
Set-Location extension
.\node_modules\.bin\vite.CMD build --configLoader runner --outDir ..\verify-dist --emptyOutDir false
```

不要把类型检查、构建、截图和清理组合为一个长命令。pnpm 在无交互环境要求清理依赖时，设置 `$env:CI = 'true'` 或使用已经安装的项目二进制文件。详见 `docs/troubleshooting.md`。

## 代码风格

### Python

- 使用完整类型标注；mypy strict 必须通过。
- Ruff 行宽 100，规则集以 `pyproject.toml` 为准。
- 导入按标准库、第三方、项目代码分组。
- 避免裸 `except:`、可变默认参数、无边界重试和隐藏异常。
- 公共类、复杂业务函数和非直观决策使用简短 docstring；代码和 SQL 必须提供详细中文注释，解释业务语义、约束和边界。
- 金额不得使用浮点数；SQL 必须参数化；明确事务边界。

### React/TypeScript

- 保持 TypeScript strict；禁止无说明的 `any`。
- 使用函数组件；组件 PascalCase，变量和函数 camelCase。
- API 类型集中维护，不在多个组件复制响应结构。
- 每个异步请求处理加载、成功、空数据、失败、取消和重试。
- 使用语义化 HTML、可访问名称、键盘焦点和非颜色状态提示。
- 侧边栏窄屏与 Web 宽屏均不得产生无必要横向滚动。

### 命名与文档

- 中文文档术语与 `CONTEXT.md` 一致，英文代码名与领域术语一一对应。
- 架构说明写入现有 `docs/` 文档；重要技术取舍写 ADR；可复现故障写入 `docs/troubleshooting.md`；行为约束写成测试。
- 文件统一使用 UTF-8；发现乱码时先确认编码，不复制乱码文本。

## 禁止事项

- 禁止提交或输出 `.env`、API Key、Client ID、访问令牌、真实客户数据、本地数据库和其他敏感信息。
- 禁止在自动化测试中访问真实 Ozon Seller API；使用 Stub、Mock 或契约夹具。
- 禁止猜测 Ozon 路径、字段、枚举、配额或弃用时间；实现前核对官方资料或现有契约。
- 禁止把凭据、客户隐私或敏感响应保存到 `chrome.storage`、日志或截图。
- 禁止关闭类型、Lint、安全或测试规则来让检查通过。
- 禁止在领域层导入 FastAPI 或具体数据库基础设施；禁止 API 路由直接执行 SQL。
- 禁止使用字符串拼接构造 SQL 或接受任意 URL/请求体透传到后端。
- 禁止修改无关文件、删除用户改动，或运行 `git reset --hard`、`git checkout --` 等破坏性命令。
- 禁止未经用户授权提交、推送、发布、调用真实写接口或执行大范围删除。
- 禁止把超时、终止或未实际运行的命令报告为验证通过。

## 提交前检查

- [ ] 功能符合需求和 `CONTEXT.md` 领域语言。
- [ ] 已检查 `git status --short`，变更范围只包含本任务内容。
- [ ] 新行为或缺陷修复有相应测试。
- [ ] pytest、Ruff、mypy、schema 验证、TypeScript 和 Vite 检查按改动风险通过。
- [ ] `git diff --check` 无空白或补丁格式错误。
- [ ] API、schema、前端类型、测试和文档保持一致；代码与 SQL 均有足够的中文注释供 RAG 使用。
- [ ] 没有泄露凭据、客户数据、敏感日志、数据库或构建缓存。
- [ ] Manifest V3 权限保持最小，引用的扩展文件真实存在。
- [ ] 所有失败、跳过或环境阻塞的检查已明确记录。

## 重要文档入口

- `CONTEXT.md`：统一领域语言。
- `docs/REQUIREMENTS.md`：产品需求和范围。
- `docs/PROJECT_PLAN.md`：开发计划。
- `docs/ARCHITECTURE.md`：架构与模块边界。
- `docs/API.md`：HTTP API 契约。
- `docs/DATABASE.md`：数据库模型与约束。
- `database/postgresql_schema.sql`：PostgreSQL 权威 schema。
- `docs/DEVELOPMENT_STANDARDS.md`：详细开发和评审规范。
- `docs/LOCAL_DEVELOPMENT.md`：本地安装、启动和调试。
- `docs/troubleshooting.md`：已知故障、原因和恢复办法。
- `.agents/skills/project-run/SKILL.md`：Codex 项目执行工作流。
