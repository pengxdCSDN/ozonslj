-- AI-001 模型适配器配置：保存非敏感配置和凭据存在状态，绝不保存 API Key 或访问令牌。
CREATE TABLE IF NOT EXISTS model_adapter_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    adapter TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    base_url TEXT,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    credential_configured BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
