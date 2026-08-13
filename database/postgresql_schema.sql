-- ozonslj PostgreSQL schema
-- PostgreSQL stores business facts. Redis is reserved for cache, queues, locks,
-- rate-limit counters, and other recoverable short-lived coordination state.

BEGIN;

CREATE TABLE IF NOT EXISTS operators (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    password_hash TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS seller_accounts (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    ozon_client_id TEXT NOT NULL UNIQUE,
    encrypted_api_key BYTEA NOT NULL,
    credential_version INTEGER NOT NULL DEFAULT 1 CHECK (credential_version > 0),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'active', 'invalid', 'disabled')),
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS store_workspaces (
    id TEXT PRIMARY KEY,
    seller_account_id TEXT NOT NULL UNIQUE REFERENCES seller_accounts(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    region TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_offers (
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position >= 0),
    offer_id TEXT NOT NULL,
    ozon_product_id TEXT,
    name TEXT NOT NULL,
    -- `name` 始终保存 Ozon 俄文原文；中文展示使用独立派生字段，禁止覆盖事实。
    name_zh TEXT,
    description_ru TEXT,
    description_zh TEXT,
    attributes_ru JSONB,
    attributes_zh JSONB,
    translation_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (translation_status IN ('pending', 'succeeded', 'failed', 'not_required')),
    translation_model TEXT,
    translation_source_hash CHAR(64)
        CHECK (translation_source_hash IS NULL OR translation_source_hash ~ '^[0-9a-f]{64}$'),
    translated_at TIMESTAMPTZ,
    translation_error TEXT,
    embedding_text TEXT,
    embedding_profile_id TEXT,
    price_minor BIGINT NOT NULL CHECK (price_minor >= 0),
    currency CHAR(3) NOT NULL CHECK (currency = UPPER(currency)),
    available_stock INTEGER NOT NULL CHECK (available_stock >= 0),
    synced_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (workspace_id, offer_id),
    UNIQUE (workspace_id, position)
);

CREATE TABLE IF NOT EXISTS stock_positions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    offer_id TEXT NOT NULL,
    warehouse_id TEXT NOT NULL,
    warehouse_name TEXT,
    fulfillment_type TEXT NOT NULL CHECK (fulfillment_type IN ('FBO', 'FBS')),
    available_quantity INTEGER NOT NULL CHECK (available_quantity >= 0),
    reserved_quantity INTEGER NOT NULL DEFAULT 0 CHECK (reserved_quantity >= 0),
    synced_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, offer_id, warehouse_id, fulfillment_type),
    FOREIGN KEY (workspace_id, offer_id)
        REFERENCES product_offers(workspace_id, offer_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS customer_orders (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    ozon_order_id TEXT NOT NULL,
    status TEXT NOT NULL,
    currency CHAR(3) NOT NULL CHECK (currency = UPPER(currency)),
    total_amount_minor BIGINT NOT NULL CHECK (total_amount_minor >= 0),
    ordered_at TIMESTAMPTZ NOT NULL,
    raw_summary JSONB,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, ozon_order_id)
);

CREATE TABLE IF NOT EXISTS postings (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    customer_order_id TEXT REFERENCES customer_orders(id) ON DELETE SET NULL,
    ozon_posting_number TEXT NOT NULL,
    fulfillment_type TEXT NOT NULL CHECK (fulfillment_type IN ('FBO', 'FBS')),
    status TEXT NOT NULL,
    shipment_date DATE,
    tracking_number TEXT,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, ozon_posting_number)
);

CREATE TABLE IF NOT EXISTS posting_items (
    id TEXT PRIMARY KEY,
    posting_id TEXT NOT NULL REFERENCES postings(id) ON DELETE CASCADE,
    offer_id TEXT NOT NULL,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_minor BIGINT CHECK (unit_price_minor >= 0),
    currency CHAR(3) CHECK (currency IS NULL OR currency = UPPER(currency))
);

