from backend.app.domain.listing_layering import classify_listing_keywords


def test_listing_layering_prefers_manual_terms_and_long_tail_rule() -> None:
    result = classify_listing_keywords(
        ["термос", "500 мл", "для похода термос стальной вакуумный", "термос"],
        core_terms={"термос"},
        attribute_terms={"500 мл"},
    )
    assert [(item.keyword, item.layer) for item in result] == [
        ("термос", "core"),
        ("500 мл", "attribute"),
        ("для похода термос стальной вакуумный", "long_tail"),
    ]
    assert result[0].manually_confirmed is True
