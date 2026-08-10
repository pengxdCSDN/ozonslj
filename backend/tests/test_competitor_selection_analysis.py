from backend.app.domain.competitor_selection_analysis import analyze_competitor_selection


def test_competitor_selection_analysis_preserves_estimation_boundary() -> None:
    result = analyze_competitor_selection(
        sample_count=5, opportunity_count=2, median_price_minor=2500,
        top_competitor_rating=4.8, source_window="2026-08",
    )
    assert result.estimated is True
    assert "全市场" in result.caveat
    assert result.read_only is True
