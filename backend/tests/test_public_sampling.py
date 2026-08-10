import asyncio

from backend.app.domain.public_sampling import PublicSampler, SamplingRequest


def test_sampler_blocks_policy_denied_request_without_fetching() -> None:
    called = False

    async def fetch(url: str) -> int:
        nonlocal called
        called = True
        return 200

    result = asyncio.run(
        PublicSampler(fetch).sample(
            [SamplingRequest("http://example.com", robots_allowed=True)]
        )
    )
    assert result[0].allowed is False
    assert result[0].attempts == 0
    assert called is False


def test_sampler_retries_429_and_keeps_results() -> None:
    statuses = iter([429, 503, 200])

    async def fetch(url: str) -> int:
        del url
        return next(statuses)

    result = asyncio.run(PublicSampler(fetch).sample([SamplingRequest("https://example.com/item")]))
    assert result[0].allowed is True
    assert result[0].attempts == 3
    assert result[0].status_code == 200


def test_sampler_accepts_retry_after_metadata() -> None:
    calls = 0

    async def fetch(url: str) -> tuple[int, float]:
        nonlocal calls
        del url
        calls += 1
        return (429, 0.0) if calls == 1 else (200, 0.0)

    result = asyncio.run(
        PublicSampler(fetch, max_attempts=2).sample([SamplingRequest("https://example.com/item")])
    )
    assert result[0].attempts == 2
