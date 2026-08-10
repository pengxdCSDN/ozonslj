from datetime import UTC, datetime

import pytest

from backend.app.domain.listing_keyword import (
    ListingKeyword,
    ListingKeywordError,
    normalize_listing_keyword,
)


def test_listing_keyword_normalizes_and_preserves_provenance() -> None:
    result = normalize_listing_keyword(
        ListingKeyword(
            "  термос   стальной ", "operator_imported", datetime.now(UTC), "RU", "core", "SKU-1"
        )
    )
    assert result.keyword == "термос стальной"
    assert result.language == "ru"
    assert result.source == "operator_imported"


def test_listing_keyword_requires_content() -> None:
    with pytest.raises(ListingKeywordError):
        normalize_listing_keyword(
            ListingKeyword(" ", "import", datetime.now(UTC), "ru", "core", "SKU-1")
        )
