from backend.app.domain.selection_expand import ExpandInput, expand_product


def test_expand_deduplicates_layers_and_builds_variants() -> None:
    result = expand_product(
        ExpandInput(
            "термос",
            ("термос", "термос стальной"),
            ("Термос",),
            ("500 мл",),
            ("поход",),
            (),
        )
    )
    assert result.core_terms == ("термос", "термос стальной")
    assert result.attribute_terms == ("500 мл",)
    assert result.scene_terms == ("поход",)
    assert result.variant_candidates == ("термос 500 мл",)
    assert result.estimated is True
