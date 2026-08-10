import pytest

from backend.app.domain.listing_version import create_listing_version


def test_listing_version_preserves_original_and_diff() -> None:
    result = create_listing_version(
        version=1, original_text="原文", edited_text="修改后", status="review"
    )
    assert result.original_text == "原文"
    assert result.diff


def test_listing_version_rejects_empty_original() -> None:
    with pytest.raises(ValueError):
        create_listing_version(version=1, original_text=" ", edited_text="修改")
