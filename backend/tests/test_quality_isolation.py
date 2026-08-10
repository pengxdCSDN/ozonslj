from backend.app.domain.quality_isolation import isolate_invalid_records


def test_invalid_records_are_removed_from_accepted_set() -> None:
    result = isolate_invalid_records([{"id": "1"}, {"id": "2"}], {2}, reason="负库存")
    assert result.accepted == [{"id": "1"}]
    assert result.isolated[0].record == {"id": "2"}
