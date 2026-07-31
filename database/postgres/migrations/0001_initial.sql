/*
 * ozonslj PostgreSQL 基线结构
 *
 * 设计原则：
 * 1. store_workspaces 是卖家业务数据的隔离边界，所有 Ozon 业务表必须携带 workspace_id。
 * 2. Ozon 外部编号使用 text，避免上游编号超出整数范围或格式发生变化。
 * 3. 金额使用最小货币单位 bigint，币种使用 ISO 4217 三位大写代码，禁止浮点数。
 * 4. 上游状态表采用幂等 UPSERT 与软失效；单次分页缺失不能直接删除业务数据。
 * 5. source_payload_json 只允许保存经过白名单筛选的脱敏摘要，严禁保存凭据、完整联系方式和地址。
 * 6. 所有业务时间使用 timestamptz，应用写入 UTC，展示层再转换为用户时区。
 */

CREATE TABLE operators (
    id text PRIMARY KEY,
    display_name text NOT NULL CHECK (length(btrim(display_name)) > 0),
    password_hash text,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE seller_accounts (
    id text PRIMARY KEY,
    display_name text NOT NULL CHECK (length(btrim(display_name)) > 0),
    ozon_client_id text UNIQUE,
    encrypted_api_key bytea,
    credential_version integer NOT NULL DEFAULT 1 CHECK (credential_version > 0),
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'active', 'invalid', 'disabled')),
    verified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (
        status <> 'active'
        OR (
            ozon_client_id IS NOT NULL
            AND length(btrim(ozon_client_id)) > 0
            AND encrypted_api_key IS NOT NULL
            AND octet_length(encrypted_api_key) > 0
        )
    )
);

COMMENT ON TABLE operators IS
    '运营人员身份。负责登录主体、启停状态和审计归属；不保存业务工作区数据。';
COMMENT ON COLUMN operators.id IS '应用生成的稳定文本标识，不使用可变用户名作为主键。';
COMMENT ON COLUMN operators.password_hash IS
    '账号密码的单向哈希；禁止保存明文密码、可逆密文或日志副本。';
COMMENT ON COLUMN operators.is_active IS '账号是否允许登录；停用账号时保留历史审计归属。';

COMMENT ON TABLE seller_accounts IS
    'Ozon Seller API 凭据与验证状态的所有者；API 响应不得返回 encrypted_api_key。';
COMMENT ON COLUMN seller_accounts.ozon_client_id IS
    'Ozon Client-Id。作为外部账号标识处理，不假设其为数字。';
COMMENT ON COLUMN seller_accounts.encrypted_api_key IS
    '经应用密钥加密后的 Api-Key 密文；不得用于查询、日志、RAG 索引或 API 输出。';
COMMENT ON COLUMN seller_accounts.credential_version IS
    '凭据加密格式或主密钥版本，用于后续安全轮换和兼容读取。';
COMMENT ON COLUMN seller_accounts.status IS
    '凭据生命周期：pending 待验证、active 可同步、invalid 验证失败、disabled 人工停用。';
COMMENT ON COLUMN seller_accounts.verified_at IS '最近一次成功验证 Ozon 凭据的 UTC 时间。';

CREATE TABLE store_workspaces (
    id text PRIMARY KEY,
    seller_account_id text NOT NULL UNIQUE
        REFERENCES seller_accounts(id) ON DELETE CASCADE,
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    region text,
    is_active boolean NOT NULL DEFAULT true,
    last_synced_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE store_workspaces IS
    '店铺工作区，是商品、库存、订单、履约、同步任务和运营审计的强制隔离边界。';
COMMENT ON COLUMN store_workspaces.seller_account_id IS
    '当前工作区绑定的卖家账号；首版一个账号只属于一个工作区。';
COMMENT ON COLUMN store_workspaces.region IS '业务区域标签，不用于推断 Ozon API 域名或数据驻留。';
COMMENT ON COLUMN store_workspaces.is_active IS '软停用开关；停用后禁止新同步，但保留已有数据。';
COMMENT ON COLUMN store_workspaces.last_synced_at IS
    '任一核心资源最近完整成功同步的摘要时间，不替代各资源 checkpoint。';

CREATE TABLE product_offers (
    workspace_id text NOT NULL
        REFERENCES store_workspaces(id) ON DELETE CASCADE,
    offer_id text NOT NULL CHECK (length(btrim(offer_id)) > 0),
    position integer NOT NULL CHECK (position >= 0),
    ozon_product_id text,
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    price_minor bigint NOT NULL CHECK (price_minor >= 0),
    currency text NOT NULL
        CHECK (length(currency) = 3 AND currency = upper(currency)),
    available_stock integer NOT NULL CHECK (available_stock >= 0),
    source_status text,
    is_active boolean NOT NULL DEFAULT true,
    source_created_at timestamptz,
    source_updated_at timestamptz,
    last_seen_at timestamptz,
    last_seen_sync_job_id text,
    source_payload_json jsonb,
    synced_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, offer_id),
    CHECK (
        source_payload_json IS NULL
        OR jsonb_typeof(source_payload_json) = 'object'
    )
);

