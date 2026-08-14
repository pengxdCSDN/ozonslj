-- 迁移 0005：使组织角色与需求 V5 一致，并把早期 viewer 规范化为 readonly_analyst。
-- owner/admin 可管理组织；其他角色必须结合 workspace_memberships 限定数据范围。

BEGIN;

ALTER TABLE organization_members
    DROP CONSTRAINT IF EXISTS organization_members_role_check;

UPDATE organization_members
SET role = 'readonly_analyst', updated_at = CURRENT_TIMESTAMP
WHERE role = 'viewer';

ALTER TABLE organization_members
    ADD CONSTRAINT organization_members_role_check CHECK (
        role IN (
            'owner',
            'admin',
            'operations_manager',
            'operator',
            'finance',
            'readonly_analyst'
        )
    );

COMMENT ON COLUMN organization_members.role IS
    '组织角色：owner 所有者、admin 管理员、operations_manager 运营主管、operator 运营人员、finance 财务、readonly_analyst 只读分析人员。除 owner/admin 外还需显式工作区授权。';

COMMIT;
