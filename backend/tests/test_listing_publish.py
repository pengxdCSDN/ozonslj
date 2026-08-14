from backend.app.domain.listing_publish import execute_controlled_publish


def test_publish_rejects_unapproved_version() -> None:
    result = execute_controlled_publish(
        idempotency_key="cmd-1", version=2, status="review", requested_text="新标题"
    )
    assert result.status == "rejected"
    assert "审核通过" in result.message


def test_publish_readback_detects_mismatch() -> None:
    result = execute_controlled_publish(
        idempotency_key="cmd-2", version=2, status="approved",
        requested_text="新标题", readback_text="旧标题",
    )
    assert result.status == "partial"
    assert result.matched is False
