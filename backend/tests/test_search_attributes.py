from backend.app.domain.search_attributes import build_search_attributes


def test_search_attributes_reports_coverage_and_missing_fields() -> None:
    result = build_search_attributes(
        {"volume": "", "material": "", "color": ""},
        {"volume": "500 мл"},
        {"material": "нержавеющая сталь"},
    )
    assert result.coverage_percent == 66.67
    assert result.missing_required == ("color",)
    assert result.suggestions[1].source_term == "material"
