-- 迁移 0003：为所有工作区业务事实补齐直接组织归属、同组织复合外键和强制 RLS。
-- organization_id 的冗余是有意设计：它让数据库能在不依赖应用 JOIN 约定的情况下
-- 执行租户过滤，并使索引、审计与后台任务都能明确携带租户上下文。

BEGIN;

ALTER TABLE product_offers
    ADD COLUMN IF NOT EXISTS organization_id TEXT;
ALTER TABLE stock_positions
    ADD COLUMN IF NOT EXISTS organization_id TEXT;
ALTER TABLE customer_orders
    ADD COLUMN IF NOT EXISTS organization_id TEXT;
ALTER TABLE postings
    ADD COLUMN IF NOT EXISTS organization_id TEXT;
ALTER TABLE posting_items
    ADD COLUMN IF NOT EXISTS organization_id TEXT;
ALTER TABLE posting_items
    ADD COLUMN IF NOT EXISTS workspace_id TEXT;
ALTER TABLE sync_jobs
    ADD COLUMN IF NOT EXISTS organization_id TEXT;
ALTER TABLE seller_operations
    ADD COLUMN IF NOT EXISTS organization_id TEXT;
ALTER TABLE seller_operations
    ADD COLUMN IF NOT EXISTS user_id TEXT;

-- 先依据受约束的工作区和父记录回填；无法回填的孤儿数据会在 SET NOT NULL 阶段失败，
-- 使迁移显式停止，禁止把未知归属静默放入公共租户。
UPDATE product_offers AS fact
SET organization_id = workspace.organization_id
FROM store_workspaces AS workspace
WHERE fact.workspace_id = workspace.id
  AND fact.organization_id IS NULL;

UPDATE stock_positions AS fact
SET organization_id = workspace.organization_id
FROM store_workspaces AS workspace
WHERE fact.workspace_id = workspace.id
  AND fact.organization_id IS NULL;

UPDATE customer_orders AS fact
SET organization_id = workspace.organization_id
FROM store_workspaces AS workspace
WHERE fact.workspace_id = workspace.id
  AND fact.organization_id IS NULL;

UPDATE postings AS fact
SET organization_id = workspace.organization_id
FROM store_workspaces AS workspace
WHERE fact.workspace_id = workspace.id
  AND fact.organization_id IS NULL;

UPDATE posting_items AS item
SET organization_id = posting.organization_id,
    workspace_id = posting.workspace_id
FROM postings AS posting
WHERE item.posting_id = posting.id
  AND (item.organization_id IS NULL OR item.workspace_id IS NULL);

UPDATE sync_jobs AS fact
SET organization_id = workspace.organization_id
FROM store_workspaces AS workspace
WHERE fact.workspace_id = workspace.id
  AND fact.organization_id IS NULL;

UPDATE seller_operations AS fact
SET organization_id = workspace.organization_id
FROM store_workspaces AS workspace
WHERE fact.workspace_id = workspace.id
  AND fact.organization_id IS NULL;

ALTER TABLE product_offers
    ALTER COLUMN organization_id SET NOT NULL;
ALTER TABLE stock_positions
    ALTER COLUMN organization_id SET NOT NULL;
ALTER TABLE customer_orders
    ALTER COLUMN organization_id SET NOT NULL;
ALTER TABLE postings
    ALTER COLUMN organization_id SET NOT NULL;
ALTER TABLE posting_items
    ALTER COLUMN organization_id SET NOT NULL;
ALTER TABLE posting_items
    ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE sync_jobs
    ALTER COLUMN organization_id SET NOT NULL;
ALTER TABLE seller_operations
    ALTER COLUMN organization_id SET NOT NULL;

