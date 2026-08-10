-- Performance API 凭据与 Seller Api-Key 分离；访问令牌仅保存加密值和过期元数据。
CREATE TABLE IF NOT EXISTS performance_oauth_credentials (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    encrypted_access_token BYTEA NOT NULL,
    encrypted_refresh_token BYTEA,
    expires_at TIMESTAMPTZ NOT NULL,
    credential_scope TEXT NOT NULL DEFAULT 'performance_api' CHECK (credential_scope = 'performance_api'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_performance_oauth_workspace
    ON performance_oauth_credentials (organization_id, workspace_id);
ALTER TABLE performance_oauth_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_oauth_credentials FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS performance_oauth_credentials_isolation ON performance_oauth_credentials;
CREATE POLICY performance_oauth_credentials_isolation ON performance_oauth_credentials
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
