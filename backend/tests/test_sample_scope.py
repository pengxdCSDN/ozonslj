from datetime import UTC, datetime, timedelta

from backend.app.domain.sample_scope import summarize_sample_scope


def test_sample_scope_reports_count_window_and_missing_fields() -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    scope = summarize_sample_scope(
        [
            {"sampled_at": start, "title": "A", "price_minor": 100},
            {"sampled_at": start + timedelta(hours=1), "title": "B", "rating": "4.5"},
        ]
    )
    assert scope.sample_count == 2
    assert scope.sampled_from == start
    assert scope.sampled_to == start + timedelta(hours=1)
    assert "review_count" in scope.missing_fields
    assert scope.estimated is True
