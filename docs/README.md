# ozonslj 项目文档索引

本目录保存可持续指导需求、设计、开发、测试、部署和排障的项目知识。版本确认稿用于记录某次定档范围；可复用规则必须沉积到对应权威文档，避免后续开发只能从历史版本稿中拼接上下文。

## 1. 文档职责

| 文档 | 权威内容 | 不应保存 |
|---|---|---|
| [`REQUIREMENTS.md`](./REQUIREMENTS.md) | 当前已进入开发基线的产品范围、角色、业务规则和验收条件 | 技术实现细节 |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | 当前系统边界、模块、依赖方向、运行拓扑和架构不变量 | 单次讨论过程 |
| [`API.md`](./API.md) | 已实现接口与已定档目标接口的 HTTP 契约 | Ozon 上游接口猜测 |
| [`DATABASE.md`](./DATABASE.md) | PostgreSQL/Redis 数据边界、实体所有权、约束、索引和迁移原则 | 仅存在于旧持久化实现的规则 |
| [`PROJECT_PLAN.md`](./PROJECT_PLAN.md) | 实施顺序、阶段状态、退出条件和未完成工作 | 永久架构规则 |
| [`FEATURE_INVENTORY.md`](./FEATURE_INVENTORY.md) | 全部细功能点、页面数量、开发状态和后续顺序 | 需求确认过程或临时进度日志 |
| [`DEVELOPMENT_STANDARDS.md`](./DEVELOPMENT_STANDARDS.md) | 可重复执行的代码、测试、数据和评审规范 | 临时进度 |
| [`LOCAL_DEVELOPMENT.md`](./LOCAL_DEVELOPMENT.md) | 本地安装、配置、启动、Stub 和检查方式 | 云端生产凭据 |
| [`troubleshooting.md`](./troubleshooting.md) | 已复现故障的现象、原因、恢复和预防 | 未验证猜测 |
| [`decisions/`](./decisions/) | 已接受或被替代的重大技术决策、背景与权衡 | 详细接口/schema 规范 |
| [`DELIVERY_BASELINE.md`](./DELIVERY_BASELINE.md) | WorkBuddy 交付方案提炼出的新增事实基线 | 替代已确认需求或架构 |
| `REQUIREMENTS-V*-PENDING.md`、`ARCHITECTURE-V*-PENDING.md` | 逐项确认过程和待定决策 | 当前权威规则的唯一副本 |
| `REQUIREMENTS-V*.md`、`ARCHITECTURE-V*.md` | 已定档版本快照和变更历史 | 日常持续维护入口 |

## 2. 状态标识

权威文档描述能力时必须区分：

- **已开发**：代码、应用闭环和相应自动化测试均存在。
- **部分开发**：只有 schema、端口、Stub、配置或单层实现，尚未形成可运行闭环。
- **已定档待开发**：产品或架构已经确认，但仓库尚无完整实现。
- **待确认**：仍会影响实现方向，禁止提前按某一方案开发。
- **历史/已废弃**：只为迁移或追溯保留，不是正式运行基线。

只有数据库表或迁移 SQL 不代表功能已经开发；只有界面草稿也不代表后端能力已经完成。

## 3. 更新规则

1. 需求确认后，将稳定业务规则同步到 `REQUIREMENTS.md`，版本稿保留确认快照。
2. 架构确认过程中，已开发能力按代码和测试写入 `ARCHITECTURE.md`；新决策先记录在待确认稿，确认后沉积到对应专项文档。
3. API、表结构、迁移、运行方式或阶段顺序发生变化时，同一改动必须同步更新对应权威文档。
4. 重大技术取舍及其替代方案单独写入 `docs/decisions/` ADR；不要把讨论过程长期塞在总体架构文档。
5. 同一条规则只设一个权威归属，其余文档使用链接引用；版本快照中的重复内容仅用于历史追溯。
6. 文档不得把规划能力写成已实现。结束任务前以实际代码、测试、schema 和部署文件复核状态，并执行 `git diff --check`。

## 4. 当前版本关系

- 产品确认基线：[`REQUIREMENTS-V5.md`](./REQUIREMENTS-V5.md)。
- 当前架构定档版本：[`ARCHITECTURE-V6.md`](./ARCHITECTURE-V6.md)，自 2026-08-04 起替代 V5；当前文档修订号为 1，已补充实施级运行架构。
- 历史架构快照：[`ARCHITECTURE-V5.md`](./ARCHITECTURE-V5.md)。
- V6 中尚未开发的能力继续标记为“已定档待开发”，不能仅因定档而标记为已实现。
- 已接受 ADR：[ADR-0001：所有环境统一使用 PostgreSQL](./decisions/0001-postgresql-only.md)。

## 5. 维护检查清单

- 文档中的“当前状态”与仓库代码和测试一致。
- `ARCHITECTURE.md`、`API.md`、`DATABASE.md`、`LOCAL_DEVELOPMENT.md` 只描述 PostgreSQL 基线；历史实现细节只保留在 ADR 和迁移计划中。
- 新接口在 `API.md` 标明“已实现”或“目标契约”。
- 新表和迁移在 `DATABASE.md` 说明租户所有权、约束和主要查询索引。
- 新运行组件在 `ARCHITECTURE.md` 和 `PROJECT_PLAN.md` 同时记录资源预算与启用阶段。
- 可复现故障才写入 `troubleshooting.md`。
