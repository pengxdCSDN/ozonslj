import pytest

from backend.app.domain.price_batch import PriceChange, validate_price_batch


def test_price_batch_does_not_allow_zero_old_price_to_bypass_limit() -> None:
    result = validate_price_batch([PriceChange("SKU-001", 0, 100)])
    assert result.valid is False


def test_price_batch_rejects_boolean_configuration_limits() -> None:
    with pytest.raises(ValueError):
        validate_price_batch([PriceChange("SKU-001", 100, 100)], max_items=True)
    with pytest.raises(ValueError):
        validate_price_batch([PriceChange("SKU-001", 100, 100)], max_change_percent=True)
