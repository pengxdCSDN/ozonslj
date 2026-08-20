"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from difflib import unified_diff
from typing import Literal, Protocol

ListingVersionStatus = Literal["draft", "review", "approved", "rejected"]


@dataclass(frozen=True, slots=True)
class ListingVersion:
    """说明 ListingVersion 的职责、状态边界和对外协作关系。"""
    version: int
    original_text: str
    edited_text: str
    status: ListingVersionStatus
    diff: tuple[str, ...]


class ListingVersionGateway(Protocol):
    """说明 ListingVersionGateway 的职责、状态边界和对外协作关系。"""
    async def save_version(
        self, *, workspace_id: str, product_scope: str, version: ListingVersion
    ) -> ListingVersion:
        """执行 save_version 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    product_scope: 参数语义、输入边界和安全约束。
    version: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_versions(
        self, *, workspace_id: str, product_scope: str, limit: int
    ) -> list[ListingVersion]:
        """执行 list_versions 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    product_scope: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


def create_listing_version(
    *,
    version: int,
    original_text: str,
    edited_text: str,
    status: ListingVersionStatus = "draft",
) -> ListingVersion:
    """执行 create_listing_version 的业务流程并返回该流程的结果。

Args:
    version: 参数语义、输入边界和安全约束。
    original_text: 参数语义、输入边界和安全约束。
    edited_text: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    if version < 1:
        raise ValueError("版本号必须从 1 开始")
    if not original_text.strip():
        raise ValueError("原始 Listing 文本不能为空")
    if not edited_text.strip():
        raise ValueError("修改后的 Listing 文本不能为空")
    diff = tuple(
        unified_diff(
            original_text.splitlines(), edited_text.splitlines(),
            fromfile="original", tofile=f"version-{version}", lineterm="",
        )
    )
    return ListingVersion(version, original_text, edited_text, status, diff)
