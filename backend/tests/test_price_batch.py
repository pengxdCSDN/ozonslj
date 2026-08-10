from backend.app.domain.price_batch import PriceChange, validate_price_batch


def test_price_batch_rejects_more_than_twenty_items() -> None:
    items = [PriceChange(f"SKU-{index}", 100, 110) for index in range(21)]
    result = validate_price_batch(items)
    assert result.valid is False
    assert result.total_items == 21


def test_price_batch_rejects_change_over_ten_percent() -> None:
    result = validate_price_batch([PriceChange("SKU-001", 1000, 1110)])
    assert result.valid is False
    assert result.max_change_percent == 10


def test_price_batch_rejects_price_below_profit_line() -> None:
    result = validate_price_batch([PriceChange("SKU-001", 1000, 900, 1000)])
    assert result.valid is False


def test_price_batch_rejects_duplicate_skus_case_insensitively() -> None:
    result = validate_price_batch([
        PriceChange("SKU-001", 1000, 1050),
        PriceChange(" sku-001 ", 1000, 1050),
    ])
    assert result.valid is False
