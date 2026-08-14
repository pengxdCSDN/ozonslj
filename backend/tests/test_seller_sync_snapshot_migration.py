from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_seller_sync_snapshot_migration_protects_json_shape_source_and_cursor() -> None:
    migration = (
        PROJECT_ROOT / "database" / "migrations" / "0088_seller_sync_snapshot_constraints.sql"
    )
    sql = migration.read_text(encoding="utf-8")
    assert sql.count("jsonb_typeof(items) = 'array'") == 4
    assert sql.count("source = 'seller_api'") == 4
    assert sql.count("length(btrim(cursor)) > 0") == 4
