"""说明本模块的职责、边界和主要协作对象。"""

from typing import Protocol

from backend.app.domain.seller_stock_sync import SellerStockSyncPreview


class SellerStockSnapshotGateway(Protocol):
    """说明 SellerStockSnapshotGateway 的职责、状态边界和对外协作关系。"""
    async def save_snapshot(
        self, *, workspace_id: str, preview: SellerStockSyncPreview
    ) -> SellerStockSyncPreview:
        """执行 save_snapshot 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    preview: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_snapshots(
        self, *, workspace_id: str, limit: int = 20
    ) -> list[SellerStockSyncPreview]:
        """执行 list_snapshots 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
