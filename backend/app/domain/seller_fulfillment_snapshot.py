from typing import Protocol

from backend.app.domain.seller_fulfillment_sync import SellerFulfillmentSyncPreview


class SellerFulfillmentSnapshotGateway(Protocol):
    async def save_snapshot(
        self, *, workspace_id: str, preview: SellerFulfillmentSyncPreview
    ) -> SellerFulfillmentSyncPreview: ...

    async def list_snapshots(
        self, *, workspace_id: str, limit: int = 20
    ) -> list[SellerFulfillmentSyncPreview]: ...