COMMENT ON TABLE product_offers IS
    '自有店铺商品最新状态。以 workspace_id + offer_id 幂等写入，不保存价格历史。';
COMMENT ON COLUMN product_offers.offer_id IS
    '卖家自定义 offer_id；只在工作区内唯一，是商品 UPSERT 冲突键的一部分。';
COMMENT ON COLUMN product_offers.position IS
    '界面展示顺序快照，不是 Ozon 业务不变量，允许变化且不设唯一约束。';
COMMENT ON COLUMN product_offers.ozon_product_id IS 'Ozon 商品编号；保留文本类型以兼容上游格式。';
COMMENT ON COLUMN product_offers.price_minor IS '当前售价的最小货币单位整数，例如 1290.00 RUB 保存为 129000。';
COMMENT ON COLUMN product_offers.available_stock IS
    '兼容现有 API 的汇总可售库存；仓库维度明细以 stock_positions 为准。';
COMMENT ON COLUMN product_offers.source_status IS 'Ozon 返回的商品状态摘要，具体枚举接入端点前核验。';
COMMENT ON COLUMN product_offers.is_active IS
    '软失效标志；仅在完整快照或对账成功后才能将未出现商品置为 false。';
COMMENT ON COLUMN product_offers.last_seen_at IS '本地最近一次在成功处理的上游页面中见到该商品的 UTC 时间。';
COMMENT ON COLUMN product_offers.last_seen_sync_job_id IS '最近见到该商品的同步任务标识，用于快照收尾判断。';
COMMENT ON COLUMN product_offers.source_payload_json IS
    '白名单脱敏上游摘要；禁止 Api-Key、Client-Id、客户联系方式、地址和未知字段。';

CREATE TABLE stock_positions (
    id text PRIMARY KEY,
    workspace_id text NOT NULL,
    offer_id text NOT NULL,
    warehouse_id text NOT NULL CHECK (length(btrim(warehouse_id)) > 0),
    warehouse_name text,
    fulfillment_type text NOT NULL CHECK (fulfillment_type IN ('FBO', 'FBS')),
    available_quantity integer NOT NULL CHECK (available_quantity >= 0),
    reserved_quantity integer NOT NULL DEFAULT 0 CHECK (reserved_quantity >= 0),
    is_active boolean NOT NULL DEFAULT true,
    source_updated_at timestamptz,
    last_seen_at timestamptz,
    last_seen_sync_job_id text,
    synced_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_stock_positions_identity
        UNIQUE (workspace_id, offer_id, warehouse_id, fulfillment_type),
    FOREIGN KEY (workspace_id, offer_id)
        REFERENCES product_offers(workspace_id, offer_id) ON DELETE CASCADE
);

COMMENT ON TABLE stock_positions IS
    '商品在仓库与履约模式维度的最新库存位置；不保存库存变化历史。';
COMMENT ON COLUMN stock_positions.id IS '应用生成的记录标识；幂等冲突键不依赖此字段。';
COMMENT ON COLUMN stock_positions.warehouse_id IS 'Ozon 仓库外部编号，按文本保存。';
COMMENT ON COLUMN stock_positions.fulfillment_type IS '履约模式，仅允许 FBO 或 FBS。';
COMMENT ON COLUMN stock_positions.available_quantity IS '当前可售数量，必须为非负整数。';
COMMENT ON COLUMN stock_positions.reserved_quantity IS '当前已预留数量，必须为非负整数。';
COMMENT ON COLUMN stock_positions.is_active IS
    '软失效标志；完整库存快照成功前不得停用本页未出现的位置。';
