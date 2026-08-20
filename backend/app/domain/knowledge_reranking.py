"""混合召回后的确定性精排与多跳预算控制。"""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.domain.knowledge_retrieval import RetrievalHit


@dataclass(frozen=True, slots=True)
class RerankPolicy:
    """说明 RerankPolicy 的职责、状态边界和对外协作关系。"""
    max_candidates: int = 30
    min_score: float = 0.0
    authority_bonus: float = 0.05


def rerank_hits(
    hits: list[RetrievalHit], *, policy: RerankPolicy | None = None
) -> list[RetrievalHit]:
    """按 RRF 分数、来源权威等级和发布状态精排，过滤草稿与撤回证据。

Args:
    hits: 参数语义、输入边界和安全约束。
    policy: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    active_policy = policy or RerankPolicy()
    ranked: list[RetrievalHit] = []
    for hit in hits:
        metadata = hit.chunk.metadata
        if metadata.status != "published" or hit.score < active_policy.min_score:
            continue
        bonus = active_policy.authority_bonus if metadata.source_level == "a" else 0.0
        ranked.append(RetrievalHit(hit.chunk, hit.score + bonus, hit.channel))
    ranked.sort(key=lambda item: (-item.score, item.chunk.chunk_id))
    return ranked[: active_policy.max_candidates]


def bounded_hop_queries(
    initial_query: str, evidence: list[RetrievalHit], *, max_hops: int = 2
) -> tuple[str, ...]:
    """只从证据标题路径生成有限补充查询，禁止模型自由扩展导致查询爆炸。

Args:
    initial_query: 参数语义、输入边界和安全约束。
    evidence: 参数语义、输入边界和安全约束。
    max_hops: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    if max_hops <= 0:
        return ()
    queries: list[str] = []
    for hit in evidence:
        for title in hit.chunk.metadata.title_path:
            normalized = title.strip()
            if (
                normalized
                and normalized not in queries
                and normalized.casefold() not in initial_query.casefold()
            ):
                queries.append(normalized)
        if len(queries) >= max_hops:
            break
    return tuple(queries[:max_hops])
