from backend.app.domain.listing_version import create_listing_version


def test_listing_version_preserves_original_and_generates_diff() -> None:
    result = create_listing_version(
        version=2,
        original_text="标题\n500 мл",
        edited_text="标题\n500 мл для похода",
        status="review",
    )
    assert result.version == 2
    assert result.original_text == "标题\n500 мл"
    assert result.status == "review"
    assert any("+500 мл для похода" in line for line in result.diff)
