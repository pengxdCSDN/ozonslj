-- 迁移 0002：把早期单工作区结构扩展为云端 PostgreSQL/Redis、多组织 SaaS 基线。
-- 本迁移采用 expand-and-contract：先增加组织所有权和授权关系，再回填历史数据，
-- 最后启用外键、非空约束与 RLS。旧 operators 表暂时保留，待认证模块迁移完成后清理。

BEGIN;

CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL CHECK (btrim(name) <> ''),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'disabled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    display_name TEXT NOT NULL CHECK (btrim(display_name) <> ''),
    password_hash TEXT NOT NULL CHECK (btrim(password_hash) <> ''),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'active', 'disabled')),
    email_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT users_email_normalized CHECK (email = lower(btrim(email))),
    CONSTRAINT users_email_unique UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS organization_members (
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'operator', 'viewer')),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('invited', 'active', 'disabled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (organization_id, user_id)
);

-- 历史数据统一归入明确的迁移组织。部署方必须在开放多租户流量前重命名该组织，
-- 并为真实用户建立成员关系；该值不是跨租户共享组织，也不能用于新租户。
INSERT INTO organizations (id, name)
VALUES ('legacy-bootstrap', '历史数据迁移组织')
ON CONFLICT (id) DO NOTHING;

ALTER TABLE seller_accounts
    ADD COLUMN IF NOT EXISTS organization_id TEXT;
ALTER TABLE store_workspaces
    ADD COLUMN IF NOT EXISTS organization_id TEXT;

UPDATE seller_accounts
SET organization_id = 'legacy-bootstrap'
WHERE organization_id IS NULL;

UPDATE store_workspaces AS workspace
SET organization_id = account.organization_id
FROM seller_accounts AS account
WHERE workspace.seller_account_id = account.id
  AND workspace.organization_id IS NULL;

ALTER TABLE seller_accounts
    ALTER COLUMN organization_id SET NOT NULL;
ALTER TABLE store_workspaces
    ALTER COLUMN organization_id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'seller_accounts_organization_fk'
    ) THEN
        ALTER TABLE seller_accounts
            ADD CONSTRAINT seller_accounts_organization_fk
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'store_workspaces_organization_fk'
    ) THEN
        ALTER TABLE store_workspaces
            ADD CONSTRAINT store_workspaces_organization_fk
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT;
    END IF;
END $$;

-- Client-Id 只要求在组织内唯一；不同组织可能授权同一个 Ozon 账号，是否允许共享
-- 由后续账号授权策略决定，但数据库不能把一个租户的标识冲突泄露给另一个租户。
ALTER TABLE seller_accounts
    DROP CONSTRAINT IF EXISTS seller_accounts_ozon_client_id_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_seller_accounts_org_client
    ON seller_accounts (organization_id, ozon_client_id);

-- 工作区与卖家账户必须属于同一组织。先建立可被复合外键引用的唯一键，再添加约束。
CREATE UNIQUE INDEX IF NOT EXISTS uq_seller_accounts_org_id
    ON seller_accounts (organization_id, id);
