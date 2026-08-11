# 数据库设计文档

> 本文是数据模型与持久化规则的持续维护入口，文档职责见 [项目文档索引](./README.md)。所有环境唯一业务数据库为 PostgreSQL。Redis 不是业务数据库，只保存可恢复协调状态。历史持久化实现的退出决策统一记录在 [ADR-0001](./decisions/0001-postgresql-only.md)，不在活动设计中重复维护。

## 1. 存储设计定位

| 项目 | 结论 |
|---|---|
| 工作负载 | 多组织 SaaS OLTP，包含同步任务、审核、审计和分析邻接查询 |
| 数据路线 | 关系型优先，必要的快照/扩展元数据使用受控 `jsonb` |
| 变更类型 | 向唯一 PostgreSQL 运行时增量迁移 |
| 完整性重点 | 组织/工作区隔离、金额精度、任务恢复、跨表所有权和迁移安全 |
| 权威 schema | [`database/postgresql_schema.sql`](../database/postgresql_schema.sql) + [`database/migrations/`](../database/migrations/) |

PostgreSQL 保存业务事实、任务事实、授权关系、审核状态和审计记录。Redis 只保存可重建的 Stream 投递、锁、限流计数、短期令牌缓存和协调状态。新代码、Stub、Live 调试、单元/集成测试和云端运行均使用 PostgreSQL。

## 2. 实现状态

| 能力 | 状态 | 证据或缺口 |
|---|---|---|
| PostgreSQL 基础业务 schema | 已有结构基础 | `database/postgresql_schema.sql` 包含商品、库存、订单、履约、同步任务和审计 |
| 多组织与 RLS 迁移 | 已有结构基础 | `0002_multi_tenant_saas.sql` 建立租户/授权边界，`0003_business_facts_rls.sql` 为全部业务事实补齐直接组织归属、同组织外键和强制 RLS |
| Python PostgreSQL 适配器 | 开发中 | 已完成事务级租户上下文、商品、工作区/凭据/审计和多组织身份适配器及单元测试；登录路由、Redis 限流与完整应用装配待完成 |
| RLS 请求/任务事务上下文 | 尚未开发 | 尚无连接池事务内 `SET LOCAL` 的运行时实现与集成测试 |
| Redis Streams 任务闭环 | 已定档待开发 | 尚无投递、Consumer Group、租约、心跳和恢复实现 |
| V5 选品/Listing/Performance/审核/Agent 表 | 已定档待开发 | V6 定档和迁移包完成前不得提前标记已存在 |

只有 schema 或迁移 SQL 不等于功能已开发。能力至少需要应用用例、持久化适配器、权限上下文和相应测试形成闭环。

### 2.1 迁移顺序

1. `postgresql_schema.sql`：建立单工作区基础业务表，仅作为新库基础结构。
2. `0002_multi_tenant_saas.sql`：建立组织、用户、成员关系、工作区授权和 RLS 上下文函数。
3. `0003_business_facts_rls.sql`：为商品、库存、订单、履约、任务和审计补齐 `organization_id`、同组织复合外键、租户索引与强制 RLS。
4. `0004_identity_sessions.sql`：建立仅保存令牌 SHA-256 的服务端会话，并通过复合外键确保活动组织属于当前用户。
5. `0005_organization_roles.sql`：补齐所有者、管理员、运营主管、运营人员、财务和只读分析角色，并把历史 `viewer` 迁移为 `readonly_analyst`。

迁移必须按顺序执行。`0003` 对无法映射组织或工作区的孤儿数据采用失败关闭：回填后通过 `SET NOT NULL` 和复合外键中止迁移，不把未知数据静默归入共享组织。

新审计写入使用 `seller_operations.user_id`，并通过 `(organization_id, user_id)` 复合外键验证组织成员身份。早期 `operator_id` 只用于历史数据兼容，PostgreSQL 运行时不得继续写入；完成历史审计映射后在 Contract 阶段删除。

