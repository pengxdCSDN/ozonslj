-- SYN-009 同步水位：保存最后成功页面游标；失败任务不得推进水位。
CREATE TABLE IF NOT EXISTS sync_watermarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    resource_type TEXT NOT NULL CHECK (resource_type IN ('products', 'stock', 'orders', 'postings')),
    cursor TEXT,
    last_success_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, resource_type)
);