-- 复合唯一键是同组织外键的引用目标；任何事实都不能把其他组织的工作区或父记录
-- 绑定到当前 organization_id，即使应用错误传入了可猜测的文本 ID。
CREATE UNIQUE INDEX IF NOT EXISTS uq_store_workspaces_org_workspace
    ON store_workspaces (organization_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_product_offers_org_workspace_offer
    ON product_offers (organization_id, workspace_id, offer_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_postings_org_workspace_id
    ON postings (organization_id, workspace_id, id);

ALTER TABLE product_offers
    ADD CONSTRAINT product_offers_workspace_same_org_fk
    FOREIGN KEY (organization_id, workspace_id)
    REFERENCES store_workspaces(organization_id, id) ON DELETE CASCADE;
ALTER TABLE stock_positions
    ADD CONSTRAINT stock_positions_workspace_same_org_fk
    FOREIGN KEY (organization_id, workspace_id)
    REFERENCES store_workspaces(organization_id, id) ON DELETE CASCADE;
ALTER TABLE stock_positions
    ADD CONSTRAINT stock_positions_offer_same_org_fk
    FOREIGN KEY (organization_id, workspace_id, offer_id)
    REFERENCES product_offers(organization_id, workspace_id, offer_id) ON DELETE CASCADE;
ALTER TABLE customer_orders
    ADD CONSTRAINT customer_orders_workspace_same_org_fk
    FOREIGN KEY (organization_id, workspace_id)
    REFERENCES store_workspaces(organization_id, id) ON DELETE CASCADE;
ALTER TABLE postings
    ADD CONSTRAINT postings_workspace_same_org_fk
    FOREIGN KEY (organization_id, workspace_id)
    REFERENCES store_workspaces(organization_id, id) ON DELETE CASCADE;
ALTER TABLE posting_items
    ADD CONSTRAINT posting_items_posting_same_org_fk
    FOREIGN KEY (organization_id, workspace_id, posting_id)
    REFERENCES postings(organization_id, workspace_id, id) ON DELETE CASCADE;
ALTER TABLE sync_jobs
    ADD CONSTRAINT sync_jobs_workspace_same_org_fk
    FOREIGN KEY (organization_id, workspace_id)
    REFERENCES store_workspaces(organization_id, id) ON DELETE CASCADE;
ALTER TABLE seller_operations
    ADD CONSTRAINT seller_operations_workspace_same_org_fk
    FOREIGN KEY (organization_id, workspace_id)
    REFERENCES store_workspaces(organization_id, id) ON DELETE CASCADE;
ALTER TABLE seller_operations
    ADD CONSTRAINT seller_operations_member_same_org_fk
    FOREIGN KEY (organization_id, user_id)
    REFERENCES organization_members(organization_id, user_id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_product_offers_org_workspace
    ON product_offers (organization_id, workspace_id, position);
CREATE INDEX IF NOT EXISTS idx_stock_positions_org_workspace
    ON stock_positions (organization_id, workspace_id, offer_id);
CREATE INDEX IF NOT EXISTS idx_customer_orders_org_workspace_time
    ON customer_orders (organization_id, workspace_id, ordered_at DESC);
CREATE INDEX IF NOT EXISTS idx_postings_org_workspace_date
    ON postings (organization_id, workspace_id, shipment_date);
CREATE INDEX IF NOT EXISTS idx_posting_items_org_workspace
    ON posting_items (organization_id, workspace_id, posting_id);
CREATE INDEX IF NOT EXISTS idx_sync_jobs_org_workspace_queue
    ON sync_jobs (organization_id, workspace_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_seller_operations_org_workspace_time
    ON seller_operations (organization_id, workspace_id, occurred_at DESC);

ALTER TABLE product_offers ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_offers FORCE ROW LEVEL SECURITY;
ALTER TABLE stock_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_positions FORCE ROW LEVEL SECURITY;
ALTER TABLE customer_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_orders FORCE ROW LEVEL SECURITY;
ALTER TABLE postings ENABLE ROW LEVEL SECURITY;
ALTER TABLE postings FORCE ROW LEVEL SECURITY;
ALTER TABLE posting_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE posting_items FORCE ROW LEVEL SECURITY;
ALTER TABLE sync_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_jobs FORCE ROW LEVEL SECURITY;
ALTER TABLE seller_operations ENABLE ROW LEVEL SECURITY;
ALTER TABLE seller_operations FORCE ROW LEVEL SECURITY;

-- 所有策略同时校验组织上下文和工作区授权。current_setting 缺失时辅助函数返回
-- NULL/false，因此策略默认拒绝，不存在“忘记设置上下文就看到全表”的降级路径。
CREATE POLICY product_offers_tenant_isolation ON product_offers
    USING (organization_id = app_current_organization_id()
           AND app_has_workspace_access(workspace_id))
    WITH CHECK (organization_id = app_current_organization_id()
                AND app_has_workspace_access(workspace_id));
CREATE POLICY stock_positions_tenant_isolation ON stock_positions
    USING (organization_id = app_current_organization_id()
           AND app_has_workspace_access(workspace_id))
    WITH CHECK (organization_id = app_current_organization_id()
                AND app_has_workspace_access(workspace_id));
CREATE POLICY customer_orders_tenant_isolation ON customer_orders
    USING (organization_id = app_current_organization_id()
           AND app_has_workspace_access(workspace_id))
    WITH CHECK (organization_id = app_current_organization_id()
                AND app_has_workspace_access(workspace_id));
CREATE POLICY postings_tenant_isolation ON postings
    USING (organization_id = app_current_organization_id()
           AND app_has_workspace_access(workspace_id))
    WITH CHECK (organization_id = app_current_organization_id()
                AND app_has_workspace_access(workspace_id));
CREATE POLICY posting_items_tenant_isolation ON posting_items
    USING (organization_id = app_current_organization_id()
           AND app_has_workspace_access(workspace_id))
    WITH CHECK (organization_id = app_current_organization_id()
                AND app_has_workspace_access(workspace_id));
CREATE POLICY sync_jobs_tenant_isolation ON sync_jobs
    USING (organization_id = app_current_organization_id()
           AND app_has_workspace_access(workspace_id))
    WITH CHECK (organization_id = app_current_organization_id()
                AND app_has_workspace_access(workspace_id));
CREATE POLICY seller_operations_tenant_isolation ON seller_operations
    USING (organization_id = app_current_organization_id()
           AND app_has_workspace_access(workspace_id))
    WITH CHECK (organization_id = app_current_organization_id()
                AND app_has_workspace_access(workspace_id));

COMMENT ON COLUMN product_offers.organization_id IS
    '事实所属组织；必须与 workspace_id 所属组织一致，并作为 RLS 与索引前缀。';
COMMENT ON COLUMN posting_items.workspace_id IS
    '从履约单冗余的工作区标识；用于直接执行 RLS，不允许与 posting_id 所属工作区不一致。';
COMMENT ON COLUMN posting_items.organization_id IS
    '从履约单冗余的组织标识；通过复合外键防止跨组织明细关联。';
COMMENT ON COLUMN seller_operations.user_id IS
    '执行操作的平台用户；必须是同组织成员。旧 operator_id 仅用于历史迁移兼容，不接受新写入。';

COMMIT;
