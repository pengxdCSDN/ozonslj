from backend.app.domain.rag_reconciliation import build_reconciliation_plan


def test_reconciliation_removes_orphans_and_blocks_missing_metadata() -> None:
    plan = build_reconciliation_plan({"a", "b"}, {"b", "c"}, metadata_ids={"a"})
    assert plan.upsert_ids == ("a",)
    assert plan.delete_ids == ("c",)
    assert plan.missing_metadata_ids == ("b",)
    assert plan.safe_to_publish is False
