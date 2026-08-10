from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = _PROJECT_ROOT / "database" / "migrations" / "0002_multi_tenant_saas.sql"
_FACT_RLS_MIGRATION = (
    _PROJECT_ROOT / "database" / "migrations" / "0003_business_facts_rls.sql"
)
_IDENTITY_MIGRATION = (
    _PROJECT_ROOT / "database" / "migrations" / "0004_identity_sessions.sql"
)
_ROLES_MIGRATION = (
    _PROJECT_ROOT / "database" / "migrations" / "0005_organization_roles.sql"
)
_SYNC_JOB_MIGRATION = (
    _PROJECT_ROOT / "database" / "migrations" / "0006_recoverable_sync_jobs.sql"
)
_QUALITY_MIGRATION = _PROJECT_ROOT / "database" / "migrations" / "0007_data_quality_findings.sql"
_KEYWORD_IMPORT_MIGRATION = (
    _PROJECT_ROOT / "database" / "migrations" / "0008_keyword_report_imports.sql"
)


def test_multi_tenant_migration_contains_required_ownership_constraints() -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")

    required_fragments = (
        "CREATE TABLE IF NOT EXISTS organizations",
        "CREATE TABLE IF NOT EXISTS users",
        "CREATE TABLE IF NOT EXISTS organization_members",
        "CREATE TABLE IF NOT EXISTS workspace_memberships",
        "FOREIGN KEY (organization_id, seller_account_id)",
        "FOREIGN KEY (organization_id, user_id)",
        "ALTER TABLE seller_accounts\n    ALTER COLUMN organization_id SET NOT NULL",
        "ALTER TABLE store_workspaces\n    ALTER COLUMN organization_id SET NOT NULL",
    )
    for fragment in required_fragments:
        assert fragment in sql


def test_multi_tenant_migration_enables_fail_closed_rls() -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")

    assert "current_setting('app.organization_id', true)" in sql
    assert "current_setting('app.user_id', true)" in sql
    assert "FORCE ROW LEVEL SECURITY" in sql
    assert "app_has_workspace_access" in sql
    assert "app_has_organization_access" in sql


def test_business_fact_migration_adds_direct_tenant_ownership() -> None:
    """所有业务事实必须携带组织归属，不能只依赖应用层工作区过滤。"""
    sql = _FACT_RLS_MIGRATION.read_text(encoding="utf-8")

    tenant_tables = (
        "product_offers",
        "stock_positions",
        "customer_orders",
        "postings",
        "posting_items",
        "sync_jobs",
        "seller_operations",
    )
    for table in tenant_tables:
        assert f"ALTER TABLE {table}\n    ADD COLUMN IF NOT EXISTS organization_id TEXT" in sql
        assert f"ALTER TABLE {table}\n    ALTER COLUMN organization_id SET NOT NULL" in sql
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql
        assert f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY" in sql


def test_business_fact_rls_is_fail_closed_and_workspace_scoped() -> None:
    """策略必须同时校验请求组织与工作区授权，缺少上下文时默认拒绝。"""
    sql = _FACT_RLS_MIGRATION.read_text(encoding="utf-8")

    assert "organization_id = app_current_organization_id()" in sql
    assert "app_has_workspace_access(workspace_id)" in sql
    assert "FOREIGN KEY (organization_id, workspace_id)" in sql
    assert "FOREIGN KEY (organization_id, workspace_id, offer_id)" in sql
    assert "FOREIGN KEY (organization_id, user_id)" in sql
    assert "seller_operations_member_same_org_fk" in sql


def test_identity_sessions_store_only_hash_and_require_membership() -> None:
    sql = _IDENTITY_MIGRATION.read_text(encoding="utf-8")

    assert "token_hash CHAR(64) PRIMARY KEY" in sql
    assert "CHECK (token_hash ~ '^[0-9a-f]{64}$')" in sql
    assert "FOREIGN KEY (active_organization_id, user_id)" in sql
    assert "REFERENCES organization_members(organization_id, user_id)" in sql
    assert "revoked_at TIMESTAMPTZ" in sql


def test_organization_roles_match_confirmed_requirements() -> None:
    sql = _ROLES_MIGRATION.read_text(encoding="utf-8")

    for role in (
        "owner",
        "admin",
        "operations_manager",
        "operator",
        "finance",
        "readonly_analyst",
    ):
        assert f"'{role}'" in sql
    assert "SET role = 'readonly_analyst'" in sql
    assert "WHERE role = 'viewer'" in sql


def test_sync_jobs_are_idempotent_and_recoverable() -> None:
    sql = _SYNC_JOB_MIGRATION.read_text(encoding="utf-8")

    for field in (
        "idempotency_key",
        "attempt_count",
        "max_attempts",
        "next_attempt_at",
        "lease_expires_at",
        "heartbeat_at",
        "cancel_requested_at",
    ):
        assert field in sql
    assert "uq_sync_jobs_idempotency" in sql
    assert "idx_sync_jobs_dispatch" in sql
    assert "idx_sync_jobs_expired_lease" in sql


def test_quality_findings_are_isolated_and_fail_closed() -> None:
    sql = _QUALITY_MIGRATION.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS data_quality_findings" in sql
    assert "organization_id TEXT NOT NULL" in sql
    assert "ALTER TABLE data_quality_findings FORCE ROW LEVEL SECURITY" in sql
    assert "current_setting('app.organization_id', true)" in sql
    assert "WITH CHECK (organization_id = current_setting('app.organization_id', true))" in sql
    assert "uq_quality_findings_open_fingerprint" in sql


def test_keyword_import_batches_are_workspace_idempotent_and_isolated() -> None:
    sql = _KEYWORD_IMPORT_MIGRATION.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS keyword_report_imports" in sql
    assert "UNIQUE (organization_id, workspace_id, fingerprint)" in sql
    assert "FORCE ROW LEVEL SECURITY" in sql
    assert "keyword_report_imports_isolation" in sql
