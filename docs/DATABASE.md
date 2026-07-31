# 数据库设计文档

## 1. 设计定位

项目当前使用 PostgreSQL 16。数据模型采用关系核心与脱敏 JSONB
摘要结合的混合方案，支持商品、价格、库存、客户订单和 FBO/FBS 履约数据的真实同步。

本地开发和 Linux Docker Compose 节点使用同一套 PostgreSQL 版本化迁移。完整迁移位于
PostgreSQL 结构与版本化迁移唯一来源位于
[`database/postgres/migrations`](../database/postgres/migrations)，不维护第二种数据库或双份 DDL。

## 2. 核心约定

- `store_workspaces` 是全部卖家业务数据的所有权边界。
- Ozon 外部编号统一保存为 `TEXT`，避免精度、前导零和接口类型变化问题。
- 金额保存为最小货币单位整数，不使用 `REAL`。
- 时间保存为 UTC ISO 8601 文本，并区分 Ozon 来源时间与本地同步时间。
- 当前状态表使用 `is_active` 软失效；单页缺失不得触发停用或物理删除。
- 同步使用稳定业务键执行原子 UPSERT，不采用“先查询再插入”。
- JSON 字段必须通过 `json_valid`，并且只能保存后端白名单生成的脱敏摘要。
- Ozon 凭据、完整客户联系方式、地址和未授权原始响应不得进入业务 JSON。

## 3. 表与所有权

| 表名 | 用途 | 主业务键或生命周期 |
|---|---|---|
| `schema_migrations` | 本地结构版本 | 迁移版本永久保留 |
| `operators` | 本地运营人员 | 本地配置 |
| `seller_accounts` | Ozon 卖家账户及加密凭据 | 凭据根实体 |
| `store_workspaces` | 卖家账户隔离工作区 | 每个卖家账户一个工作区 |
| `product_offers` | 商品报价与当前价格、汇总库存 | `(workspace_id, offer_id)` |
| `stock_positions` | 仓库及履约模式库存快照 | 工作区、报价、仓库、履约模式唯一 |
| `customer_orders` | 客户订单当前状态 | 工作区内 Ozon 订单编号唯一 |
| `postings` | FBO/FBS 履约单当前状态 | 工作区内 Ozon 履约单编号唯一 |
| `posting_items` | 履约成交商品快照 | 依赖履约单，不依赖当前商品缓存 |
| `sync_jobs` | 一次有边界的同步执行 | 保存窗口、游标、租约、计数和脱敏错误 |
| `sync_checkpoints` | 各资源的长期同步水位 | `(workspace_id, resource_type)` |
| `seller_operations` | 卖家操作审计 | 不随可重建缓存清理 |

## 4. 当前状态与来源字段

### 4.1 商品报价

`product_offers` 保留当前 API 需要的名称、价格、币种和汇总库存，同时增加：

- `source_status`：Ozon 返回的当前业务状态。
- `is_active`：本地软失效标记。
- `source_created_at`、`source_updated_at`：Ozon 来源时间；接口没有提供时允许为空。
- `last_seen_at`、`last_seen_sync_job_id`：最近一次完整同步看到该记录的时间和任务。
- `source_payload_json`：只包含商品状态、可见性等白名单诊断字段的脱敏摘要。
- `synced_at`：本地最近一次成功写入时间。

`position` 仅用于本地展示顺序，不是 Ozon 业务标识，也不再具有唯一约束。

### 4.2 库存位置

`stock_positions` 以 `(workspace_id, offer_id, warehouse_id, fulfillment_type)` 作为 UPSERT
冲突键。库存同步采用完整快照语义：同步过程中只更新 `last_seen_at`，所有分页成功后才把
本轮未出现的记录设为 `is_active = 0`。

### 4.3 订单与履约

订单和履约单分别使用 Ozon 订单编号和履约单编号作为工作区内业务唯一键，并保存
`source_created_at`、`source_updated_at`、`last_seen_at` 与脱敏摘要。

