import pytest

from backend.app.domain.keyword_import import (
    KeywordImportError,
    keyword_import_fingerprint,
    parse_keyword_csv,
)


def test_keyword_csv_maps_rows_to_internal_model() -> None:
    rows = parse_keyword_csv("keyword,search_count,conversion_rate\nкружка,120,4.5%\n")

    assert rows[0].keyword == "кружка"
    assert rows[0].search_count == 120
    assert rows[0].source_row == 2


def test_keyword_csv_supports_external_column_mapping() -> None:
    rows = parse_keyword_csv(
        "term,volume,rate\nкружка,120,4.5%\n",
        {"term": "keyword", "volume": "search_count", "rate": "conversion_rate"},
    )

    assert rows[0].keyword == "кружка"
    assert rows[0].search_count == 120


def test_keyword_csv_deduplicates_case_insensitive_keywords_and_fingerprints_content() -> None:
    rows = parse_keyword_csv("keyword,search_count,conversion_rate\nCup,1,1%\ncup,2,2%\n")

    assert len(rows) == 1
    assert keyword_import_fingerprint("a") == keyword_import_fingerprint("a")


def test_keyword_csv_rejects_conversion_rate_outside_percentage_range() -> None:
    with pytest.raises(KeywordImportError, match="conversion_rate"):
        parse_keyword_csv("keyword,search_count,conversion_rate\nCup,1,101%\n")


@pytest.mark.parametrize(
    "content",
    [
        "keyword,search_count\nкружка,1\n",
        "keyword,search_count,conversion_rate\n,1,2%\n",
        "keyword,search_count,conversion_rate\nкружка,-1,2%\n",
    ],
)
def test_keyword_csv_rejects_invalid_rows(content: str) -> None:
    with pytest.raises(KeywordImportError):
        parse_keyword_csv(content)