COMMENT ON CONSTRAINT uq_stock_positions_identity
    ON stock_positions IS
    '库存幂等键：同一工作区、商品、仓库和履约模式只有一个最新状态。';

CREATE TABLE customer_orders (
    id text NOT NULL,
    workspace_id text NOT NULL
        REFERENCES store_workspaces(id) ON DELETE CASCADE,
    ozon_order_id text NOT NULL CHECK (length(btrim(ozon_order_id)) > 0),
    status text NOT NULL CHECK (length(btrim(status)) > 0),
    currency text NOT NULL
        CHECK (length(currency) = 3 AND currency = upper(currency)),
    total_amount_minor bigint NOT NULL CHECK (total_amount_minor >= 0),
    ordered_at timestamptz NOT NULL,
    source_created_at timestamptz,
    source_updated_at timestamptz,
    last_seen_at timestamptz,
    source_payload_json jsonb,
    synced_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, id),
    UNIQUE (workspace_id, ozon_order_id),
    CHECK (
        source_payload_json IS NULL
        OR jsonb_typeof(source_payload_json) = 'object'
    )
);

COMMENT ON TABLE customer_orders IS
    '客户订单最新业务状态。订单属于工作区，个人信息只允许保存业务所需的脱敏摘要。';
COMMENT ON COLUMN customer_orders.id IS '应用内部订单标识，与 workspace_id 组成可移植复合主键。';
COMMENT ON COLUMN customer_orders.ozon_order_id IS 'Ozon 订单编号；在工作区内唯一并作为 UPSERT 业务键。';
COMMENT ON COLUMN customer_orders.total_amount_minor IS '订单当前总金额的最小货币单位整数。';
COMMENT ON COLUMN customer_orders.ordered_at IS '客户下单时间，使用带时区时间并按 UTC 写入。';
COMMENT ON COLUMN customer_orders.source_payload_json IS
    '订单白名单脱敏摘要；禁止完整姓名、电话、邮箱、地址及未审核字段。';

CREATE TABLE postings (
    id text NOT NULL,
    workspace_id text NOT NULL
        REFERENCES store_workspaces(id) ON DELETE CASCADE,
    customer_order_id text,
    ozon_posting_number text NOT NULL
        CHECK (length(btrim(ozon_posting_number)) > 0),
    fulfillment_type text NOT NULL CHECK (fulfillment_type IN ('FBO', 'FBS')),
    status text NOT NULL CHECK (length(btrim(status)) > 0),
    shipment_date timestamptz,
    tracking_number text,
    source_created_at timestamptz,
    source_updated_at timestamptz,
    last_seen_at timestamptz,
    source_payload_json jsonb,
    synced_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, id),
    UNIQUE (workspace_id, ozon_posting_number),
    FOREIGN KEY (workspace_id, customer_order_id)
        REFERENCES customer_orders(workspace_id, id) ON DELETE RESTRICT,
    CHECK (
        source_payload_json IS NULL
        OR jsonb_typeof(source_payload_json) = 'object'
    )
);

COMMENT ON TABLE postings IS
    'FBO/FBS 履约单最新状态；一个客户订单可以对应多个履约单，也允许先于订单到达。';
COMMENT ON COLUMN postings.customer_order_id IS
    '可空的内部订单标识；复合外键确保只能关联同一工作区订单。';
COMMENT ON COLUMN postings.ozon_posting_number IS 'Ozon 履约单号，在工作区内唯一并用于幂等 UPSERT。';
COMMENT ON COLUMN postings.shipment_date IS '预计或实际发运时间，具体语义由同步适配器按端点映射。';
COMMENT ON COLUMN postings.tracking_number IS '物流跟踪号，属于受控业务数据，不应进入公开日志。';
COMMENT ON COLUMN postings.source_payload_json IS
    '履约白名单脱敏摘要；禁止客户完整联系方式、地址、凭据和未知字段。';

