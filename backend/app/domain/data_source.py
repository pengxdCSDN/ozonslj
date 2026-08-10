from dataclasses import dataclass
from typing import Literal

DataSource = Literal["official_private", "operator_imported", "public_sample", "derived_estimate"]


@dataclass(frozen=True, slots=True)
class DataSourceLabel:
    source: DataSource
    label: str
    estimated: bool
    description: str


SOURCE_LABELS: dict[DataSource, tuple[str, bool, str]] = {
    "official_private": ("官方私有", False, "Seller/Performance 官方接口的店铺事实"),
    "operator_imported": ("运营导入", False, "运营人员导入并确认的业务补充事实"),
    "public_sample": ("公开样本", True, "公开页面受控采样，不代表全市场精确值"),
    "derived_estimate": ("推导估算", True, "系统基于输入事实计算的决策辅助结果"),
}


def get_data_source_label(source: str) -> DataSourceLabel:
    normalized = source.strip().lower()
    if normalized not in SOURCE_LABELS:
        raise ValueError("数据来源标签无效")
    label, estimated, description = SOURCE_LABELS[normalized]
    return DataSourceLabel(normalized, label, estimated, description)
