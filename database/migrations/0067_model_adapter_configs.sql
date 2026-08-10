-- 保存模型适配器非敏感配置；凭据仅由后端密钥存储处理，不进入本表。
CREATE TABLE IF NOT EXISTS model_adapter_configs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    adapter TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    base_url TEXT,
    enabled BOOLEAN NOT NULL,
    credential_configured BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_model_adapter_workspace_created
    ON model_adapter_configs (workspace_id, created_at DESC);
ALTER TABLE model_adapter_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_adapter_configs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS model_adapter_isolation ON model_adapter_configs;
CREATE POLICY model_adapter_isolation ON model_adapter_configs
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
