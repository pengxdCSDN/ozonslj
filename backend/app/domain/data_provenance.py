"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Literal, Protocol, cast

DataSource = Literal["official_private", "operator_imported", "public_sample", "derived_estimate"]


@dataclass(frozen=True, slots=True)
class DataProvenance:
    """说明 DataProvenance 的职责、状态边界和对外协作关系。"""
    source: DataSource
    observed_at: str
    explanation: str


class DataProvenanceGateway(Protocol):
    """说明 DataProvenanceGateway 的职责、状态边界和对外协作关系。"""
    async def save(self, *, workspace_id: str, provenance: DataProvenance) -> DataProvenance:
        """执行 save 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    provenance: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_history(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[DataProvenance]:
        """执行 list_history 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


def classify_source(*, source: str, observed_at: str, explanation: str) -> DataProvenance:
    """执行 classify_source 的业务流程并返回该流程的结果。

Args:
    source: 参数语义、输入边界和安全约束。
    observed_at: 参数语义、输入边界和安全约束。
    explanation: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    allowed = {"official_private", "operator_imported", "public_sample", "derived_estimate"}
    if source not in allowed or not observed_at.strip() or not explanation.strip():
        raise ValueError("数据来源必须是受支持的来源标签，并包含时间和说明")
    return DataProvenance(cast(DataSource, source), observed_at, explanation)
