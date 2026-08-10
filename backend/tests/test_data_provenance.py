import pytest

from backend.app.domain.data_provenance import classify_source


def test_provenance_preserves_official_source() -> None:
    result = classify_source(
        source="official_private",
        observed_at="2026-08-09T00:00:00Z",
        explanation="Seller API 商品事实",
    )
    assert result.source == "official_private"


def test_provenance_rejects_unknown_source() -> None:
    with pytest.raises(ValueError):
        classify_source(source="unknown", observed_at="now", explanation="不明")
