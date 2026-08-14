from backend.app.domain.readback_verification import verify_readback


def test_readback_detects_field_difference() -> None:
    result = verify_readback(expected={"price": 100}, actual={"price": 110})
    assert result.matched is False
    assert result.fields[0].matched is False
    assert result.message == "回读核对发现差异"
