-- DAT-009 Seller 商品同步快照：只保存已规范化的只读预览，真实写入由后续 Worker/适配器负责。
CREATE TABLE IF NOT EXISTS seller_product_sync_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    cursor TEXT,
    total INTEGER NOT NULL CHECK (total >= 0),
    items JSONB NOT NULL,
    source TEXT NOT NULL DEFAULT 'seller_api',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_seller_product_sync_workspace_created
    ON seller_product_sync_snapshots (workspace_id, created_at DESC);
