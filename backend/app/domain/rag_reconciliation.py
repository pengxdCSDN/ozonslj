"""PostgreSQL 切片目录与 Chroma 索引的对账计划。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IndexReconciliationPlan:
    """说明 IndexReconciliationPlan 的职责、状态边界和对外协作关系。"""
    upsert_ids: tuple[str, ...]
    delete_ids: tuple[str, ...]
    missing_metadata_ids: tuple[str, ...]

    @property
    def safe_to_publish(self) -> bool:
        """执行 safe_to_publish 的业务流程并返回该流程的结果。"""
        return not self.missing_metadata_ids


def build_reconciliation_plan(
    published_chunk_ids: set[str], indexed_chunk_ids: set[str],
    *, metadata_ids: set[str] | None = None,
) -> IndexReconciliationPlan:
    """只允许已发布目录进入索引；孤立向量必须删除，缺元数据则阻断发布。"""

    metadata = metadata_ids if metadata_ids is not None else published_chunk_ids
    return IndexReconciliationPlan(
        upsert_ids=tuple(sorted(published_chunk_ids - indexed_chunk_ids)),
        delete_ids=tuple(sorted(indexed_chunk_ids - published_chunk_ids)),
        missing_metadata_ids=tuple(sorted(published_chunk_ids - metadata)),
    )
