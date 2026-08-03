ALTER TABLE operators
    ADD COLUMN email text,
    ADD COLUMN role text NOT NULL DEFAULT 'operator'
        CHECK (role IN ('admin', 'supervisor', 'operator', 'finance', 'readonly_analyst'));

CREATE UNIQUE INDEX operators_email_unique_idx ON operators (lower(email))
    WHERE email IS NOT NULL;

CREATE TABLE workspace_memberships (
    operator_id text NOT NULL REFERENCES operators(id) ON DELETE CASCADE,
    workspace_id text NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (operator_id, workspace_id)
);

CREATE INDEX workspace_memberships_workspace_idx
    ON workspace_memberships (workspace_id, operator_id);

CREATE TABLE user_sessions (
    token_hash text PRIMARY KEY CHECK (length(token_hash) = 64),
    operator_id text NOT NULL REFERENCES operators(id) ON DELETE CASCADE,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    CHECK (expires_at > created_at)
);

CREATE INDEX user_sessions_operator_active_idx
    ON user_sessions (operator_id, expires_at)
    WHERE revoked_at IS NULL;

COMMENT ON TABLE workspace_memberships IS
    '操作员可访问的店铺工作区；角色由 operators.role 定义，成员关系仅限定数据范围。';
COMMENT ON TABLE user_sessions IS
    '服务端登录会话，只保存随机令牌的 SHA-256 摘要，不保存浏览器持有的原始令牌。';
