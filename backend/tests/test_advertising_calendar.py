from datetime import date

from backend.app.domain.advertising_calendar import build_advertising_calendar


def test_calendar_contains_four_phases_and_is_read_only() -> None:
    result = build_advertising_calendar(date(2026, 8, 10))
    assert len(result) == 30
    assert [result[index].phase for index in (0, 7, 14, 21, 29)] == [
        "testing", "filtering", "scaling", "optimizing", "optimizing"
    ]
    assert all(item.read_only for item in result)
