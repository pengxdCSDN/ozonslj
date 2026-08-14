from datetime import UTC, datetime, timedelta

import pytest

from backend.app.domain.diff_preview import StalePreviewError, build_diff_preview


def test_diff_preview_contains_changed_fields_and_review_gate() -> None:
    result = build_diff_preview(
        old_values={"price": "2500", "title": "旧标题"},
        new_values={"price": "2700", "title": "新标题"},
        source="人工编辑",
        impact="影响商品展示与售价",
    )
    assert len(result) == 2
    assert result[0].requires_review is True
    assert result[0].source == "人工编辑"


def test_diff_preview_rejects_stale_data_before_review() -> None:
    now = datetime(2026, 8, 9, tzinfo=UTC)
    with pytest.raises(StalePreviewError, match="过期"):
        build_diff_preview(
            old_values={"price": "2500"}, new_values={"price": "2700"},
            source="人工编辑", impact="影响售价",
            observed_at=now - timedelta(minutes=11), max_age_seconds=600, now=now,
        )


def test_diff_preview_requires_complete_freshness_metadata() -> None:
    with pytest.raises(ValueError, match="同时提供"):
        build_diff_preview(
            old_values={"price": "2500"}, new_values={"price": "2700"},
            source="人工编辑", impact="影响售价", max_age_seconds=600,
        )
