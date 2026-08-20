from backend.app.domain.performance_credentials import inspect_performance_credentials


def test_performance_credentials_are_isolated_from_seller() -> None:
    result = inspect_performance_credentials(
        client_id="client", client_secret="secret", access_token=None,
        refresh_token="refresh", expires_at=None
    )
    assert result.credential_scope == "performance_api"
    assert result.ready is True
    assert result.isolated_from_seller is True


def test_expired_access_token_is_not_ready_without_refresh_token() -> None:
    result = inspect_performance_credentials(
        client_id="client", client_secret="secret", access_token="access", refresh_token=None,
        expires_at="2020-01-01T00:00:00+00:00",
    )
    assert result.access_token_present is True
    assert result.ready is False


def test_expired_access_token_can_refresh_with_refresh_token() -> None:
    result = inspect_performance_credentials(
        client_id="client", client_secret="secret", access_token="access", refresh_token="refresh",
        expires_at="2020-01-01T00:00:00+00:00",
    )
    assert result.ready is True
