import asyncio

from backend.app.application.public_sampling_collector import PublicSamplingCollector
from backend.app.domain.public_sampling import FetchResponse
from backend.app.domain.public_snapshot import PublicSnapshot


class StubSnapshots:
    def __init__(self) -> None:
        self.saved: list[PublicSnapshot] = []

    async def save_snapshot(self, *, workspace_id: str, snapshot: PublicSnapshot) -> PublicSnapshot:
        del workspace_id
        self.saved.append(snapshot)
        return snapshot

    async def list_snapshots(self, *, workspace_id: str, limit: int = 50) -> list[PublicSnapshot]:
        del workspace_id, limit
        return self.saved


class StubEventPublisher:
    def __init__(self) -> None:
        self.events: list[object] = []

    async def publish_once(self, event: object) -> bool:
        self.events.append(event)
        return True


def test_collector_saves_only_successfully_parsed_public_snapshot() -> None:
    async def fetch(url: str) -> FetchResponse:
        if url.endswith("/blocked"):
            return FetchResponse(403, False, "robots 策略禁止访问")
        return FetchResponse(
            200,
            True,
            "请求完成",
            '<title>Item</title><meta property="og:price:amount" content="10">'
            '<meta property="og:price:currency" content="RUB">',
        )

    snapshots = StubSnapshots()
    events = StubEventPublisher()
    results, saved = asyncio.run(
        PublicSamplingCollector(snapshots, fetch, events).collect(
            workspace_id="store-1",
            urls=["https://example.com/item", "https://example.com/blocked"],
            global_limit=2,
            max_attempts=1,
        )
    )

    assert results[0].allowed is True
    assert results[1].allowed is False
    assert len(saved) == 1
    assert saved[0].price_minor == 1000
    assert len(events.events) == 1
