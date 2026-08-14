import pytest

from backend.app.domain.model_adapter import inspect_model_adapter


def test_model_adapter_is_vendor_neutral_and_does_not_expose_secret() -> None:
    result = inspect_model_adapter(
        adapter="openai-compatible", provider="Internal", model="text-model",
        base_url="https://example.invalid/v1", enabled=False, credential_configured=False,
    )
    assert result.adapter == "openai-compatible"
    assert not hasattr(result, "api_key")


def test_enabled_adapter_requires_backend_credential() -> None:
    with pytest.raises(ValueError, match="凭据"):
        inspect_model_adapter(
            adapter="generic", provider="Provider", model="model",
            base_url=None, enabled=True, credential_configured=False,
        )
