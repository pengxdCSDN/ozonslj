-- Ozon 跨境电商运营插件 SQLite 建库脚本
-- 时间字段统一保存 UTC ISO 8601 文本；金额保存十进制定点文本。

PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS operators (
    id TEXT PRIMARY KEY,                         -- 运营人员唯一编号（UUID）
    display_name TEXT NOT NULL,                 -- 运营人员显示名称
    password_hash TEXT,                         -- 本地登录口令哈希；未启用登录时可为空
    is_active INTEGER NOT NULL DEFAULT 1        -- 是否启用：1 启用，0 停用
        CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,                   -- 创建时间（UTC）
    updated_at TEXT NOT NULL                    -- 最后更新时间（UTC）
);

CREATE TABLE IF NOT EXISTS seller_accounts (
    id TEXT PRIMARY KEY,                         -- 卖家账户唯一编号（UUID）
    display_name TEXT NOT NULL,                  -- 卖家账户显示名称
    ozon_client_id TEXT NOT NULL UNIQUE,         -- Ozon Client-Id
    encrypted_api_key BLOB NOT NULL,             -- 加密后的 Ozon Api-Key 密文
    credential_version INTEGER NOT NULL DEFAULT 1, -- 凭据加密版本
    status TEXT NOT NULL DEFAULT 'pending'       -- pending/active/invalid/disabled
        CHECK (status IN ('pending', 'active', 'invalid', 'disabled')),
    verified_at TEXT,                            -- 最近验证成功时间（UTC）
    created_at TEXT NOT NULL,                    -- 创建时间（UTC）
    updated_at TEXT NOT NULL                     -- 最后更新时间（UTC）
);

CREATE TABLE IF NOT EXISTS store_workspaces (
    id TEXT PRIMARY KEY,                         -- 店铺工作区唯一编号
    seller_account_id TEXT NOT NULL UNIQUE,      -- 对应卖家账户编号
    name TEXT NOT NULL,                          -- 工作区名称
    region TEXT,                                 -- Ozon 区域标识
    is_active INTEGER NOT NULL DEFAULT 1         -- 是否启用
        CHECK (is_active IN (0, 1)),
    last_synced_at TEXT,                         -- 最近完整同步时间（UTC）
    created_at TEXT NOT NULL,                    -- 创建时间（UTC）
    updated_at TEXT NOT NULL,                    -- 最后更新时间（UTC）
    FOREIGN KEY (seller_account_id)
        REFERENCES seller_accounts(id) ON DELETE CASCADE
);

-- 当前代码已使用此表。为兼容现有本地垂直切片，暂不强制 workspace_id。
CREATE TABLE IF NOT EXISTS product_offers (
    position INTEGER NOT NULL,                   -- 本地稳定展示顺序
    offer_id TEXT PRIMARY KEY,                   -- 卖家商品报价编号
    ozon_product_id TEXT,                        -- Ozon 商品编号
    name TEXT NOT NULL,                          -- 商品名称
    price TEXT NOT NULL,                         -- 十进制定点价格
    currency TEXT NOT NULL                       -- ISO 4217 三位币种代码
        CHECK (length(currency) = 3),
    available_stock INTEGER NOT NULL             -- 汇总可用库存
        CHECK (available_stock >= 0)
);

