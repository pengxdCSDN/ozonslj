# ADR-0001：所有环境统一使用 PostgreSQL

- 状态：已接受
- 日期：2026-08-04
- 关联：[需求](../REQUIREMENTS.md)、[架构](../ARCHITECTURE.md)、[数据库](../DATABASE.md)、[项目计划](../PROJECT_PLAN.md)

## 背景

项目早期使用 SQLite + Windows DPAPI 完成本地商品与店铺工作区切片，后续产品基线已经转为云端 PostgreSQL/Redis、多组织 SaaS。继续保留 SQLite 本地/测试模式会形成两套约束、事务、类型、迁移和权限行为，尤其无法可信覆盖 PostgreSQL RLS、并发任务、连接池和云端恢复。

## 决策

本地开发、Stub、Live 调试、自动化测试、集成和云端运行全部只使用 PostgreSQL 作为业务数据库。Redis 只保存可恢复协调状态，不成为第二业务数据库。

SQLite、`DATABASE_PATH`、SQLite schema/适配器/测试夹具和依赖均列为迁移技术债。历史 SQLite 文件只允许作为一次性只读迁移来源，不再作为兼容运行或回滚写入目标。

凭据保护保留通用端口，但正式实现改为应用级信封加密和 Secret 注入；历史 DPAPI 密文不跨机器迁移，用户在新运行时重新授权。

## 后果

正面影响：

- 开发和测试覆盖与生产一致的类型、约束、事务、索引和 RLS 行为。
- 多组织隔离、任务恢复和迁移验证不再依赖 SQLite 模拟。
- 删除双数据库分支后，端口实现、文档和故障面更小。

代价与风险：

- 本地开发必须提供隔离 PostgreSQL；测试基础设施更重。
- PostgreSQL 适配器完成前，现有业务切片不能视为新基线可运行。
- 历史凭据需要重新授权，历史数据迁移必须停写、核对并可回滚应用版本。

## 被否决方案

- **SQLite 用于本地/单元测试，PostgreSQL 用于生产**：否决，因为无法覆盖 RLS、事务并发和 PostgreSQL 类型行为。
- **长期 SQLite/PostgreSQL 双写**：否决，因为增加一致性、故障恢复和排障复杂度，且没有业务必要性。
- **Redis 保存部分业务事实**：否决，因为 Redis 清空或内存压力不能造成不可恢复数据丢失。

## 实施约束

迁移采用 expand-and-contract，详细步骤和停止条件见 `PROJECT_PLAN.md`。Contract 阶段完成前，文档必须把 SQLite 标记为待删除历史实现，不能称为支持模式。

## 清理台账

本节是历史持久化退出的唯一长期台账，活动需求、架构、API、数据库和开发文档不再复制实现细节。

| 对象 | 当前状态 | 删除条件 |
|---|---|---|
| `scripts/validate_schema.py` | 已删除 | PostgreSQL schema 验证由迁移契约测试接管 |
| 业务事实租户隔离 | 已补齐结构 | `0003_business_facts_rls.sql` 已增加直接组织归属、同组织复合外键和强制 RLS；等待真实 PostgreSQL 集成测试 |
| `database/schema.sql` | 已删除 | PostgreSQL schema 与迁移目录是唯一结构来源 |
| `infrastructure/local/sqlite_*` | 已删除 | 默认应用装配已切换 PostgreSQL 商品与工作区适配器 |
| `DATABASE_PATH` 与对应配置 | 已删除 | 应用装配只接受 PostgreSQL DSN/Secret |
| SQLite 测试夹具与驱动引用 | 已删除 | API 使用内存替身，持久化由 PostgreSQL 适配器和迁移契约测试覆盖 |
| 历史确认稿中的相关文字 | 保留只读 | 作为决策过程证据，不作为现行规范入口 |

删除必须原子完成：先落地 PostgreSQL 适配器和验证，再在同一变更中删除旧 schema、适配器、配置与测试。不得先删除仍被应用启动或测试直接加载的文件，也不得为保持兼容建立长期双写。
