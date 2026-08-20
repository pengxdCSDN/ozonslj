"""解析和校验物流模板 CSV，生成可追溯的版本化 FBS 规则。"""

import csv
import io
from dataclasses import dataclass

from backend.app.domain.sku_profit import (
    FbsLogisticsTemplate,
    LogisticsBand,
    RateTrace,
)


class LogisticsTemplateImportError(ValueError):
    """表示模板 CSV 缺列、格式错误或业务规则不完整。"""


@dataclass(frozen=True, slots=True)
class LogisticsTemplateImportPreview:
    """保存 CSV 预览结果，提交前只返回摘要和标准化模板，不写入数据库。"""

    templates: tuple[FbsLogisticsTemplate, ...]
    row_count: int
    errors: tuple[str, ...]


_REQUIRED_COLUMNS = frozenset(
    {
        "template_id",
        "fulfillment_type",
        "warehouse_id",
        "route_id",
        "region_id",
        "version",
        "effective_from",
        "max_weight_g",
        "base_fee_minor",
        "currency",
        "source",
        "volumetric_divisor_cm3_per_kg",
    }
)


def preview_logistics_template_csv(content: str) -> LogisticsTemplateImportPreview:
    """预览物流模板 CSV 并按模板、上下文和重量上限聚合规则。

    Args:
        content: UTF-8 CSV 文本；不得包含凭据或客户个人数据。

    Returns:
        包含标准化模板、行数和所有可操作错误的预览对象。

    Raises:
        LogisticsTemplateImportError: CSV 为空、缺少表头或无法解析时抛出。
    """
    if not content.strip():
        raise LogisticsTemplateImportError("物流模板 CSV 不能为空")
    reader = csv.DictReader(io.StringIO(content))
    columns = frozenset(reader.fieldnames or ())
    missing = sorted(_REQUIRED_COLUMNS - columns)
    if missing:
        raise LogisticsTemplateImportError(f"CSV 缺少必需列：{', '.join(missing)}")
    grouped: dict[str, list[LogisticsBand]] = {}
    metadata: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    row_count = 0
    for row_number, row in enumerate(reader, start=2):
        row_count += 1
        try:
            template_id = _text(row, "template_id")
            max_weight = _positive_int(row, "max_weight_g")
            band = LogisticsBand(
                max_chargeable_weight_g=max_weight,
                fee_minor=_nonnegative_int(row, "base_fee_minor"),
                additional_fee_minor=_nonnegative_int(row, "additional_fee_minor"),
                additional_step_g=_nonnegative_int(row, "additional_step_g"),
                fee_rate_bps=_nonnegative_int(row, "fee_rate_bps"),
            )
            if template_id not in metadata:
                metadata[template_id] = {
                    key: _text(row, key)
                    for key in (
                        "fulfillment_type", "warehouse_id", "route_id", "region_id",
                        "version", "effective_from", "currency", "source",
                    )
                }
                metadata[template_id]["effective_to"] = _optional_text(row, "effective_to")
                metadata[template_id]["volumetric_divisor"] = _text(
                    row, "volumetric_divisor_cm3_per_kg"
                )
            elif any(
                metadata[template_id][key] != _text(row, key)
                for key in metadata[template_id]
                if key not in {"volumetric_divisor", "effective_to"}
            ):
                raise LogisticsTemplateImportError("同一模板编号的上下文或版本不一致")
            grouped.setdefault(template_id, []).append(band)
        except (KeyError, ValueError, LogisticsTemplateImportError) as exc:
            errors.append(f"第 {row_number} 行：{exc}")
    templates: list[FbsLogisticsTemplate] = []
    if not errors:
        for template_id, bands in grouped.items():
            info = metadata[template_id]
            ordered = tuple(sorted(bands, key=lambda item: item.max_chargeable_weight_g))
            if len(ordered) != len({item.max_chargeable_weight_g for item in ordered}):
                errors.append(f"模板 {template_id} 存在重复重量上限")
                continue
            templates.append(
                FbsLogisticsTemplate(
                    template_id=template_id,
                    volumetric_divisor_cm3_per_kg=int(info["volumetric_divisor"]),
                    bands=ordered,
                    trace=RateTrace(
                        version=info["version"],
                        source=info["source"],
                        effective_at=info["effective_from"],
                    ),
                    fulfillment_type=info["fulfillment_type"],
                    warehouse_id=info["warehouse_id"],
                    route_id=info["route_id"],
                    region_id=info["region_id"],
                    effective_to=info["effective_to"] or None,
                )
            )
    return LogisticsTemplateImportPreview(tuple(templates), row_count, tuple(errors))


def _text(row: dict[str, str | None], name: str) -> str:
    """读取并清理一个不可为空的文本字段。"""
    value = (row.get(name) or "").strip()
    if not value:
        raise LogisticsTemplateImportError(f"{name} 不能为空")
    return value


def _optional_text(row: dict[str, str | None], name: str) -> str:
    """读取允许为空的文本字段；空值表示当前版本没有结束日期。"""
    return (row.get(name) or "").strip()


def _positive_int(row: dict[str, str | None], name: str) -> int:
    """读取必须大于零的整数列。"""
    value = int(_text(row, name))
    if value <= 0:
        raise LogisticsTemplateImportError(f"{name} 必须大于 0")
    return value


def _nonnegative_int(row: dict[str, str | None], name: str) -> int:
    """读取允许为零但不允许为负的整数列。"""
    raw = (row.get(name) or "0").strip()
    value = int(raw)
    if value < 0:
        raise LogisticsTemplateImportError(f"{name} 不能为负数")
    return value
