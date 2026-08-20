"""回答声明与检索证据的确定性支持关系校验。"""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.domain.knowledge_retrieval import RetrievalHit


@dataclass(frozen=True, slots=True)
class ClaimSupport:
    """说明 ClaimSupport 的职责、状态边界和对外协作关系。"""
    claim_id: str
    text: str
    citation_ids: tuple[str, ...]
    support_status: str


def validate_claims(
    claims: list[tuple[str, str, tuple[str, ...]]], hits: list[RetrievalHit]
) -> tuple[ClaimSupport, ...]:
    """引用 ID 必须来自当前已发布证据；否则声明标记 unsupported。

Args:
    claims: 参数语义、输入边界和安全约束。
    hits: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    available = {hit.chunk.chunk_id for hit in hits if hit.chunk.metadata.status == "published"}
    result: list[ClaimSupport] = []
    for claim_id, text, citation_ids in claims:
        valid = tuple(citation_id for citation_id in citation_ids if citation_id in available)
        result.append(
            ClaimSupport(
                claim_id=claim_id, text=text, citation_ids=valid,
                support_status="supported" if valid else "unsupported",
            )
        )
    return tuple(result)
