import pytest

from backend.app.domain.model_adapter import inspect_model_adapter


def test_remote_model_adapter_requires_https() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        inspect_model_adapter(
            adapter="generic", provider="Provider", model="model",
            base_url="http://model.example/v1", enabled=False, credential_configured=False,
        )


def test_local_model_adapter_may_use_http() -> None:
    result = inspect_model_adapter(
        adapter="generic", provider="Local", model="model",
        base_url="http://localhost:8000/v1", enabled=False, credential_configured=False,
    )
    assert result.base_url == "http://localhost:8000/v1"
