from dataclasses import dataclass
from typing import Literal, Protocol, cast

DataSource = Literal["official_private", "operator_imported", "public_sample", "derived_estimate"]


@dataclass(frozen=True, slots=True)
class DataProvenance:
    source: DataSource
    observed_at: str
    explanation: str


class DataProvenanceGateway(Protocol):
    async def save(self, *, workspace_id: str, provenance: DataProvenance) -> DataProvenance: ...

    async def list_history(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[DataProvenance]: ...


def classify_source(*, source: str, observed_at: str, explanation: str) -> DataProvenance:
    allowed = {"official_private", "operator_imported", "public_sample", "derived_estimate"}
    if source not in allowed or not observed_at.strip() or not explanation.strip():
        raise ValueError("数据来源必须是受支持的来源标签，并包含时间和说明")
    return DataProvenance(cast(DataSource, source), observed_at, explanation)