## 3. 核心约定

- 标识符按字符串保存，兼容 UUID 和 Ozon 外部编号；不得用浮点或 JavaScript Number 承载可能超出安全范围的上游 ID。
- 金额使用最小货币单位整数 `BIGINT`，API 边界使用十进制字符串；禁止 `REAL`、`DOUBLE PRECISION` 和浮点金额。
- 时间使用 `timestamptz` 并按 UTC 保存；界面按用户时区显示。
- 币种使用 ISO 4217 三位大写代码。
- 所有跨租户业务实体必须直接包含 `organization_id`，或通过数据库可验证的受约束外键链确定组织。
- 工作区级事实必须包含 `workspace_id`；唯一约束和主要索引必须以租户/工作区为前缀，避免跨租户冲突和低效扫描。
- 查询、排序、过滤、授权、幂等和报表依赖的字段必须是一等列；`jsonb` 只保存暂不参与这些操作的受控扩展元数据。
- 可变业务状态、追加式审计、原始/诊断快照和派生读模型分开保存，禁止用一个 JSON 文档混合承担。
- 凭据只保存信封加密密文、密钥版本和必要元数据；Access Token、明文凭据和完整敏感响应不得进入 PostgreSQL。

## 4. 当前实体与所有权

| 实体/表 | 所有权 | 生命周期与关键约束 |
|---|---|---|
| `users` | 平台 | 规范化邮箱唯一；密码只保存强哈希；会话需独立表 |
| `organizations` | 平台 | SaaS 租户边界；停用后阻止新任务，历史事实保留 |
| `organization_members` | 组织 | `(organization_id, user_id)` 唯一；角色和状态受检查约束 |
| `seller_accounts` | 组织 | Client ID 组织内唯一；凭据密文；与 Performance 账户分离 |
| `store_workspaces` | 组织/卖家账户 | 必须与卖家账户同组织；业务事实和授权边界 |
| `workspace_memberships` | 工作区 | 成员必须先属于同组织；显式工作区访问级别 |
| `product_offers` | 工作区 | `(workspace_id, offer_id)` 主键；整数价格与同步时间 |
| `stock_positions` | 工作区/商品 | 商品、仓库、履约方式唯一；非负可售与预留数量 |
| `customer_orders` | 工作区 | Ozon 订单号工作区内唯一；只保存去 PII 的业务摘要 |
| `postings` | 工作区 | 履约编号工作区内唯一；订单删除后可保留履约事实 |
| `posting_items` | 履约单 | 数量为正；名称和价格保存履约时快照 |
| `sync_jobs` | 工作区 | PostgreSQL 中的可恢复任务事实；Redis 丢失后可重建 |
| `seller_operations` | 工作区 | 追加式脱敏审计；不作为业务状态来源 |

`operators` 是早期身份表；多组织认证迁移完成并验证审计引用兼容后才能清理。禁止在同一阶段直接删除旧身份表、切换全部外键并发布新认证代码。

## 5. 已定档待开发的数据族

以下是需求 V5 和架构 V6 已确认的数据边界，不代表表已经创建：

| 数据族 | 主要实体 | 关键规则 |
|---|---|---|
| 身份与令牌 | `user_sessions`、`single_use_tokens`、`mail_delivery_jobs` | 会话只存令牌摘要；单次令牌保存哈希/用途/过期/消费时间；投递任务可恢复 |
| 搜索词导入 | `keyword_report_imports`、`research_keywords` | 文件指纹幂等；来源、统计时间、语言和分层可查询 |
| 公开采样 | `competitor_seeds`、`collection_policies`、`public_product_snapshots` | 仅受控种子；采样时间、估算标识、解析器版本和指纹必填 |
| 选品研究 | `product_research_runs`、`product_decision_documents`、`assumption_versions` | 冻结数据引用、算法版本和输入假设，保证结果可复现 |
| Listing | `listing_drafts`、`listing_versions`、`listing_risk_findings` | 原始草稿不可被检测结果覆盖；版本与审核分离 |
| Performance | `performance_accounts`、`ad_campaign_snapshots`、`ad_metric_snapshots` | 与 Seller 凭据、限流和错误域完全隔离 |
| 审核执行 | `review_requests`、`execution_commands`、`execution_items` | 预览、批准、幂等、分项结果、回读和不确定状态可追溯 |
| Agent | `agent_workflows`、`agent_runs`、`agent_run_steps`、`reports` | 只读工具、工作流/模型/提示词版本和成本可追溯 |
| 任务投递 | `outbox_events` | 先提交数据库事实再投递 Redis；成功投递后记录状态 |

