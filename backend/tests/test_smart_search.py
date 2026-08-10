from backend.app.domain.smart_search import check_smart_search


def test_smart_search_reports_coverage_repeat_and_preserves_original() -> None:
    result = check_smart_search(
        "термос термос термос сталь",
        required_terms=["термос", "500 мл"],
        category="Термосы",
        category_terms=["термос"],
    )
    assert "500 мл" in result.missing_terms
    assert any(item.code == "LST-REPEAT" for item in result.findings)
    assert result.original_text_preserved is True
