from backend.app.domain.source_conflict import find_source_conflicts


def test_source_conflict_keeps_source_names_and_values() -> None:
    result = find_source_conflicts(
        {"official_private": {"price": 100}, "operator_imported": {"price": 120}},
        fields=["price"],
    )
    assert result[0].sources == ["official_private", "operator_imported"]
    assert result[0].values == ["100", "120"]
