from backend.app.domain.competition_analysis import CompetitorObservation, analyze_competition


def test_competition_analysis_reports_sample_estimate_and_concentration() -> None:
    result = analyze_competition(
        [
            CompetitorObservation("seller-a", "brand-a", 1000, 4.8, 2000),
            CompetitorObservation("seller-a", "brand-a", 1200, 4.5, 1000),
            CompetitorObservation("seller-b", "brand-b", 900, 4.0, 100),
        ]
    )
    assert result.sample_count == 3
    assert result.seller_concentration_percent == 66.67
    assert result.brand_concentration_percent == 66.67
    assert result.estimated is True
    assert result.median_price_minor == 1000


def test_small_competitor_sample_is_marked_low_confidence() -> None:
    result = analyze_competition([CompetitorObservation("seller-a", None, 1000, None, 0)])
    assert "低置信度" in result.caveat
