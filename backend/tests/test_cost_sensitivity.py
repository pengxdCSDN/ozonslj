from backend.app.domain.cost_sensitivity import CostSensitivityInput, analyze_cost_sensitivity


def test_cost_sensitivity_returns_downside_base_and_upside() -> None:
    scenarios = analyze_cost_sensitivity(CostSensitivityInput(10000, 3000, 700, 1000, 500, 200))
    assert [item.change_percent for item in scenarios] == [-20, 0, 20]
    assert scenarios[0].profit_minor > scenarios[1].profit_minor > scenarios[2].profit_minor
    assert scenarios[2].margin_percent < scenarios[1].margin_percent
