from datetime import UTC, datetime, timedelta

import pytest

from backend.app.domain.performance_oauth import PerformanceOAuthError, build_performance_token


def test_performance_token_is_separate_and_refreshes_early() -> None:
    token = build_performance_token(
        "perf-token", datetime.now(UTC) + timedelta(minutes=2), "refresh"
    )
    assert token.credential_scope == "performance_api"
    assert token.refresh_token_present is True
    assert token.needs_refresh is True


def test_performance_token_rejects_naive_expiry() -> None:
    with pytest.raises(PerformanceOAuthError):
        build_performance_token("perf-token", datetime.now(), None)
