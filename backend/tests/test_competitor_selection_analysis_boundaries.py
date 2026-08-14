import pytest

from backend.app.domain.competitor_selection_analysis import analyze_competitor_selection


def test_competitor_selection_rejects_boolean_counts_and_rating() -> None:
    with pytest.raises(ValueError):
        analyze_competitor_selection(
            sample_count=True, opportunity_count=0, median_price_minor=None,
            top_competitor_rating=None, source_window="2026-08",
        )
    with pytest.raises(ValueError):
        analyze_competitor_selection(
            sample_count=1, opportunity_count=0, median_price_minor=None,
            top_competitor_rating=True, source_window="2026-08",
        )
