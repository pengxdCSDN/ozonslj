from backend.app.domain.listing_title_draft import generate_russian_title


def test_title_draft_reports_coverage_and_keeps_editable() -> None:
    result = generate_russian_title(
        category="Термосы",
        core_terms=["термос"],
        attribute_terms=["500 мл", "нержавеющая сталь"],
        scene_terms=["для похода"],
    )
    assert result.title == "термос 500 мл нержавеющая сталь для похода"
    assert result.character_count == len(result.title)
    assert result.editable is True
    assert result.missing_terms == ()
