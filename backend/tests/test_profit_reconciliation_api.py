from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.app.api.dependencies import (
    get_profit_reconciliation_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.profit_reconciliation_record import (
    ProfitReconciliationBatch,
    ProfitReconciliationRecord,
)
from backend.app.domain.store_workspace import StoreWorkspace
from backend.app.main import create_app


class StubWorkspaceGateway:
    async def get_workspace(self, workspace_id: str) -> StoreWorkspace | None:
        if workspace_id != "store-1":
            return None
        now = datetime.now(UTC)
        return StoreWorkspace(
            id="store-1",
            display_name="测试店铺",
            status="active",
            verified_at=now,
            created_at=now,
            updated_at=now,
        )


class StubReconciliationGateway:
    def __init__(self) -> None:
        self.batch = ProfitReconciliationBatch(
            id="batch-1",
            workspace_id="store-1",
            idempotency_key="run-1",
            source="finance",
            status="partial",
            created_at=datetime.now(UTC),
        )
        self.records: list[ProfitReconciliationRecord] = []

    async def create_batch(
        self, *, workspace_id: str, idempotency_key: str, source: str,
        status: str, records: list[ProfitReconciliationRecord],
    ) -> ProfitReconciliationBatch:
        del idempotency_key, source, status
        self.records = [
            item.model_copy(update={"batch_id": self.batch.id, "workspace_id": workspace_id})
            for item in records
        ]
        return self.batch

    async def list_records(
        self, *, workspace_id: str, batch_id: str | None, limit: int
    ) -> list[ProfitReconciliationRecord]:
        return [
            item for item in self.records
            if item.workspace_id == workspace_id and (batch_id is None or item.batch_id == batch_id)
        ][:limit]


def _record() -> dict[str, object]:
    return {
        "id": "record-1",
        "batch_id": "preview-batch",
        "workspace_id": "store-1",
        "order_id": "order-1",
        "sku_id": "sku-1",
        "estimated_profit_minor": 1000,
        "actual_profit_minor": 850,
        "variance_minor": -150,
        "side": "matched",
        "source": "finance",
        "created_at": "2026-08-22T00:00:00Z",
    }


def test_reconciliation_can_be_saved_and_read_back() -> None:
    app = create_app()
    gateway = StubReconciliationGateway()
    app.dependency_overrides[get_profit_reconciliation_gateway] = lambda: gateway
    app.dependency_overrides[get_store_workspace_gateway] = StubWorkspaceGateway
    client = TestClient(app)

    saved = client.post(
        "/v1/selection/profit-model/store-1/reconciliation",
        json={
            "idempotency_key": "run-1",
            "source": "finance",
            "status": "partial",
            "records": [_record()],
        },
    )
    read_back = client.get(
        "/v1/selection/profit-model/store-1/reconciliation/records?batch_id=batch-1"
    )

    assert saved.status_code == 200
    assert saved.json()["record_count"] == 1
    assert read_back.status_code == 200
    assert read_back.json()[0]["variance_minor"] == -150


def test_reconciliation_rejects_unknown_workspace() -> None:
    app = create_app()
    app.dependency_overrides[get_profit_reconciliation_gateway] = StubReconciliationGateway
    app.dependency_overrides[get_store_workspace_gateway] = StubWorkspaceGateway

    response = TestClient(app).get(
        "/v1/selection/profit-model/unknown/reconciliation/records"
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "workspace_not_found"
