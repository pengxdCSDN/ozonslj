"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class PublicSnapshot:
    """说明 PublicSnapshot 的职责、状态边界和对外协作关系。"""
    url: str
    sampled_at: datetime
    title: str | None
    price_minor: int | None
    currency: str | None
    rating: Decimal | None
    review_count: int | None
    image_url: str | None
    attributes: dict[str, str]
    sample_size: int
    estimated: bool = True


class PublicSnapshotGateway(Protocol):
    """说明 PublicSnapshotGateway 的职责、状态边界和对外协作关系。"""
    async def save_snapshot(
        self, *, workspace_id: str, snapshot: PublicSnapshot
    ) -> PublicSnapshot:
        """执行 save_snapshot 的业务流程并返回该流程的结果。"""

    async def list_snapshots(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[PublicSnapshot]:
        """执行 list_snapshots 的业务流程并返回该流程的结果。"""


class PublicSnapshotError(ValueError):
    """公开页面字段无法满足快照边界时抛出。"""


def normalize_public_snapshot(raw: dict[str, object], *, sampled_at: datetime) -> PublicSnapshot:
    """只保留公开字段，并把金额、评分和评价数转换为可审计类型。"""
    url = _optional_text(raw.get("url"))
    parsed = urlparse(url or "")
    if parsed.scheme != "https" or not parsed.hostname:
        raise PublicSnapshotError("公开快照 URL 必须是 HTTPS")
    price_minor = _integer(raw.get("price_minor"), "price_minor")
    review_count = _integer(raw.get("review_count"), "review_count")
    if review_count is not None and review_count < 0:
        raise PublicSnapshotError("评价数不能为负数")
    rating = _decimal(raw.get("rating"), "rating")
    if rating is not None and not 0 <= rating <= 5:
        raise PublicSnapshotError("评分必须在 0 到 5 之间")
    currency = _optional_text(raw.get("currency"))
    if currency is not None and (len(currency) != 3 or not currency.isupper()):
        raise PublicSnapshotError("币种必须是三位大写代码")
    raw_sample_size = _integer(raw.get("sample_size"), "sample_size")
    if raw_sample_size is not None and raw_sample_size < 1:
        raise PublicSnapshotError("样本数量必须为正数")
    attributes = raw.get("attributes", {})
    if not isinstance(attributes, dict):
        raise PublicSnapshotError("公开属性必须是对象")
    return PublicSnapshot(
        url=url or "",
        sampled_at=sampled_at,
        title=_optional_text(raw.get("title")),
        price_minor=price_minor,
        currency=currency,
        rating=rating,
        review_count=review_count,
        image_url=_optional_text(raw.get("image_url")),
        attributes={str(key): str(value) for key, value in attributes.items()},
        sample_size=raw_sample_size or 1,
    )


def _integer(value: object, field: str) -> int | None:
    """执行内部步骤 _integer，供同一模块的公开流程复用。"""
    if value is None or value == "":
        return None
    if not isinstance(value, (int, str)):
        raise PublicSnapshotError(f"{field} 必须是整数")
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise PublicSnapshotError(f"{field} 必须是整数") from error
    if field == "price_minor" and result < 0:
        raise PublicSnapshotError("价格不能为负数")
    return result


def _decimal(value: object, field: str) -> Decimal | None:
    """执行内部步骤 _decimal，供同一模块的公开流程复用。"""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation as error:
        raise PublicSnapshotError(f"{field} 必须是数字") from error


def _optional_text(value: object) -> str | None:
    """执行内部步骤 _optional_text，供同一模块的公开流程复用。"""
    return str(value).strip() or None if value is not None else None
