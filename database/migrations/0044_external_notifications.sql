-- AI-010 外部通知配置：仅保存渠道、模板和重试策略；凭据由后端 Secret 管理，默认仅预览不发送。
CREATE TABLE IF NOT EXISTS external_notification_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('feishu', 'dingtalk', 'wechat_work', 'email')),
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    template TEXT NOT NULL,
    retry_limit INTEGER NOT NULL CHECK (retry_limit BETWEEN 0 AND 5),
    sensitive_data_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    preview_only BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_notification_configs_workspace_channel
    ON external_notification_configs (workspace_id, channel);
