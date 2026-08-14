import httpx
import pytest

from backend.app.domain.store_workspace import (
    OzonAuthenticationError,
    OzonCredentials,
    OzonMalformedResponseError,
    OzonPermissionError,
    OzonRateLimitError,
    OzonTemporaryError,
)
from backend.app.infrastructure.ozon.account_verifier import (
    HttpOzonSellerAccountVerifier,
)

_CREDENTIALS = OzonCredentials(client_id="client-id", api_key="api-key")


def _verifier(status_code: int, payload: object) -> HttpOzonSellerAccountVerifier:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/seller/info"
        assert request.headers["Client-Id"] == "client-id"
        assert request.headers["Api-Key"] == "api-key"
        return httpx.Response(status_code, json=payload)

    return HttpOzonSellerAccountVerifier(
        "https://api-seller.ozon.ru",
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.asyncio
async def test_ozon_verifier_accepts_object_response() -> None:
    await _verifier(200, {"seller_id": 123}).verify(_CREDENTIALS)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (401, OzonAuthenticationError),
        (403, OzonPermissionError),
        (429, OzonRateLimitError),
        (500, OzonTemporaryError),
    ],
)
async def test_ozon_verifier_maps_documented_error_classes(
    status_code: int,
    expected_error: type[Exception],
) -> None:
    with pytest.raises(expected_error):
        await _verifier(status_code, {"error": "redacted"}).verify(_CREDENTIALS)


@pytest.mark.asyncio
async def test_ozon_verifier_rejects_malformed_success_response() -> None:
    with pytest.raises(OzonMalformedResponseError):
        await _verifier(200, ["unexpected"]).verify(_CREDENTIALS)


@pytest.mark.asyncio
async def test_ozon_verifier_maps_network_timeout_to_retryable_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    verifier = HttpOzonSellerAccountVerifier(
        "https://api-seller.ozon.ru",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(OzonTemporaryError):
        await verifier.verify(_CREDENTIALS)
