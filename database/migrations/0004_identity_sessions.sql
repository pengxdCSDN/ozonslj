-- 迁移 0004：为多组织用户建立服务端会话。浏览器只持有随机原始令牌，
-- PostgreSQL 只保存 SHA-256 摘要；active_organization_id 必须是用户的有效组织成员关系。

BEGIN;

CREATE TABLE IF NOT EXISTS user_sessions (
    token_hash CHAR(64) PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    active_organization_id TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    CHECK (expires_at > created_at),
    FOREIGN KEY (active_organization_id, user_id)
        REFERENCES organization_members(organization_id, user_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user_active
    ON user_sessions (user_id, expires_at DESC)
    WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_user_sessions_expiry
    ON user_sessions (expires_at)
    WHERE revoked_at IS NULL;

COMMENT ON TABLE user_sessions IS
    '服务端登录会话；只保存随机令牌的 SHA-256，不保存 Cookie/Bearer 原始令牌。';
COMMENT ON COLUMN user_sessions.active_organization_id IS
    '本会话当前组织；必须与 user_id 的组织成员关系匹配，切换组织应创建或更新受控会话。';
COMMENT ON COLUMN user_sessions.revoked_at IS
    '会话撤销时间；退出、密码重置、账户停用或安全事件发生时写入。';

COMMIT;
