import pytest

from backend.app.domain.external_notification import validate_notification_config


def test_notification_rejects_boolean_retry_and_oversized_template() -> None:
    with pytest.raises(ValueError):
        validate_notification_config(
            channel="feishu", enabled=False, template="test",
            retry_limit=True, sensitive_data_allowed=False,
        )
    with pytest.raises(ValueError, match="5000"):
        validate_notification_config(
            channel="feishu", enabled=False, template="x" * 5001,
            retry_limit=0, sensitive_data_allowed=False,
        )
