-- 保存外部通知渠道配置；默认预览模式且禁止敏感数据。
CREATE TABLE IF NOT EXISTS external_notification_configs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    channel TEXT NOT NULL CHECK (channel IN ('feishu', 'dingtalk', 'wechat_work', 'email')),
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    template TEXT NOT NULL,
    retry_limit INTEGER NOT NULL CHECK (retry_limit BETWEEN 0 AND 5),
    sensitive_data_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    preview_only BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_external_notification_workspace_created
    ON external_notification_configs (workspace_id, created_at DESC);
ALTER TABLE external_notification_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE external_notification_configs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS external_notification_isolation ON external_notification_configs;
CREATE POLICY external_notification_isolation ON external_notification_configs
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