CREATE TABLE IF NOT EXISTS sync_jobs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    resource_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('queued', 'running', 'succeeded', 'partial', 'failed', 'cancelled')
    ),
    requested_by TEXT REFERENCES operators(id) ON DELETE SET NULL,
    processed_count INTEGER NOT NULL DEFAULT 0 CHECK (processed_count >= 0),
    failure_count INTEGER NOT NULL DEFAULT 0 CHECK (failure_count >= 0),
    error_code TEXT,
    error_message TEXT,
    idempotency_key TEXT,
    requested_user_id TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 10),
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lease_owner TEXT,
    lease_expires_at TIMESTAMPTZ,
    heartbeat_at TIMESTAMPTZ,
    cancel_requested_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS seller_operations (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    operator_id TEXT REFERENCES operators(id) ON DELETE SET NULL,
    operation_type TEXT NOT NULL,
    risk_level TEXT NOT NULL CHECK (
        risk_level IN ('read', 'reversible_write', 'destructive_write')
    ),
    target_type TEXT,
    target_count INTEGER NOT NULL DEFAULT 0 CHECK (target_count >= 0),
    request_id TEXT,
    result TEXT NOT NULL CHECK (result IN ('success', 'partial', 'failed', 'cancelled')),
    detail JSONB,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ==================== RAG 友好的表与字段语义说明 ====================
-- 运营人员表：保存本地后台操作主体。密码哈希和操作审计之间通过 operator_id 关联，
-- 不保存明文密码；删除人员时审计记录保留，但 operator_id 置空。
COMMENT ON TABLE operators IS '运营人员主体；仅保存显示信息、密码哈希和启用状态，不保存明文凭据。';
COMMENT ON COLUMN operators.id IS '运营人员唯一标识；由应用生成并作为审计记录的引用。';
COMMENT ON COLUMN operators.is_active IS '是否允许执行操作；停用不删除历史审计记录。';

-- 卖家账户表：一个 Ozon 卖家账户对应一套 Client-Id 和加密 Api-Key。
-- encrypted_api_key 必须是经过凭据保护适配器处理后的密文，禁止写入明文或日志。
COMMENT ON TABLE seller_accounts IS 'Ozon 卖家账户及加密凭据；业务数据通过 seller_account_id 间接归属账户。';
COMMENT ON COLUMN seller_accounts.ozon_client_id IS 'Ozon Client-Id；全局唯一，响应、日志和前端展示均应脱敏。';
COMMENT ON COLUMN seller_accounts.encrypted_api_key IS '应用使用 Compose Secret 中的 Fernet 主密钥生成的密文 Api-Key；类型 bytea，禁止存明文。';
COMMENT ON COLUMN seller_accounts.credential_version IS '凭据密文格式或 Fernet 主密钥版本；用于安全轮换和兼容读取，不是凭据替换次数。';
COMMENT ON COLUMN seller_accounts.status IS '账户状态：pending 待验证、active 可用、invalid 验证失败、disabled 主动停用。';

-- 工作区表：工作区是业务数据隔离边界。当前一个卖家账户对应一个工作区，
-- 后续如支持多个店铺，可移除 seller_account_id 的唯一约束并新增显式授权关系。
COMMENT ON TABLE store_workspaces IS '卖家业务工作区；商品、库存、订单、任务和审计记录必须通过 workspace_id 隔离。';
COMMENT ON COLUMN store_workspaces.seller_account_id IS '所属卖家账户；级联删除工作区及其业务数据。';
COMMENT ON COLUMN store_workspaces.last_synced_at IS '最近一次完整同步完成时间；不代表某个单独资源已同步。';

-- 商品报价表：保存工作区内可查询的商品报价快照。价格使用最小货币单位整数，
-- 例如 1290.00 RUB 保存为 129000，避免浮点误差；Redis 只可作为该表的可重建缓存。
COMMENT ON TABLE product_offers IS '工作区范围内的商品报价快照；PostgreSQL 是事实来源，Redis 只能缓存查询结果。';
COMMENT ON COLUMN product_offers.name IS 'Ozon 返回的商品名称原文；通常为俄文，禁止被中文译文覆盖。';
COMMENT ON COLUMN product_offers.name_zh IS '云端生成的中文商品名称副本；缺失时界面回退显示俄文原文。';
COMMENT ON COLUMN product_offers.description_ru IS 'Ozon 商品俄文描述原文，用于证据追溯和中俄双语检索。';
COMMENT ON COLUMN product_offers.description_zh IS '云端生成的中文描述副本，不作为 Ozon 原始事实来源。';
COMMENT ON COLUMN product_offers.attributes_ru IS 'Ozon 属性的俄文原始键值；品牌、型号、SKU、数字和单位保持原值。';
COMMENT ON COLUMN product_offers.attributes_zh IS '属性键值的中文展示副本；翻译失败时可以为空。';
COMMENT ON COLUMN product_offers.translation_status IS '翻译任务状态：pending、succeeded、failed 或 not_required。';
COMMENT ON COLUMN product_offers.translation_model IS '生成译文的云端模型标识，不保存 API Key。';
COMMENT ON COLUMN product_offers.translation_source_hash IS '俄文原文规范化后的 SHA-256 指纹，源内容变化时触发重译。';
COMMENT ON COLUMN product_offers.translated_at IS '最近一次成功生成中文译文的 UTC 时间。';
COMMENT ON COLUMN product_offers.translation_error IS '脱敏后的翻译失败摘要，不得写入请求头或完整供应商响应。';
COMMENT ON COLUMN product_offers.embedding_text IS '由中文译文和俄文原文拼接生成的中俄双语向量化文本。';
COMMENT ON COLUMN product_offers.embedding_profile_id IS '向量模型、维度和预处理配置版本；变更时必须重建索引。';
COMMENT ON COLUMN product_offers.price_minor IS '以最小货币单位保存的整数价格；禁止使用 REAL、DOUBLE PRECISION 或浮点金额。';
COMMENT ON COLUMN product_offers.currency IS 'ISO 4217 三位大写币种代码，例如 RUB、CNY。';
COMMENT ON COLUMN product_offers.position IS '工作区内稳定展示顺序；复合唯一约束防止同一位置重复占用。';

-- 库存表：按商品、仓库和履约方式保存库存分解，唯一约束防止重复快照。
COMMENT ON TABLE stock_positions IS '商品库存位置快照；一个商品可对应多个仓库和 FBO/FBS 履约方式。';
COMMENT ON COLUMN stock_positions.available_quantity IS '当前可售数量，必须为非负整数。';
COMMENT ON COLUMN stock_positions.reserved_quantity IS '已预留数量，必须为非负整数；不能与可售数量混用。';

-- 订单、履约单和履约明细：订单是客户交易事实，履约单记录 Ozon 履约状态，
-- 明细记录履约时的商品名称与价格快照，避免商品后续改名影响历史记录。
COMMENT ON TABLE customer_orders IS '工作区内的 Ozon 客户订单事实；同一工作区内 Ozon 订单号唯一。';
COMMENT ON COLUMN customer_orders.raw_summary IS '脱敏后的 Ozon 原始摘要；仅放查询暂不结构化的字段，禁止存凭据和客户敏感信息。';
COMMENT ON TABLE postings IS '订单履约单（FBO/FBS）；订单被清理后履约单仍可保留，customer_order_id 置空。';
COMMENT ON TABLE posting_items IS '履约单商品明细快照；数量必须为正，价格使用最小货币单位整数。';

-- 同步任务表：任务状态必须可从 PostgreSQL 恢复，Redis 队列丢失时可依据本表重新入队。
COMMENT ON TABLE sync_jobs IS '可恢复的数据同步任务；保存状态、处理计数、错误摘要和执行时间线。';
COMMENT ON COLUMN sync_jobs.status IS '任务状态：queued 排队、running 执行中、succeeded 成功、partial 部分成功、failed 失败、cancelled 取消。';
COMMENT ON COLUMN sync_jobs.error_message IS '脱敏后的错误摘要；禁止写入 Api-Key、Client-Id 原值或 Ozon 原始敏感响应。';

-- 卖家操作审计表：记录谁在什么工作区执行了什么风险级别的操作，供追踪和审计使用。
COMMENT ON TABLE seller_operations IS '卖家操作脱敏审计记录；只追加，不作为业务状态事实来源。';
COMMENT ON COLUMN seller_operations.risk_level IS '风险级别：read 只读、reversible_write 可逆写入、destructive_write 破坏性写入。';
COMMENT ON COLUMN seller_operations.detail IS '脱敏结构化审计详情；禁止保存凭据、完整请求体和客户敏感信息。';

CREATE INDEX IF NOT EXISTS idx_product_offers_stock
    ON product_offers (workspace_id, available_stock, position);
CREATE INDEX IF NOT EXISTS idx_stock_positions_workspace
    ON stock_positions (workspace_id, offer_id);
CREATE INDEX IF NOT EXISTS idx_customer_orders_status_time
    ON customer_orders (workspace_id, status, ordered_at DESC);
CREATE INDEX IF NOT EXISTS idx_postings_status_date
    ON postings (workspace_id, status, shipment_date);
CREATE INDEX IF NOT EXISTS idx_posting_items_offer ON posting_items (offer_id);
CREATE INDEX IF NOT EXISTS idx_sync_jobs_queue
    ON sync_jobs (workspace_id, resource_type, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_seller_operations_time
    ON seller_operations (workspace_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_seller_accounts_status
    ON seller_accounts (status, updated_at DESC);

CREATE TABLE IF NOT EXISTS data_quality_findings (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    rule_code TEXT NOT NULL,
    field_name TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('warning', 'error')),
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'accepted', 'resolved', 'ignored')),
    source TEXT NOT NULL DEFAULT 'derived_quality' CHECK (source = 'derived_quality'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_quality_findings_workspace_status
    ON data_quality_findings (workspace_id, status, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_quality_findings_open_fingerprint
    ON data_quality_findings (organization_id, workspace_id, rule_code, field_name, message)
    WHERE status = 'open';

ALTER TABLE data_quality_findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_quality_findings FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS data_quality_findings_isolation ON data_quality_findings;
CREATE POLICY data_quality_findings_isolation ON data_quality_findings
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));

CREATE TABLE IF NOT EXISTS keyword_report_imports (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    fingerprint CHAR(64) NOT NULL,
    source TEXT NOT NULL DEFAULT 'operator_imported' CHECK (source = 'operator_imported'),
    row_count INTEGER NOT NULL CHECK (row_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, workspace_id, fingerprint)
);

CREATE INDEX IF NOT EXISTS idx_keyword_report_imports_workspace_created
    ON keyword_report_imports (workspace_id, created_at DESC);

ALTER TABLE keyword_report_imports ENABLE ROW LEVEL SECURITY;
ALTER TABLE keyword_report_imports FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS keyword_report_imports_isolation ON keyword_report_imports;
CREATE POLICY keyword_report_imports_isolation ON keyword_report_imports
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));

COMMENT ON TABLE data_quality_findings IS '数据质量隔离记录；异常不覆盖业务事实。';

COMMIT;
