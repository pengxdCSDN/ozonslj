from backend.app.domain.smart_search import check_smart_search


def test_smart_search_rejects_empty_text_without_modifying_source() -> None:
    result = check_smart_search(" ", required_terms=["термос"], category="户外")
    assert result.valid is False
    assert result.original_text_preserved is True
    assert result.findings[0].code == "LST-EMPTY"
