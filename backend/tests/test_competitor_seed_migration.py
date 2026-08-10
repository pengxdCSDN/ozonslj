from pathlib import Path


def test_competitor_seed_migration_is_workspace_scoped_and_rls_protected() -> None:
    root = Path(__file__).resolve().parents[2]
    sql = (root / "database" / "migrations" / "0009_competitor_seeds.sql").read_text(
        encoding="utf-8"
    )

    assert "UNIQUE (organization_id, workspace_id, url)" in sql
    assert "FORCE ROW LEVEL SECURITY" in sql
    assert "competitor_seeds_isolation" in sql
