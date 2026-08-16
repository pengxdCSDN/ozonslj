import pytest

from backend.app.domain.advertising_budget import analyze_advertising_budget


def test_budget_analysis_projects_overrun_without_writing() -> None:
    result = analyze_advertising_budget(
        budget_minor=10000, spend_minor=6000, days_elapsed=5, days_total=10
    )
    assert result.status == "at_risk"
    assert result.projected_spend_minor == 12000
    assert result.read_only is True


def test_budget_analysis_rejects_invalid_period() -> None:
    with pytest.raises(ValueError, match="已用天数"):
        analyze_advertising_budget(
            budget_minor=10000, spend_minor=100, days_elapsed=11, days_total=10
        )
