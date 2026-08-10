from typing import Protocol

from backend.app.domain.seller_order_sync import SellerOrderSyncPreview


class SellerOrderSnapshotGateway(Protocol):
    async def save_snapshot(
        self, *, workspace_id: str, preview: SellerOrderSyncPreview
    ) -> SellerOrderSyncPreview: ...

    async def list_snapshots(
        self, *, workspace_id: str, limit: int = 20
    ) -> list[SellerOrderSyncPreview]: ...
