from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

SellerAccountStatus = Literal["pending", "active", "invalid", "disabled"]


class WorkspaceNotFoundError(LookupError):
    """请求的店铺工作区不存在。"""


class StoreWorkspace(BaseModel):
    """扩展端可见的工作区摘要，不包含卖家凭据或其密文。"""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    seller_display_name: str = Field(min_length=1)
    seller_status: SellerAccountStatus


class StoreWorkspaceList(BaseModel):
    items: list[StoreWorkspace]


class StoreWorkspaceGateway(Protocol):
    """读取运营用户可见工作区的领域端口。"""

    async def list_store_workspaces(
        self, workspace_ids: tuple[str, ...]
    ) -> list[StoreWorkspace]: ...
