from backend.app.domain.selection_explore import (
    ExploreFilters,
    ExploreInput,
    explore_opportunities,
    filter_opportunities,
)


def test_explore_fuses_sources_and_marks_estimate() -> None:
    results = explore_opportunities(
        [
            ExploreInput("термос", 1000, 12, 5, 199900, 0, 0),
            ExploreInput("чехол", 500, 5, 0, 0, 10, 4),
        ]
    )
    assert results[0].keyword == "термос"
    assert results[0].estimated is True
    assert results[0].own_coverage_gap is True
    assert "公开样本" in results[0].reasons[1]


def test_explore_filters_keep_score_and_only_select_coverage_gaps() -> None:
    results = explore_opportunities([
        ExploreInput("термос", 1000, 12, 5, 199900, 0, 0),
        ExploreInput("чехол", 500, 5, 0, 89900, 10, 4),
    ])
    filtered = filter_opportunities(
        results, ExploreFilters(min_score=50, min_search_count=900, coverage_gap_only=True)
    )
    assert [item.keyword for item in filtered] == ["термос"]
    assert filtered[0].score == results[0].score