`posting_items` 保存成交时的报价编号、Ozon 商品编号、名称、数量和单价快照。商品报价
后来下架或尚未同步时，历史履约明细仍可写入和读取。

## 5. 同步任务与检查点

`sync_jobs` 表示一次执行，包含：

- `sync_mode`：`initial`、`incremental` 或 `reconcile`。
- `window_from`、`window_to`：本次时间窗口。
- `resume_cursor`：分页中断恢复游标，不作为长期水位。
- `attempt_count`、处理/新增/更新/停用/失败计数。
- `heartbeat_at`、`lease_expires_at`：异常退出和任务接管判断。
- 状态、开始/完成时间以及脱敏错误。

部分唯一索引保证同一工作区只能存在一个 `queued` 或 `running` 任务。当前以
工作区级串行同步避免写锁竞争和商品、库存、履约依赖竞争。

`sync_checkpoints` 保存长期水位。数据库触发器要求 `last_sync_job_id` 必须引用同工作区、
同资源（或 `all`）且状态为 `succeeded` 的任务，因此失败、部分成功或运行中的任务不能
推进水位。

真实同步采用：

1. 首次有限全量；
2. 订单和履约的重叠时间窗口增量；
3. 商品和库存的分页快照 UPSERT；
4. 周期性完整对账。

外部 HTTP 请求必须在数据库事务外执行，每一页标准化数据使用短事务写入。

## 6. 索引策略

- 商品库存筛选：`(workspace_id, is_active, available_stock, position)`。
- 商品展示：`(workspace_id, position)`。
- 商品、订单、履约来源更新时间：`(workspace_id, source_updated_at)`。
- 库存风险：`(workspace_id, is_active, available_quantity)`。
- 订单筛选：`(workspace_id, status, ordered_at DESC)`。
- 履约筛选：`(workspace_id, status, shipment_date)`。
- 履约与订单、明细关联均按复合外键顺序建立索引。
- 同步任务：工作区、资源、状态、创建时间，并使用活动任务部分唯一索引。
- 可空运营人员外键使用部分索引，减少无意义索引项。

## 7. 版本化迁移

Python 迁移器在数据库初始化时执行：

1. 识别旧版无工作区商品表并沿用原有安全迁移。
2. 对已有工作区 Schema 推断登记 v1 基线。
3. 在 `BEGIN IMMEDIATE` 事务内执行 v2 当前状态表升级和 v3 复合外键升级。
4. 完成复制后交换表，执行当前建库脚本补齐新表、索引和触发器。
5. 运行 `PRAGMA foreign_key_check`，通过后登记迁移校验和并提交。
6. 任一步失败均回滚，保留原表和原业务数据。

已经登记的迁移文件视为不可变；校验和不一致时后端拒绝继续启动，防止不同代码版本静默
解释同一数据库。

## 8. PostgreSQL 类型约定

未来迁移 PostgreSQL 时采用以下映射：

| 业务语义 | PostgreSQL | 说明 |
|---|---|---|
| UTC 业务时间 | `timestamptz` | 应用按 UTC 写入，展示层转换时区 |
| 布尔状态 | `boolean` | 不使用 0/1 模拟 |
| 白名单脱敏摘要 | `jsonb` | 查询需要稳定后再增加表达式或 GIN 索引 |
| 最小货币单位金额 | `bigint` | 不使用浮点金额 |
| Ozon 外部编号 | `text` | 不转换为数值 |

所有业务表继续保留 `workspace_id`，未来可在 PostgreSQL 建立复合索引、外键和行级安全
策略。`database/postgres/migrations` 是唯一 DDL 来源，不维护第二套数据库结构。

## 9. 验证

运行：

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_schema
```

校验器从空数据库运行真实迁移入口，并验证12张表、Schema v3、关键字段、16个索引、2个
checkpoint 触发器、外键、工作区活动任务唯一性及水位成功约束。
