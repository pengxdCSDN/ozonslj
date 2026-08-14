from backend.app.domain.data_quality_schema import check_required_and_enums


def test_quality_schema_finds_missing_and_unknown_enum() -> None:
    result = check_required_and_enums(
        [{"sku": "SKU-1", "status": "unknown"}, {"status": "active"}],
        required_fields=["sku"], enum_fields={"status": ["active", "paused"]},
    )
    assert result.valid is False
    assert len(result.findings) == 2
    assert result.isolated_required is True