ALTER TABLE store_workspaces
    DROP CONSTRAINT IF EXISTS store_workspaces_seller_account_id_fkey;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'store_workspaces_account_same_org_fk'
    ) THEN
        ALTER TABLE store_workspaces
            ADD CONSTRAINT store_workspaces_account_same_org_fk
            FOREIGN KEY (organization_id, seller_account_id)
            REFERENCES seller_accounts(organization_id, id)
            ON DELETE CASCADE;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS workspace_memberships (
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    access_level TEXT NOT NULL DEFAULT 'read'
        CHECK (access_level IN ('read', 'operate', 'manage')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (workspace_id, user_id),
    FOREIGN KEY (organization_id, user_id)
        REFERENCES organization_members(organization_id, user_id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_id)
        REFERENCES store_workspaces(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_organization_members_user
    ON organization_members (user_id, status, organization_id);
CREATE INDEX IF NOT EXISTS idx_workspace_memberships_user
    ON workspace_memberships (user_id, organization_id, workspace_id);
CREATE INDEX IF NOT EXISTS idx_store_workspaces_org
    ON store_workspaces (organization_id, is_active, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_seller_accounts_org_status
    ON seller_accounts (organization_id, status, updated_at DESC);

-- 应用必须在每个事务开始时使用 SET LOCAL 写入两个上下文值。缺少任意上下文时，
-- 下列函数返回 NULL/false，使 RLS 默认拒绝访问，而不是退化为跨租户查询。
CREATE OR REPLACE FUNCTION app_current_organization_id()
RETURNS TEXT
LANGUAGE sql
STABLE
AS $$
    SELECT NULLIF(current_setting('app.organization_id', true), '')
$$;

CREATE OR REPLACE FUNCTION app_current_user_id()
RETURNS TEXT
LANGUAGE sql
STABLE
AS $$
    SELECT NULLIF(current_setting('app.user_id', true), '')
$$;

CREATE OR REPLACE FUNCTION app_has_organization_access(target_organization_id TEXT)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT target_organization_id = app_current_organization_id()
       AND EXISTS (
           SELECT 1
           FROM organization_members AS member
           WHERE member.organization_id = target_organization_id
             AND member.user_id = app_current_user_id()
             AND member.status = 'active'
       )
$$;

CREATE OR REPLACE FUNCTION app_has_workspace_access(target_workspace_id TEXT)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM store_workspaces AS workspace
        JOIN organization_members AS member
          ON member.organization_id = workspace.organization_id
         AND member.user_id = app_current_user_id()
         AND member.status = 'active'
        LEFT JOIN workspace_memberships AS membership
          ON membership.organization_id = workspace.organization_id
         AND membership.workspace_id = workspace.id
         AND membership.user_id = member.user_id
        WHERE workspace.id = target_workspace_id
          AND workspace.organization_id = app_current_organization_id()
          AND (
              member.role IN ('owner', 'admin')
              OR membership.user_id IS NOT NULL
          )
    )
$$;

ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations FORCE ROW LEVEL SECURITY;
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_members FORCE ROW LEVEL SECURITY;
ALTER TABLE seller_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE seller_accounts FORCE ROW LEVEL SECURITY;
ALTER TABLE store_workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE store_workspaces FORCE ROW LEVEL SECURITY;
ALTER TABLE workspace_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_memberships FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS organizations_tenant_isolation ON organizations;
CREATE POLICY organizations_tenant_isolation ON organizations
    USING (app_has_organization_access(id))
    WITH CHECK (id = app_current_organization_id());

DROP POLICY IF EXISTS organization_members_tenant_isolation ON organization_members;
CREATE POLICY organization_members_tenant_isolation ON organization_members
    USING (app_has_organization_access(organization_id))
    WITH CHECK (organization_id = app_current_organization_id());

DROP POLICY IF EXISTS seller_accounts_tenant_isolation ON seller_accounts;
CREATE POLICY seller_accounts_tenant_isolation ON seller_accounts
    USING (app_has_organization_access(organization_id))
    WITH CHECK (organization_id = app_current_organization_id());

DROP POLICY IF EXISTS store_workspaces_tenant_isolation ON store_workspaces;
CREATE POLICY store_workspaces_tenant_isolation ON store_workspaces
    USING (app_has_workspace_access(id))
    WITH CHECK (organization_id = app_current_organization_id());

DROP POLICY IF EXISTS workspace_memberships_tenant_isolation ON workspace_memberships;
CREATE POLICY workspace_memberships_tenant_isolation ON workspace_memberships
    USING (app_has_workspace_access(workspace_id))
    WITH CHECK (organization_id = app_current_organization_id());

COMMENT ON TABLE organizations IS
    'SaaS 租户边界。组织停用后应由应用层阻止新同步和写操作，历史事实与审计继续保留。';
COMMENT ON TABLE users IS
    '平台登录身份。密码只保存强哈希；会话、邮箱令牌和设备信息应使用独立表管理。';
COMMENT ON TABLE organization_members IS
    '用户在组织内的角色与状态；owner/admin 可访问组织内工作区，operator/viewer 还需显式工作区授权。';
COMMENT ON TABLE workspace_memberships IS
    '成员级工作区授权。organization_id 同时参与外键，防止把其他组织用户授权到当前工作区。';
COMMENT ON COLUMN seller_accounts.organization_id IS
    '卖家账户所属组织；Client-Id 只在该组织内唯一，查询与错误响应不得泄露其他组织是否存在相同标识。';
COMMENT ON COLUMN store_workspaces.organization_id IS
    '工作区所属组织；必须与 seller_account_id 指向的卖家账户组织一致。';

COMMIT;
