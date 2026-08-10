import pytest

from backend.app.domain.performance_credentials import inspect_performance_credentials


def test_performance_credentials_reject_invalid_expiry() -> None:
    with pytest.raises(ValueError, match="ISO-8601"):
        inspect_performance_credentials(
            client_id="client", access_token=None, refresh_token="refresh", expires_at="tomorrow",
        )


def test_performance_credentials_trim_empty_secrets() -> None:
    result = inspect_performance_credentials(
        client_id=" client ", access_token="  ", refresh_token=" refresh ", expires_at=None,
    )
    assert result.client_id_present is True
    assert result.access_token_present is False
    assert result.refresh_token_present is True
