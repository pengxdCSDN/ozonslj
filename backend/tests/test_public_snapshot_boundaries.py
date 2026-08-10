from datetime import UTC, datetime

import pytest

from backend.app.domain.public_snapshot import PublicSnapshotError, normalize_public_snapshot


def test_snapshot_rejects_invalid_currency_and_sample_size() -> None:
    records = (
        {"url": "https://example.com", "currency": "rub"},
        {"url": "https://example.com", "sample_size": 0},
    )
    for record in records:
        with pytest.raises(PublicSnapshotError):
            normalize_public_snapshot(record, sampled_at=datetime.now(UTC))
