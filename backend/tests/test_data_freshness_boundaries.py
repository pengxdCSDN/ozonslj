from datetime import UTC, datetime, timedelta

import pytest

from backend.app.domain.data_freshness import check_data_freshness


def test_freshness_rejects_future_observation_and_boolean_age() -> None:
    now = datetime(2026, 8, 9, tzinfo=UTC)
    with pytest.raises(ValueError, match="晚于"):
        check_data_freshness(
            data_domain="seller_product", observed_at=now + timedelta(minutes=1),
            max_age_seconds=60, now=now,
        )
    with pytest.raises(ValueError):
        check_data_freshness(
            data_domain="seller_product", observed_at=now,
            max_age_seconds=True, now=now,
        )