CREATE TABLE IF NOT EXISTS stock_positions (
    id TEXT PRIMARY KEY,                         -- 库存位置唯一编号
    workspace_id TEXT NOT NULL,                  -- 所属店铺工作区
    offer_id TEXT NOT NULL,                      -- 对应商品报价编号
    warehouse_id TEXT NOT NULL,                  -- Ozon 仓库编号
    warehouse_name TEXT,                         -- 仓库名称
    fulfillment_type TEXT NOT NULL               -- FBO 或 FBS
        CHECK (fulfillment_type IN ('FBO', 'FBS')),
    available_quantity INTEGER NOT NULL          -- 可用数量
        CHECK (available_quantity >= 0),
    reserved_quantity INTEGER NOT NULL DEFAULT 0 -- 已预留数量
        CHECK (reserved_quantity >= 0),
    synced_at TEXT NOT NULL,                     -- 数据同步时间（UTC）
    UNIQUE (workspace_id, offer_id, warehouse_id, fulfillment_type),
    FOREIGN KEY (workspace_id)
        REFERENCES store_workspaces(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS customer_orders (
    id TEXT PRIMARY KEY,                         -- 本地客户订单编号
    workspace_id TEXT NOT NULL,                  -- 所属店铺工作区
    ozon_order_id TEXT NOT NULL,                 -- Ozon 客户订单编号
    status TEXT NOT NULL,                        -- 标准化订单状态
    currency TEXT NOT NULL,                      -- 订单币种
    total_amount TEXT NOT NULL,                  -- 订单总金额（定点文本）
    ordered_at TEXT NOT NULL,                    -- 下单时间（UTC）
    raw_summary_json TEXT,                       -- 已脱敏的扩展摘要 JSON
    synced_at TEXT NOT NULL,                     -- 数据同步时间（UTC）
    UNIQUE (workspace_id, ozon_order_id),
    FOREIGN KEY (workspace_id)
        REFERENCES store_workspaces(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS postings (
    id TEXT PRIMARY KEY,                         -- 本地履约单编号
    workspace_id TEXT NOT NULL,                  -- 所属店铺工作区
    customer_order_id TEXT,                      -- 对应客户订单编号
    ozon_posting_number TEXT NOT NULL,           -- Ozon 履约单号
    fulfillment_type TEXT NOT NULL               -- FBO 或 FBS
        CHECK (fulfillment_type IN ('FBO', 'FBS')),
    status TEXT NOT NULL,                        -- 标准化履约状态
    shipment_date TEXT,                          -- 计划/实际发货时间（UTC）
    tracking_number TEXT,                        -- 物流追踪号
    synced_at TEXT NOT NULL,                     -- 数据同步时间（UTC）
    UNIQUE (workspace_id, ozon_posting_number),
    FOREIGN KEY (workspace_id)
        REFERENCES store_workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_order_id)
        REFERENCES customer_orders(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS posting_items (
    id TEXT PRIMARY KEY,                         -- 履约商品明细唯一编号
    posting_id TEXT NOT NULL,                    -- 所属履约单编号
    offer_id TEXT NOT NULL,                      -- 商品报价编号
    name TEXT NOT NULL,                          -- 下单时商品名称
    quantity INTEGER NOT NULL                    -- 商品数量
        CHECK (quantity > 0),
    unit_price TEXT,                             -- 单价（定点文本）
    currency TEXT,                               -- 币种代码
    FOREIGN KEY (posting_id)
        REFERENCES postings(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sync_jobs (
    id TEXT PRIMARY KEY,                         -- 同步任务唯一编号
    workspace_id TEXT NOT NULL,                  -- 所属店铺工作区
    resource_type TEXT NOT NULL,                 -- products/stocks/orders/postings/all
    status TEXT NOT NULL                         -- queued/running/succeeded/partial/failed/cancelled
        CHECK (status IN (
            'queued', 'running', 'succeeded', 'partial', 'failed', 'cancelled'
        )),
    requested_by TEXT,                           -- 发起任务的运营人员编号
    processed_count INTEGER NOT NULL DEFAULT 0,  -- 已处理记录数
    failure_count INTEGER NOT NULL DEFAULT 0,    -- 失败记录数
    error_code TEXT,                             -- 脱敏错误代码
    error_message TEXT,                          -- 脱敏错误说明
    created_at TEXT NOT NULL,                    -- 创建时间（UTC）
    started_at TEXT,                             -- 开始时间（UTC）
    completed_at TEXT,                           -- 完成时间（UTC）
    FOREIGN KEY (workspace_id)
        REFERENCES store_workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (requested_by)
        REFERENCES operators(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS seller_operations (
    id TEXT PRIMARY KEY,                         -- 卖家操作唯一编号
    workspace_id TEXT NOT NULL,                  -- 所属店铺工作区
    operator_id TEXT,                            -- 执行操作的运营人员
    operation_type TEXT NOT NULL,                -- 操作类型
    risk_level TEXT NOT NULL                     -- read/reversible_write/destructive_write
        CHECK (risk_level IN ('read', 'reversible_write', 'destructive_write')),
    target_type TEXT,                            -- 目标资源类型
    target_count INTEGER NOT NULL DEFAULT 0,      -- 目标数量
    request_id TEXT,                             -- 关联请求编号
    result TEXT NOT NULL,                        -- success/partial/failed/cancelled
    detail_json TEXT,                            -- 不含密钥和敏感数据的审计详情
    occurred_at TEXT NOT NULL,                   -- 操作发生时间（UTC）
    FOREIGN KEY (workspace_id)
        REFERENCES store_workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (operator_id)
        REFERENCES operators(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_stock_positions_workspace
    ON stock_positions(workspace_id, offer_id);
CREATE INDEX IF NOT EXISTS idx_orders_workspace_status_time
    ON customer_orders(workspace_id, status, ordered_at DESC);
CREATE INDEX IF NOT EXISTS idx_postings_workspace_status
    ON postings(workspace_id, status, shipment_date);
CREATE INDEX IF NOT EXISTS idx_sync_jobs_workspace_status
    ON sync_jobs(workspace_id, resource_type, status);
CREATE INDEX IF NOT EXISTS idx_operations_workspace_time
    ON seller_operations(workspace_id, occurred_at DESC);

COMMIT;
