import pytest

from backend.app.domain.listing_title_draft import generate_russian_title


def test_title_draft_reports_truncation_risk() -> None:
    result = generate_russian_title(
        category="Термос", core_terms=["термос"], attribute_terms=["стальной"],
        scene_terms=["для похода"], max_characters=8,
    )
    assert "标题超过长度限制" in result.risks


def test_title_draft_rejects_invalid_limit() -> None:
    with pytest.raises(ValueError):
        generate_russian_title(
            category="x", core_terms=[], attribute_terms=[], scene_terms=[], max_characters=0
        )
