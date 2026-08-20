from datetime import date

import httpx
import pytest

from backend.app.domain.ozon_finance_accrual import validate_finance_range
from backend.app.domain.store_workspace import OzonCredentials
from backend.app.infrastructure.ozon.finance_accrual import HttpOzonFinanceAccrualGateway


def _gateway(handler) -> HttpOzonFinanceAccrualGateway:
    return HttpOzonFinanceAccrualGateway(
        "https://api-seller.ozon.ru", transport=httpx.MockTransport(handler)
    )


@pytest.mark.asyncio
async def test_finance_accrual_reader_paginates_and_normalizes_lines() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                200,
                json={
                    "accruals": [
                        {
                            "type_id": 7,
                            "posting": {
                                "posting_number": "POST-1",
                                "products": [
                                    {
                                        "sku": 123,
                                        "commission": {
                                            "seller_price": "1290.00",
                                            "sale_commission": "-193.50",
                                        },
                                        "delivery": {"services": [{"accrued": "-50.00"}]},
                                    }
                                ],
                            },
                        }
                    ],
                    "last_id": "next",
                },
            )
        return httpx.Response(200, json={"accruals": [], "last_id": ""})

    page = await _gateway(handler).list_accruals(
        credentials=OzonCredentials("server-only", "secret"),
        date_from=date(2026, 8, 1),
        date_to=date(2026, 8, 1),
    )

    assert calls == 2
    assert [line.category for line in page.lines] == ["sale", "commission", "logistics"]
    assert page.lines[0].amount_minor == 129000
    assert page.lines[1].amount_minor == -19350


def test_finance_range_is_limited_to_31_days() -> None:
    with pytest.raises(ValueError, match="31"):
        validate_finance_range(date(2026, 1, 1), date(2026, 2, 1))
