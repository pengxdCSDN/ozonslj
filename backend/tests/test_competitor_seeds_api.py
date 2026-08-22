from dataclasses import replace
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.app.api.dependencies import (
    get_competitor_seed_gateway,
    get_public_snapshot_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.competitor_seed import CompetitorSeed
from backend.app.domain.store_workspace import StoreWorkspace
from backend.app.main import create_app


class StubWorkspaceGateway:
    async def get_workspace(self, workspace_id: str) -> StoreWorkspace | None:
        if workspace_id != "store-1":
            return None
        now = datetime.now(UTC)
        return StoreWorkspace(
            id=workspace_id,
            display_name="测试店铺",
            status="active",
            verified_at=now,
            created_at=now,
            updated_at=now,
        )


class StubSeedGateway:
    def __init__(self) -> None:
        self.seed = CompetitorSeed(
            id="seed-1",
            workspace_id="store-1",
            url="https://example.com/product/1",
            title=None,
            status="active",
        )
        self.extra_seeds: list[CompetitorSeed] = []

    async def create_seed(self, *, workspace_id: str, url: str) -> CompetitorSeed:
        self.seed = CompetitorSeed(
            id="seed-1",
            workspace_id=workspace_id,
            url=url,
            title=None,
            status="active",
        )
        return self.seed

    async def list_seeds(self, *, workspace_id: str) -> list[CompetitorSeed]:
        return ([self.seed] + self.extra_seeds) if self.seed.workspace_id == workspace_id else []

    async def update_status(self, *, seed_id: str, status: str) -> CompetitorSeed | None:
        if seed_id != self.seed.id:
            return None
        self.seed = replace(self.seed, status=status)
        return self.seed


class StubSnapshotGateway:
    async def save_snapshot(self, *, workspace_id: str, snapshot: object) -> object:
        del workspace_id
        return snapshot

    async def list_snapshots(self, *, workspace_id: str, limit: int = 50) -> list[object]:
        del workspace_id, limit
        return []


def test_competitor_seed_create_list_and_update_status() -> None:
    app = create_app()
    seeds = StubSeedGateway()
    app.dependency_overrides[get_store_workspace_gateway] = StubWorkspaceGateway
    app.dependency_overrides[get_competitor_seed_gateway] = lambda: seeds
    client = TestClient(app)

    created = client.post(
        "/v1/store-workspaces/store-1/competitor-seeds",
        json={"url": "https://example.com/product/1?utm_source=test"},
    )
    assert created.status_code == 201
    assert created.json()["url"] == "https://example.com/product/1"

    listed = client.get("/v1/store-workspaces/store-1/competitor-seeds")
    assert listed.status_code == 200
    assert listed.json()[0]["status"] == "active"

    updated = client.patch(
        "/v1/store-workspaces/store-1/competitor-seeds/seed-1",
        json={"status": "paused"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "paused"


def test_competitor_seed_rejects_non_https_url() -> None:
    app = create_app()
    app.dependency_overrides[get_store_workspace_gateway] = StubWorkspaceGateway
    app.dependency_overrides[get_competitor_seed_gateway] = StubSeedGateway
    response = TestClient(app).post(
        "/v1/store-workspaces/store-1/competitor-seeds",
        json={"url": "http://example.com/product/1"},
    )
    assert response.status_code == 422


def test_competitor_seed_limit_is_enforced() -> None:
    app = create_app()
    seeds = StubSeedGateway()
    seeds.extra_seeds = [
        CompetitorSeed(str(index), "store-1", f"https://example.com/{index}", None, "active")
        for index in range(49)
    ]
    app.dependency_overrides[get_competitor_seed_gateway] = lambda: seeds
    app.dependency_overrides[get_store_workspace_gateway] = StubWorkspaceGateway

    response = TestClient(app).post(
        "/v1/store-workspaces/store-1/competitor-seeds",
        json={"url": "https://example.com/new"},
    )

    assert response.status_code == 409


def test_competitor_seed_collect_requires_sampling_configuration() -> None:
    app = create_app()
    app.dependency_overrides[get_competitor_seed_gateway] = StubSeedGateway
    app.dependency_overrides[get_store_workspace_gateway] = StubWorkspaceGateway
    app.dependency_overrides[get_public_snapshot_gateway] = StubSnapshotGateway

    response = TestClient(app).post(
        "/v1/store-workspaces/store-1/competitor-seeds/seed-1/collect",
        json={},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "sampling_not_configured"
