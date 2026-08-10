import pytest

from backend.app.domain.manual_approval import validate_approval_request


def test_approval_requires_bounded_idempotency_key_and_rejects_secrets() -> None:
    with pytest.raises(ValueError, match="幂等键"):
        validate_approval_request(
            command_type="price", payload={"sku": "1"}, idempotency_key="short"
        )
    with pytest.raises(ValueError, match="凭据"):
        validate_approval_request(
            command_type="price", payload={"api_key": "secret"}, idempotency_key="approval-1",
        )
