"""Ozon 商品目录的领域标准模型，不暴露 Seller API 传输结构。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProductSkuFact:
    """保存一个可参与利润测算的店铺 SKU 官方事实。"""

    offer_id: str
    ozon_product_id: str
    product_group_id: str | None
    name: str
    category_id: str | None
    price_minor: int | None
    currency: str | None
    weight_g: int | None
    length_mm: int | None
    width_mm: int | None
    height_mm: int | None
    commission_rate_bps: int | None
    source: str = "official_private"


@dataclass(frozen=True, slots=True)
class ProductCatalogPage:
    """表示一次商品目录读取结果及可继续读取的官方游标。"""

    items: tuple[ProductSkuFact, ...]
    next_cursor: str | None
    source: str = "seller_api"


class OzonProductCatalogGateway(Protocol):
    """定义后端读取 Ozon 商品、规格和价格佣金的只读端口。"""

    async def list_skus(
        self,
        *,
        credentials: object,
        cursor: str | None,
        limit: int,
    ) -> ProductCatalogPage:
        """读取一页 SKU 官方事实，不执行任何外部写入。

        Args:
            credentials: 仅由后端注入的 Ozon 凭据对象；不得来自扩展请求体。
            cursor: Seller API 返回的分页游标；首次读取传入 None。
            limit: 本次最多读取的 SKU 数量，必须由调用方限制范围。

        Returns:
            包含商品组、规格、价格和可用佣金字段的标准化页面。

        Raises:
            ValueError: 分页参数或上游响应违反标准化契约时抛出。
            RuntimeError: Ozon 网络、认证、限流或服务异常已转换为稳定错误时抛出。
        """