CREATE TABLE posting_items (
    id text PRIMARY KEY,
    workspace_id text NOT NULL,
    posting_id text NOT NULL,
    offer_id text NOT NULL CHECK (length(btrim(offer_id)) > 0),
    ozon_product_id text,
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    quantity integer NOT NULL CHECK (quantity > 0),
    unit_price_minor bigint CHECK (unit_price_minor >= 0),
    currency text CHECK (
        currency IS NULL OR (length(currency) = 3 AND currency = upper(currency))
    ),
    source_payload_json jsonb,
    CHECK (
        (unit_price_minor IS NULL AND currency IS NULL)
        OR (unit_price_minor IS NOT NULL AND currency IS NOT NULL)
    ),
    CHECK (
        source_payload_json IS NULL
        OR jsonb_typeof(source_payload_json) = 'object'
    ),
    FOREIGN KEY (workspace_id, posting_id)
        REFERENCES postings(workspace_id, id) ON DELETE CASCADE
);

COMMENT ON TABLE posting_items IS
    '履约单商品成交快照。刻意不强依赖当前商品表，允许商品下架或履约先同步。';
COMMENT ON COLUMN posting_items.posting_id IS '所属履约单内部标识，复合外键强制同工作区关联。';
COMMENT ON COLUMN posting_items.offer_id IS '成交时的卖家 offer_id 快照，不对当前商品表建立外键。';
COMMENT ON COLUMN posting_items.name IS '成交时商品名称快照，避免后续改名影响历史单据。';
COMMENT ON COLUMN posting_items.unit_price_minor IS '成交单价的最小货币单位整数；未知时与 currency 同时为空。';
COMMENT ON COLUMN posting_items.source_payload_json IS '履约明细的白名单脱敏摘要，不保存客户个人信息。';

CREATE TABLE sync_jobs (
    id text PRIMARY KEY,
    workspace_id text NOT NULL
        REFERENCES store_workspaces(id) ON DELETE CASCADE,
    resource_type text NOT NULL
        CHECK (resource_type IN ('products', 'stocks', 'orders', 'postings', 'all')),
    sync_mode text NOT NULL DEFAULT 'incremental'
        CHECK (sync_mode IN ('initial', 'incremental', 'reconcile')),
    status text NOT NULL
        CHECK (status IN (
            'queued', 'running', 'succeeded', 'partial', 'failed', 'cancelled'
        )),
    requested_by text REFERENCES operators(id) ON DELETE SET NULL,
    window_from timestamptz,
    window_to timestamptz,
    resume_cursor text,
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    processed_count integer NOT NULL DEFAULT 0 CHECK (processed_count >= 0),
    inserted_count integer NOT NULL DEFAULT 0 CHECK (inserted_count >= 0),
    updated_count integer NOT NULL DEFAULT 0 CHECK (updated_count >= 0),
    deactivated_count integer NOT NULL DEFAULT 0 CHECK (deactivated_count >= 0),
    failure_count integer NOT NULL DEFAULT 0 CHECK (failure_count >= 0),
    error_code text,
    error_message text,
    created_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    heartbeat_at timestamptz,
    lease_expires_at timestamptz,
    completed_at timestamptz,
    UNIQUE (workspace_id, id),
    CHECK (
        status NOT IN ('succeeded', 'partial', 'failed', 'cancelled')
        OR completed_at IS NOT NULL
    )
);

COMMENT ON TABLE sync_jobs IS
    '一次资源同步任务的运行状态与分页恢复信息；外部 HTTP 调用不得包在数据库事务中。';
COMMENT ON COLUMN sync_jobs.resource_type IS '同步资源域：商品、库存、订单、履约或一次组合调度。';
COMMENT ON COLUMN sync_jobs.sync_mode IS
    '同步模式：initial 有限首次全量、incremental 时间窗口增量、reconcile 周期对账。';
COMMENT ON COLUMN sync_jobs.resume_cursor IS '当前任务临时分页游标；失败可恢复，但不能充当成功水位。';
COMMENT ON COLUMN sync_jobs.attempt_count IS '任务执行尝试次数，用于限制重试和分析不稳定端点。';
COMMENT ON COLUMN sync_jobs.heartbeat_at IS '运行 Worker 最近一次续租心跳时间。';
COMMENT ON COLUMN sync_jobs.lease_expires_at IS '任务租约过期时间，供其他 Worker 安全接管僵死任务。';
COMMENT ON COLUMN sync_jobs.error_message IS
    '脱敏后的故障摘要；禁止写入请求头、Api-Key、客户 PII 或完整上游响应。';

