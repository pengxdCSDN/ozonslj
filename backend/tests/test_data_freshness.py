from datetime import UTC, datetime, timedelta

from backend.app.domain.data_freshness import check_data_freshness


def test_expired_data_requires_refresh() -> None:
    now = datetime(2026, 8, 9, tzinfo=UTC)
    result = check_data_freshness(
        data_domain="seller_product",
        observed_at=now - timedelta(hours=2),
        max_age_seconds=3600,
        now=now,
    )
    assert result.fresh is False
    assert result.requires_refresh is True


def test_freshness_summary_preserves_sync_observability_fields() -> None:
    now = datetime(2026, 8, 9, tzinfo=UTC)
    result = check_data_freshness(
        data_domain="seller_product",
        observed_at=now,
        max_age_seconds=3600,
        now=now,
        last_success_at=now,
        window="last_sync",
        latency_seconds=12,
        record_count=3,
        error_summary=None,
    )
    assert result.window == "last_sync"
    assert result.latency_seconds == 12
    assert result.record_count == 3
