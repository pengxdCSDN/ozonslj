from decimal import Decimal

from backend.app.infrastructure.postgres.product_offers import _minor_to_decimal


def test_minor_amount_keeps_two_decimal_places() -> None:
    assert _minor_to_decimal(129000) == Decimal("1290.00")
    assert str(_minor_to_decimal(129000)) == "1290.00"
