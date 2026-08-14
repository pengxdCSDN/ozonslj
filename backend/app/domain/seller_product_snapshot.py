from typing import Protocol

from backend.app.domain.seller_product_sync import SellerProductSyncPreview


class SellerProductSnapshotGateway(Protocol):
    async def save_snapshot(
        self, *, workspace_id: str, preview: SellerProductSyncPreview
    ) -> SellerProductSyncPreview: ...

    async def list_snapshots(
        self, *, workspace_id: str, limit: int = 20
    ) -> list[SellerProductSyncPreview]: ...
