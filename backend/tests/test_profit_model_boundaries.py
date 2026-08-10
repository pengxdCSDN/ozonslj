import pytest

from backend.app.domain.profit_model import ProfitModelInput, calculate_profit_model


def test_profit_model_rejects_negative_cost() -> None:
    with pytest.raises(ValueError):
        calculate_profit_model(ProfitModelInput(1000, -1, 10, 10, 10, 10, 10))


def test_profit_model_rejects_zero_selling_price() -> None:
    with pytest.raises(ValueError):
        calculate_profit_model(ProfitModelInput(0, 1, 1, 1, 1, 1, 1))
