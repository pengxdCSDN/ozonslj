"""说明本模块的职责、边界和主要协作对象。"""

from typing import Protocol

from backend.app.domain.seller_product_sync import SellerProductSyncPreview


class SellerProductSnapshotGateway(Protocol):
    """说明 SellerProductSnapshotGateway 的职责、状态边界和对外协作关系。"""
    async def save_snapshot(
        self, *, workspace_id: str, preview: SellerProductSyncPreview
    ) -> SellerProductSyncPreview:
        """执行 save_snapshot 的业务流程并返回该流程的结果。"""

    async def list_snapshots(
        self, *, workspace_id: str, limit: int = 20
    ) -> list[SellerProductSyncPreview]:
        """执行 list_snapshots 的业务流程并返回该流程的结果。"""
