-- WSP-008 Performance 凭据元数据：令牌只进入后端 Secret/加密存储，本表不保存令牌正文。
CREATE TABLE IF NOT EXISTS performance_credential_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    credential_scope TEXT NOT NULL DEFAULT 'performance_api',
    client_id_present BOOLEAN NOT NULL DEFAULT FALSE,
    access_token_present BOOLEAN NOT NULL DEFAULT FALSE,
    refresh_token_present BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ,
    isolated_from_seller BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_performance_credentials_workspace
    ON performance_credential_status (workspace_id);
