from dataclasses import dataclass
from difflib import unified_diff
from typing import Literal, Protocol

ListingVersionStatus = Literal["draft", "review", "approved", "rejected"]


@dataclass(frozen=True, slots=True)
class ListingVersion:
    version: int
    original_text: str
    edited_text: str
    status: ListingVersionStatus
    diff: tuple[str, ...]


class ListingVersionGateway(Protocol):
    async def save_version(
        self, *, workspace_id: str, product_scope: str, version: ListingVersion
    ) -> ListingVersion: ...

    async def list_versions(
        self, *, workspace_id: str, product_scope: str, limit: int
    ) -> list[ListingVersion]: ...


def create_listing_version(
    *,
    version: int,
    original_text: str,
    edited_text: str,
    status: ListingVersionStatus = "draft",
) -> ListingVersion:
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
