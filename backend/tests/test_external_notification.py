import pytest

from backend.app.domain.external_notification import (
    render_notification_preview,
    validate_notification_config,
)


def test_notification_config_is_preview_only_and_blocks_sensitive_data() -> None:
    result = validate_notification_config(
        channel="feishu", enabled=False, template="{{headline}}",
        retry_limit=2, sensitive_data_allowed=False,
    )
    assert result.preview_only is True
    assert result.sensitive_data_allowed is False
    with pytest.raises(ValueError):
        validate_notification_config(
            channel="email", enabled=True, template="secret", retry_limit=1,
            sensitive_data_allowed=True,
        )


def test_notification_preview_rejects_unknown_template_fields() -> None:
    assert render_notification_preview("{{headline}}", {"headline": "库存"}) == "库存"
    with pytest.raises(ValueError):
        render_notification_preview("{{access_token}}", {"access_token": "secret"})
