import pytest

from backend.app.domain.listing_publish import execute_controlled_publish


def test_publish_rejects_invalid_version() -> None:
    with pytest.raises(ValueError):
        execute_controlled_publish(
            idempotency_key="cmd", version=0, status="approved", requested_text="标题"
        )


def test_publish_rejects_empty_text() -> None:
    with pytest.raises(ValueError):
        execute_controlled_publish(
            idempotency_key="cmd", version=1, status="approved", requested_text=" "
        )
