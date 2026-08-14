import pytest

from backend.app.domain.manual_approval import validate_approval_request


def test_approval_requires_command_and_payload() -> None:
    with pytest.raises(ValueError):
        validate_approval_request(command_type="", payload={}, idempotency_key="")