新增迁移前必须为每个实体补齐组织/工作区所有权、删除/保留策略、状态约束、主要查询形状和索引理由。

`single_use_tokens` 使用不可逆哈希作为查找凭据，原始令牌不落库；`purpose` 明确区分邮箱验证、密码重置和扩展授权，数据库约束禁止跨用途消费。消费通过单条条件更新保证原子性：令牌哈希匹配、用途匹配、未过期且 `consumed_at IS NULL` 时才写入消费时间。`mail_delivery_jobs` 不保存密码、Ozon 凭据或完整敏感经营内容。

## 6. RLS 与应用授权

API 应用授权和 PostgreSQL RLS 是两道独立边界，不能互相替代：

1. 请求或 Worker 先完成身份、组织成员关系、角色和工作区授权校验。
2. 每个数据库事务使用 `SET LOCAL` 设置 `app.organization_id` 与 `app.user_id`。
3. 缺少任一上下文时，RLS 函数必须默认拒绝，而不是退化为无租户过滤。
4. Worker 从任务事实恢复用户或服务主体、组织和工作区上下文后才能查询。
5. 连接归还连接池前由事务结束清除本地设置；禁止使用会跨请求泄漏的会话级 `SET`。
6. API、Worker 和迁移账户不得拥有日常 `BYPASSRLS`；迁移/恢复使用独立受控账户和审计流程。

当前迁移只对组织、成员、卖家账户、工作区和工作区授权启用了 RLS。商品、库存、订单、履约、任务和审计表仍需在后续迁移中补齐组织所有权与策略，完成前不得开放多租户生产流量。

## 7. 索引与访问形状

当前主要索引服务于：

- 商品低库存与稳定分页：`(workspace_id, available_stock, position)`。
- 库存按工作区和商品查询：`(workspace_id, offer_id)`。
- 订单状态时间线：`(workspace_id, status, ordered_at DESC)`。
- 履约状态与发货日期：`(workspace_id, status, shipment_date)`。
- 同步任务工作区队列：`(workspace_id, resource_type, status, created_at DESC)`。
- 审计时间线：`(workspace_id, occurred_at DESC)`。
- 组织成员反查和工作区授权：以 `user_id`、`organization_id`、`workspace_id` 为复合键。

后续任务恢复需要围绕 `status`、`next_attempt_at`、`lease_expires_at` 建立可扫描索引；事务出站需要围绕未发布状态和创建时间建立索引。索引必须对应真实查询，不为“可能有用”无边界增加。

## 8. 迁移策略

采用 expand-and-contract：

开发云服务器曾使用早期部署账本 `0001 initial`、`0002 identity_sessions`。迁移运行器只在
这两条记录的名称与 SHA-256 均精确匹配已核验基线时进入兼容路径：先在同一事务中保留旧身份
关系表，再执行权威 `database/migrations/`，并把运营人员的稳定 ID、密码哈希与工作区授权映射
到当前用户/组织模型。兼容路径不得修改旧账本记录，也不得复制第二套长期维护的 SQL 目录；
任一约束、回填或校验失败时必须回滚整个事务并阻止 API/Worker 就绪。