CREATE TABLE sync_checkpoints (
    workspace_id text NOT NULL
        REFERENCES store_workspaces(id) ON DELETE CASCADE,
    resource_type text NOT NULL
        CHECK (resource_type IN ('products', 'stocks', 'orders', 'postings')),
    watermark text,
    checkpoint_json jsonb,
    last_success_at timestamptz,
    last_full_sync_at timestamptz,
    last_sync_job_id text,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, resource_type),
    FOREIGN KEY (workspace_id, last_sync_job_id)
        REFERENCES sync_jobs(workspace_id, id) ON DELETE RESTRICT,
    CHECK (
        checkpoint_json IS NULL
        OR jsonb_typeof(checkpoint_json) = 'object'
    )
);

COMMENT ON TABLE sync_checkpoints IS
    '工作区各资源的成功同步水位；只有完整成功任务才能推进，部分成功或失败不得更新。';
COMMENT ON COLUMN sync_checkpoints.watermark IS '可比较的上游水位文本，语义由具体资源适配器定义。';
COMMENT ON COLUMN sync_checkpoints.checkpoint_json IS
    '白名单结构化成功水位补充信息；分页中的临时游标应写入 sync_jobs。';
COMMENT ON COLUMN sync_checkpoints.last_success_at IS '最近一次完整成功同步的 UTC 时间。';
COMMENT ON COLUMN sync_checkpoints.last_full_sync_at IS '最近一次 initial 或 reconcile 完整快照成功时间。';
COMMENT ON COLUMN sync_checkpoints.last_sync_job_id IS '产生当前水位的成功同步任务标识。';

CREATE TABLE seller_operations (
    id text PRIMARY KEY,
    workspace_id text NOT NULL
        REFERENCES store_workspaces(id) ON DELETE CASCADE,
    operator_id text REFERENCES operators(id) ON DELETE SET NULL,
    operation_type text NOT NULL CHECK (length(btrim(operation_type)) > 0),
    risk_level text NOT NULL
        CHECK (risk_level IN ('read', 'reversible_write', 'destructive_write')),
    target_type text,
    target_count integer NOT NULL DEFAULT 0 CHECK (target_count >= 0),
    request_id text,
    result text NOT NULL CHECK (result IN ('success', 'partial', 'failed', 'cancelled')),
    detail_json jsonb,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    CHECK (
        detail_json IS NULL
        OR jsonb_typeof(detail_json) = 'object'
    )
);

COMMENT ON TABLE seller_operations IS
    '运营人员及未来智能体执行受控业务操作的不可变审计记录。';
COMMENT ON COLUMN seller_operations.operator_id IS '发起人；账号删除或停用后允许为空但保留历史记录。';
COMMENT ON COLUMN seller_operations.risk_level IS '操作风险分级，用于决定是否需要确认、审批或禁止执行。';
COMMENT ON COLUMN seller_operations.request_id IS '贯穿 API、Worker 和外部调用的请求追踪标识。';
COMMENT ON COLUMN seller_operations.detail_json IS
    '白名单脱敏审计详情；不得保存凭据、完整客户 PII 或可重放的敏感请求。';

CREATE FUNCTION validate_sync_checkpoint_job()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.last_sync_job_id IS NOT NULL
       AND NOT EXISTS (
           SELECT 1
           FROM sync_jobs
           WHERE id = NEW.last_sync_job_id
             AND workspace_id = NEW.workspace_id
             AND status = 'succeeded'
             AND resource_type IN (NEW.resource_type, 'all')
       )
    THEN
        RAISE EXCEPTION '同步水位必须引用同工作区、同资源且已完整成功的同步任务';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_sync_checkpoints_success
BEFORE INSERT OR UPDATE OF workspace_id, resource_type, last_sync_job_id
ON sync_checkpoints
FOR EACH ROW EXECUTE FUNCTION validate_sync_checkpoint_job();

COMMENT ON FUNCTION validate_sync_checkpoint_job() IS
    '阻止失败、部分成功、跨工作区或资源不匹配的任务推进成功同步水位。';

