from typing import Protocol

from backend.app.domain.seller_stock_sync import SellerStockSyncPreview


class SellerStockSnapshotGateway(Protocol):
    async def save_snapshot(
        self, *, workspace_id: str, preview: SellerStockSyncPreview
    ) -> SellerStockSyncPreview: ...

    async def list_snapshots(
        self, *, workspace_id: str, limit: int = 20
    ) -> list[SellerStockSyncPreview]: ...
