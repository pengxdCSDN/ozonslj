import pytest

from backend.app.domain.search_attributes import build_search_attributes


def test_search_attributes_rejects_empty_required_name() -> None:
    with pytest.raises(ValueError):
        build_search_attributes({"": "red"}, {})


def test_search_attributes_reports_missing_coverage() -> None:
    report = build_search_attributes({"color": "red", "size": "500"}, {"color": "red"})
    assert report.coverage_percent == 50.0
    assert report.missing_required == ("size",)
