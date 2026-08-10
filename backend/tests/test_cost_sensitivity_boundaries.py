import pytest

from backend.app.domain.cost_sensitivity import CostSensitivityInput, analyze_cost_sensitivity


def test_cost_sensitivity_rejects_zero_price() -> None:
    with pytest.raises(ValueError):
        analyze_cost_sensitivity(CostSensitivityInput(0, 1, 1, 1, 1, 1))
