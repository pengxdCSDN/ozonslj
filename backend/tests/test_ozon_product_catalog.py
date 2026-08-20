import httpx
import pytest

from backend.app.domain.store_workspace import (
    OzonAuthenticationError,
    OzonCredentials,
    OzonMalformedResponseError,
    OzonRateLimitError,
)
from backend.app.infrastructure.ozon.product_catalog import HttpOzonProductCatalogGateway


def _gateway(handler) -> HttpOzonProductCatalogGateway:
    return HttpOzonProductCatalogGateway(
        "https://api-seller.ozon.ru",
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.asyncio
async def test_catalog_reader_merges_product_attributes_and_prices() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v3/product/list":
            return httpx.Response(
                200,
                json={
                    "result": {
                        "items": [{"offer_id": "SKU-1", "product_id": "101", "name": "杯子"}],
                        "last_id": "next",
                    },
                },
            )
        if request.url.path == "/v4/product/info/attributes":
            return httpx.Response(
                200,
                json={"result": [{
                        "id": "101", "weight": 500, "depth": 200, "width": 100, "height": 80,
                    }]},
            )
        return httpx.Response(
            200,
            json={"result": {"items": [{
                "offer_id": "SKU-1", "price": "1290", "currency": "RUB", "commission": 15,
            }]}},
        )

    page = await _gateway(handler).list_skus(
        credentials=OzonCredentials("server-only", "secret"), cursor=None, limit=20
    )

    item = page.items[0]
    assert item.offer_id == "SKU-1"
    assert item.price_minor == 129000
    assert item.weight_g == 500
    assert item.length_mm == 200
    assert item.commission_rate_bps == 1500
    assert page.next_cursor == "next"


@pytest.mark.asyncio
async def test_catalog_reader_maps_auth_and_rate_limit_errors() -> None:
    async def auth_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "invalid"})

    async def limit_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"message": "slow down"})

    credentials = OzonCredentials("server-only", "secret")
    with pytest.raises(OzonAuthenticationError):
        await _gateway(auth_handler).list_skus(credentials=credentials, cursor=None, limit=20)
    with pytest.raises(OzonRateLimitError):
        await _gateway(limit_handler).list_skus(credentials=credentials, cursor=None, limit=20)


@pytest.mark.asyncio
async def test_catalog_reader_rejects_malformed_success_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": "not-an-array"})

    with pytest.raises(OzonMalformedResponseError):
        await _gateway(handler).list_skus(
            credentials=OzonCredentials("server-only", "secret"), cursor=None, limit=20
        )
