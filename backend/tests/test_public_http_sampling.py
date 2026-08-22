import asyncio

import httpx

from backend.app.domain.public_sampling import PublicSampler, SamplingRequest
from backend.app.infrastructure.public_sampling import PublicHttpFetcher


def test_http_fetcher_checks_robots_before_page_request() -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
        return httpx.Response(200)

    async def run() -> tuple[bool, list[str]]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            fetcher = PublicHttpFetcher(client, allowed_hosts={"example.com"})
            result = await PublicSampler(fetcher.fetch_page).sample(
                [SamplingRequest("https://example.com/private")]
            )
            return result[0].allowed, requested

    allowed, urls = asyncio.run(run())
    assert allowed is False
    assert urls == ["https://example.com/robots.txt"]


def test_http_fetcher_allows_whitelisted_page_after_robots_check() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:\n")
        return httpx.Response(200)

    async def run() -> int | None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            fetcher = PublicHttpFetcher(client, allowed_hosts={"example.com"})
            result = await PublicSampler(fetcher.fetch_page).sample(
                [SamplingRequest("https://example.com/item")]
            )
            return result[0].status_code

    assert asyncio.run(run()) == 200


def test_http_fetcher_blocks_non_whitelisted_host_without_request() -> None:
    requested = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requested
        requested = True
        return httpx.Response(200)

    async def run() -> bool:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            fetcher = PublicHttpFetcher(client, allowed_hosts={"example.com"})
            result = await PublicSampler(fetcher.fetch_page).sample(
                [SamplingRequest("https://other.example/item")]
            )
            return result[0].allowed

    assert asyncio.run(run()) is False
    assert requested is False