CREATE INDEX idx_product_offers_workspace_stock
    ON product_offers(workspace_id, is_active, available_stock, position);
CREATE INDEX idx_product_offers_workspace_position
    ON product_offers(workspace_id, position, offer_id);
CREATE INDEX idx_product_offers_workspace_source_updated
    ON product_offers(workspace_id, source_updated_at);
CREATE INDEX idx_stock_positions_workspace_quantity
    ON stock_positions(workspace_id, is_active, available_quantity);
CREATE INDEX idx_orders_workspace_status_time
    ON customer_orders(workspace_id, status, ordered_at DESC);
CREATE INDEX idx_orders_workspace_source_updated
    ON customer_orders(workspace_id, source_updated_at);
CREATE INDEX idx_postings_workspace_status_shipment
    ON postings(workspace_id, status, shipment_date);
CREATE INDEX idx_postings_workspace_source_updated
    ON postings(workspace_id, source_updated_at);
CREATE INDEX idx_postings_customer_order
    ON postings(workspace_id, customer_order_id)
    WHERE customer_order_id IS NOT NULL;
CREATE INDEX idx_posting_items_posting
    ON posting_items(workspace_id, posting_id);
CREATE INDEX idx_posting_items_offer
    ON posting_items(workspace_id, offer_id);
CREATE INDEX idx_sync_jobs_workspace_status_created
    ON sync_jobs(workspace_id, resource_type, status, created_at DESC);
CREATE UNIQUE INDEX idx_sync_jobs_one_active_workspace
    ON sync_jobs(workspace_id)
    WHERE status IN ('queued', 'running');
CREATE INDEX idx_sync_jobs_requested_by
    ON sync_jobs(requested_by)
    WHERE requested_by IS NOT NULL;
CREATE INDEX idx_operations_workspace_time
    ON seller_operations(workspace_id, occurred_at DESC);
CREATE INDEX idx_operations_operator
    ON seller_operations(operator_id)
    WHERE operator_id IS NOT NULL;

COMMENT ON INDEX idx_product_offers_workspace_stock IS
    '支持工作区内按启用状态和库存筛选商品；工作区等值列在前，展示顺序在后。';
COMMENT ON INDEX idx_product_offers_workspace_position IS
    '支持商品列表按工作区稳定分页展示；position 非唯一，offer_id 用于稳定排序。';
COMMENT ON INDEX idx_product_offers_workspace_source_updated IS
    '支持按工作区与上游更新时间执行商品时间窗口增量和对账。';
COMMENT ON INDEX idx_stock_positions_workspace_quantity IS
    '支持工作区内筛选有效库存及低库存位置。';
COMMENT ON INDEX idx_orders_workspace_status_time IS
    '支持工作区按订单状态等值过滤并按下单时间倒序查看。';
COMMENT ON INDEX idx_orders_workspace_source_updated IS
    '支持订单按上游更新时间进行时间窗口增量读取。';
COMMENT ON INDEX idx_postings_workspace_status_shipment IS
    '支持工作区按履约状态筛选并查询发运时间范围。';
COMMENT ON INDEX idx_postings_workspace_source_updated IS
    '支持履约单按上游更新时间进行增量读取。';
COMMENT ON INDEX idx_postings_customer_order IS
    '支持从同工作区客户订单定位履约单；排除空关联以减小索引。';
COMMENT ON INDEX idx_posting_items_posting IS '支持按工作区和履约单批量读取成交明细。';
COMMENT ON INDEX idx_posting_items_offer IS
    '支持按工作区与成交时 offer_id 追溯历史履约明细。';
COMMENT ON INDEX idx_sync_jobs_workspace_status_created IS
    '支持按工作区、资源、状态查询任务队列及最近执行历史。';
COMMENT ON INDEX idx_sync_jobs_one_active_workspace IS
    '保证同一工作区最多存在一个 queued 或 running 任务，避免并发同步覆盖水位。';
COMMENT ON INDEX idx_sync_jobs_requested_by IS '支持追溯运营人员发起的同步任务，忽略系统任务空值。';
COMMENT ON INDEX idx_operations_workspace_time IS '支持工作区审计时间线按最近发生时间倒序查询。';
COMMENT ON INDEX idx_operations_operator IS '支持按运营人员追溯非匿名业务操作。';
