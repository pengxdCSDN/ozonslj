import pytest

from backend.app.domain.competitor_seed import CompetitorSeedError, validate_competitor_seed_url


def test_competitor_seed_accepts_public_https_and_normalizes_query() -> None:
    assert validate_competitor_seed_url("https://www.ozon.ru/product/item?utm=1") == "https://www.ozon.ru/product/item"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/item",
        "javascript:alert(1)",
        "https://user:pass@example.com/item",
        "https://example.com/item#reviews",
    ],
)
def test_competitor_seed_rejects_unsafe_url(url: str) -> None:
    with pytest.raises(CompetitorSeedError):
        validate_competitor_seed_url(url)