1. **Expand**：先增加 PostgreSQL 新表、可空列、索引和兼容读取，不破坏迁移过程。
2. **Backfill**：按确定批次回填组织所有权与历史数据，记录处理数量和异常；`legacy-bootstrap` 只能是迁移暂存组织。
3. **Validate**：检查空值、重复、跨组织关系、孤儿记录、金额和时间异常；对比旧/新读取结果。
4. **Enforce**：确认回填完成后再增加非空、唯一、复合外键、检查约束和 `FORCE ROW LEVEL SECURITY`。
5. **Switch**：上线 PostgreSQL 适配器，导入并对账历史数据后一次性切换权威读取；切换期间停止旧写入，禁止建立长期双写。
6. **Contract**：兼容窗口、恢复演练和业务验收通过后，按 [ADR-0001 清理台账](./decisions/0001-postgresql-only.md#清理台账) 原子删除旧实现及临时代码。

停止或回滚信号包括：跨租户查询、回填数量不一致、约束无法建立、主要查询明显退化、持续锁等待、恢复演练失败。每次结构升级前执行备份，并只能恢复到隔离数据库验证。

## 9. Redis 边界

Redis Streams + Consumer Group 已确认但尚未开发。Redis 消息只携带任务/命令 ID、组织 ID、工作区 ID、任务类型和跟踪 ID，不携带凭据或大载荷。任务状态、租约、心跳、游标、尝试次数、下次执行时间和结果全部保存到 PostgreSQL；Redis 清空后由 Scheduler 根据数据库事实重建投递。

短期 Performance Access Token 可加密存 Redis 并设置不超过上游有效期的 TTL；长期授权材料仍以加密密文保存到 PostgreSQL。Redis `noeviction`，达到内存限制时任务必须显式失败/退避，不能静默丢弃业务事实。

## 10. 验证要求

### SQL-RAG 中文语义元数据

- `public` 中除迁移账本外的每张业务表都必须有具体中文 `COMMENT ON TABLE`，说明领域用途、事实或快照属性以及主要边界。
- 每个业务字段都必须有具体中文 `COMMENT ON COLUMN`，至少说明字段语义；金额、时间、状态、凭据、租户归属和 JSON 字段还必须说明单位、时区、取值边界或敏感数据限制。
- 已有详细注释不得被通用模板覆盖。`0089_sql_rag_comments.sql` 只补齐缺失项，并在迁移末尾检查完整性；存在无说明的表或字段时必须回滚。
- 后续新增或修改表字段时，结构变更和中文注释必须位于同一迁移，确保数据库系统目录可直接作为 SQL-RAG 的权威结构语料。

- schema 从空库可顺序执行，迁移可重复运行或明确拒绝重复。
- 复合外键阻止跨组织卖家账户/工作区和成员授权关系。
- API 过滤与 RLS 均拒绝跨组织、跨工作区访问。
- 连接池复用不会泄漏上一事务的组织/用户上下文。
- Redis 清空后排队和租约过期任务可从 PostgreSQL 重建。
- 金额转换、币种、时间、状态和幂等约束有自动化测试。
- 自动化测试不得访问真实 Ozon 账户、真实公开页面或真实模型服务。

当前已有 `backend/tests/test_postgresql_saas_migration.py` 对迁移关键片段做契约检查；后续必须增加真实隔离 PostgreSQL 的迁移、RLS、并发和恢复集成测试。旧的 `scripts/validate_schema.py` 已删除，不得在文档中继续报告该命令可用。
## 2026-08-09 开发状态同步

- Seller 商品、库存、订单和履约快照及其历史查询均以 PostgreSQL 为事实来源；Redis 不保存不可恢复的业务事实。
- ERP 适配数据进入统一模型前，金额字段必须有对应 ISO 4217 三位币种；缺失或不一致的数据进入边界拒绝/质量处理，不静默补默认币种。
- 同步水位只在分页任务完整成功后更新，失败页不推进长期水位，便于从 PostgreSQL 恢复任务。
