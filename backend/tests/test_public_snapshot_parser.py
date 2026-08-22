from datetime import UTC, datetime

import pytest

from backend.app.domain.public_snapshot import PublicSnapshotError
from backend.app.domain.public_snapshot_parser import parse_public_snapshot_html


def test_public_snapshot_parser_keeps_allowed_metadata_only() -> None:
    snapshot = parse_public_snapshot_html(
        url="https://example.com/item",
        html=(
            "<title>  Example item </title>"
            '<meta property="og:price:amount" content="12.50">'
            '<meta property="og:price:currency" content="RUB">'
            '<meta property="product:rating" content="4.8">'
            '<meta property="product:review_count" content="17">'
            '<meta property="product:attribute:color" content="red">'
            '<script>secret="must not be persisted"</script>'
        ),
        sampled_at=datetime(2026, 8, 22, tzinfo=UTC),
    )

    assert snapshot.title == "Example item"
    assert snapshot.price_minor == 1250
    assert snapshot.currency == "RUB"
    assert str(snapshot.rating) == "4.8"
    assert snapshot.review_count == 17
    assert snapshot.attributes == {"color": "red"}


def test_public_snapshot_parser_rejects_invalid_price() -> None:
    with pytest.raises(PublicSnapshotError, match="价格"):
        parse_public_snapshot_html(
            url="https://example.com/item",
            html='<meta property="og:price:amount" content="not-a-number">',
            sampled_at=datetime(2026, 8, 22, tzinfo=UTC),
        )
