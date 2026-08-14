from datetime import UTC, datetime
from decimal import Decimal

import pytest

from backend.app.domain.public_snapshot import PublicSnapshotError, normalize_public_snapshot


def test_public_snapshot_normalizes_supported_fields() -> None:
    snapshot = normalize_public_snapshot(
        {
            "url": "https://example.com/item",
            "price_minor": "1299",
            "rating": "4.7",
            "review_count": 12,
            "attributes": {"color": "red"},
            "sample_size": 3,
        },
        sampled_at=datetime.now(UTC),
    )
    assert snapshot.price_minor == 1299
    assert snapshot.rating == Decimal("4.7")
    assert snapshot.sample_size == 3


def test_public_snapshot_rejects_invalid_rating() -> None:
    with pytest.raises(PublicSnapshotError):
        normalize_public_snapshot(
            {"url": "https://example.com", "rating": "5.1"},
            sampled_at=datetime.now(UTC),
        )
