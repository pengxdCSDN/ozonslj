"""生产知识 RAG 运行时：PostgreSQL 保存事实，Chroma 保存可重建向量。"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Literal, Protocol, cast

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from backend.app.config import Settings
from backend.app.domain.knowledge_chunking import ChunkMetadata, KnowledgeChunk
from backend.app.domain.knowledge_governance import KnowledgeSource, KnowledgeVersion
from backend.app.domain.knowledge_query import (
    AnswerGeneratorPort,
    KnowledgeCitation,
    KnowledgeQueryEngine,
    RerankerPort,
)
from backend.app.domain.knowledge_retrieval import (
    DeterministicEmbedding,
    EmbeddingPort,
    InMemoryKeywordIndex,
    RetrievalHit,
)
from backend.app.domain.model_budget import (
    BudgetPurpose,
    ModelBudgetPolicy,
    ModelBudgetUsage,
    decide_budget,
)
from backend.app.domain.rag_evaluation_corpus import fixed_evaluation_chunks
from backend.app.infrastructure.cloud_models import (
    CloudModelError,
    DashScopeEmbeddingClient,
    OpenAICompatibleRerankClient,
    OpenAICompatibleTextClient,
)
from backend.app.infrastructure.local.chroma_vector_index import (
    HttpChromaCollection,
    HttpChromaVectorIndex,
    _metadata_for_chunk,
)
from backend.app.infrastructure.model_credentials import ModelCredentialStore
from backend.app.infrastructure.postgres.knowledge_keyword_search import (
    PostgresKnowledgeKeywordSearch,
)


class _ExecutableConnection(Protocol):
    """说明 _ExecutableConnection 的职责、状态边界和对外协作关系。"""
    async def execute(self, query: str, params: tuple[object, ...]) -> object:
        """执行 execute 的业务流程并返回该流程的结果。

Args:
    query: 参数语义、输入边界和安全约束。
    params: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


class _ManagedEmbeddingRouter(EmbeddingPort):
    """从数据库读取启用的向量模型并按优先级执行自动降级。

    页面保存的是供应商元数据，API Key 通过凭据存储读取。每次批量向量化前重新读取启用状态和优先级，
    使停用、调序和配额切换无需重启 API；供应商异常不会被当作有效向量返回。
    """

    def __init__(
        self,
        *,
        pool: AsyncConnectionPool,
        organization_id: str,
        credentials: ModelCredentialStore,
        fallback: EmbeddingPort,
        configured_dimension: int,
    ) -> None:
        """初始化对象依赖和运行时状态。

Args:
    pool: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。
    credentials: 参数语义、输入边界和安全约束。
    fallback: 参数语义、输入边界和安全约束。
    configured_dimension: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._pool = pool
        self._organization_id = organization_id
        self._credentials = credentials
        self._fallback = fallback
        self.model_id = fallback.model_id
        # 生产主备模型必须共享配置中的索引维度；不能继承测试用确定性
        # Embedding 的 32 维，否则真实 1024 维响应会被误判为不兼容。
        self.dimension = configured_dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """执行 embed 的业务流程并返回该流程的结果。

Args:
    texts: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
        candidates = await self._candidates()
        errors: list[str] = []
        for provider_id, model, base_url, _credential_ref in candidates:
            if not await self._budget_allows(provider_id):
                errors.append(f"{provider_id}:budget_exceeded")
                continue
            api_key = await self._credentials.get(provider_id)
            if not api_key:
                errors.append(f"{provider_id}:credential_missing")
                continue
            try:
                # 当前云端 Embedding 客户端采用 OpenAI-compatible embeddings 协议，
                # 因此供应商名称保持可扩展；后续可按 adapter_type 注入专用客户端。
                client = DashScopeEmbeddingClient(
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    dimension=self.dimension,
                    # SiliconFlow 等 OpenAI-compatible 网关不一定支持
                    # dimensions 可选字段；响应解析仍会严格校验向量维度。
                    send_dimensions=False,
                    # 不同兼容网关对单文本 input 的字符串/数组形态实现不同；
                    # 400 时只允许一次有限的数组形态重试。
                    retry_alternate_input=True,
                )
                vectors = await client.embed(texts)
                await self._record_usage(provider_id, client.last_usage.total_tokens)
                return vectors
            except (CloudModelError, TimeoutError, RuntimeError) as error:
                # 仅记录适配器生成的脱敏业务错误，禁止传播供应商原始响应或凭据。
                errors.append(f"{provider_id}:{type(error).__name__}:{error}")
        if candidates:
            raise RuntimeError("所有已配置向量供应商均不可用，已安全降级：" + ",".join(errors))
        return await self._fallback.embed(texts)

    async def _budget_allows(self, provider_id: str) -> bool:
        """调用前读取同一组织、同一用途的预算门禁，超限不再消耗供应商额度。

Args:
    provider_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        period_start = _period_start()
        async with self._pool.connection() as connection, connection.cursor(
            row_factory=dict_row
        ) as cursor:
            await _set_scope(connection, self._organization_id)
            await cursor.execute(
                """
                SELECT p.daily_token_limit, p.monthly_token_limit, p.daily_request_limit,
                       p.monthly_budget, u.daily_tokens, u.monthly_tokens,
                       u.daily_requests, u.monthly_cost
                FROM rag_model_budget_policies p
                LEFT JOIN rag_model_budget_usage u
                  ON u.organization_id=p.organization_id AND u.provider_id=p.provider_id
                 AND u.purpose=p.purpose AND u.period_start=%s
                WHERE p.organization_id=%s AND p.provider_id=%s AND p.purpose='embedding'
                """,
                (period_start, self._organization_id, provider_id),
            )
            row = await cursor.fetchone()
        if row is None:
            return True
        policy = ModelBudgetPolicy(
            provider_id=provider_id,
            daily_token_limit=int(row["daily_token_limit"]),
            monthly_token_limit=int(row["monthly_token_limit"]),
            daily_request_limit=int(row["daily_request_limit"]),
            monthly_budget=float(row["monthly_budget"]),
            purpose="embedding",
        )
        usage = ModelBudgetUsage(
            daily_tokens=int(row["daily_tokens"] or 0),
            monthly_tokens=int(row["monthly_tokens"] or 0),
            daily_requests=int(row["daily_requests"] or 0),
            monthly_cost=float(row["monthly_cost"] or 0),
        )
        return decide_budget(policy, usage).allowed

    async def _record_usage(self, provider_id: str, total_tokens: int) -> None:
        """将真实响应 token 和一次请求原子累加到应用台账。

Args:
    provider_id: 参数语义、输入边界和安全约束。
    total_tokens: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        period_start = _period_start()
        async with self._pool.connection() as connection, connection.transaction():
            await _set_scope(connection, self._organization_id)
            await connection.execute(
                """
                INSERT INTO rag_model_budget_usage
                    (organization_id, provider_id, purpose, period_start,
                     daily_tokens, monthly_tokens, daily_requests, monthly_cost)
                VALUES (%s, %s, 'embedding', %s, %s, %s, 1, 0)
                ON CONFLICT (organization_id, provider_id, purpose, period_start)
                DO UPDATE SET
                    daily_tokens=rag_model_budget_usage.daily_tokens+EXCLUDED.daily_tokens,
                    monthly_tokens=rag_model_budget_usage.monthly_tokens+EXCLUDED.monthly_tokens,
                    daily_requests=rag_model_budget_usage.daily_requests+1,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (self._organization_id, provider_id, period_start, total_tokens, total_tokens),
            )

    async def _candidates(self) -> list[tuple[str, str, str, str | None]]:
        """执行内部步骤 _candidates，供同一模块的公开流程复用。
Returns:
    返回调用完成后的领域结果。"""
        async with self._pool.connection() as connection, connection.cursor(
            row_factory=dict_row
        ) as cursor:
            await _set_scope(connection, self._organization_id)
            await cursor.execute(
                """
                SELECT primary_provider_id, fallback_provider_ids
                FROM rag_model_purpose_bindings
                WHERE organization_id=%s AND purpose='embedding'
                """,
                (self._organization_id,),
            )
            binding = await cursor.fetchone()
            if binding is None:
                return []
            provider_ids = [
                str(binding["primary_provider_id"]),
                *[str(item) for item in (binding["fallback_provider_ids"] or [])],
            ]
            await cursor.execute(
                """
                SELECT id, model, base_url, credential_ref
                FROM rag_model_providers
                WHERE organization_id=%s AND model_kind='embedding' AND enabled=TRUE
                  AND id=ANY(%s)
                """,
                (self._organization_id, provider_ids),
            )
            rows = await cursor.fetchall()
        by_id = {str(row["id"]): row for row in rows}
        return [
            (
                provider_id,
                str(by_id[provider_id]["model"]),
                str(by_id[provider_id]["base_url"]),
                by_id[provider_id]["credential_ref"],
            )
            for provider_id in provider_ids
            if provider_id in by_id
        ]


class _ManagedRerankerRouter(RerankerPort):
    """按 rerank 用途绑定执行主备重排；失败时由问答引擎保留原召回顺序。"""

    def __init__(self, *, pool: AsyncConnectionPool, organization_id: str,
                 credentials: ModelCredentialStore) -> None:
        """初始化对象依赖和运行时状态。

Args:
    pool: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。
    credentials: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._pool, self._organization_id, self._credentials = pool, organization_id, credentials

    async def rerank(self, query: str, hits: list[RetrievalHit]) -> list[RetrievalHit]:
        """执行 rerank 的业务流程并返回该流程的结果。

Args:
    query: 参数语义、输入边界和安全约束。
    hits: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
        candidates = await _bound_candidates(self._pool, self._organization_id, "rerank", "rerank")
        if not candidates:
            return hits
        errors: list[str] = []
        documents = [hit.chunk.content for hit in hits]
        for provider_id, model, base_url in candidates:
            if not await _budget_allows(self._pool, self._organization_id, provider_id, "rerank"):
                errors.append(f"{provider_id}:budget_exceeded")
                continue
            api_key = await self._credentials.get(provider_id)
            if not api_key:
                errors.append(f"{provider_id}:credential_missing")
                continue
            try:
                client = OpenAICompatibleRerankClient(
                    api_key=api_key, model=model, base_url=base_url
                )
                ranked = await client.rerank(query=query, documents=documents)
                ordered: list[RetrievalHit] = []
                for item in ranked:
                    index = item.get("index")
                    if isinstance(index, int) and 0 <= index < len(hits):
                        ordered.append(hits[index])
                ordered.extend(hit for hit in hits if hit not in ordered)
                await _record_usage(
                    self._pool, self._organization_id, provider_id, "rerank",
                    client.last_usage.total_tokens,
                )
                return ordered
            except (CloudModelError, TimeoutError, RuntimeError, ValueError) as error:
                errors.append(f"{provider_id}:{type(error).__name__}:{error}")
        raise RuntimeError("所有已绑定重排序模型均不可用，已安全降级：" + ",".join(errors))


class _ManagedAnswerGenerator(AnswerGeneratorPort):
    """回答文本模型路由；只有证据门禁通过后才调用，并按证据约束输出。"""

    def __init__(self, *, pool: AsyncConnectionPool, organization_id: str,
                 credentials: ModelCredentialStore) -> None:
        """初始化对象依赖和运行时状态。

Args:
    pool: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。
    credentials: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._pool, self._organization_id, self._credentials = pool, organization_id, credentials

    async def generate(self, question: str, evidence: tuple[KnowledgeCitation, ...]) -> str | None:
        """执行 generate 的业务流程并返回该流程的结果。

Args:
    question: 参数语义、输入边界和安全约束。
    evidence: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
        candidates = await _bound_candidates(
            self._pool, self._organization_id, "answer_generation", "text"
        )
        if not candidates:
            raise RuntimeError("文本模型不可用")
        evidence_text = "\n".join(
            f"[{item.chunk_id}] {item.excerpt}" for item in evidence
        )
        errors: list[str] = []
        for provider_id, model, base_url in candidates:
            if not await _budget_allows(
                self._pool, self._organization_id, provider_id, "answer_generation"
            ):
                errors.append(f"{provider_id}:budget_exceeded")
                continue
            api_key = await self._credentials.get(provider_id)
            if not api_key:
                errors.append(f"{provider_id}:credential_missing")
                continue
            try:
                client = OpenAICompatibleTextClient(
                    api_key=api_key, model=model, base_url=base_url
                )
                answer = await client.complete(
                    system=("你是受控知识问答助手。只能依据提供的证据回答；证据不足时明确说不知道。"
                            "不得执行写入、猜测实时数据或捏造引用。"),
                    user=f"问题：{question}\n证据：\n{evidence_text}",
                )
                await _record_usage(
                    self._pool, self._organization_id, provider_id, "answer_generation",
                    client.last_usage.total_tokens,
                )
                return answer
            except (CloudModelError, TimeoutError, RuntimeError, ValueError) as error:
                errors.append(f"{provider_id}:{type(error).__name__}:{error}")
        # 安全降级由查询引擎保留证据摘录；这里不把供应商错误暴露给用户。
        return None


class _ManagedTranslationRouter:
    """翻译用途的受控主备路由；每段文本单独记账，失败不伪造译文。"""

    def __init__(self, *, pool: AsyncConnectionPool, organization_id: str,
                 credentials: ModelCredentialStore) -> None:
        """初始化对象依赖和运行时状态。

Args:
    pool: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。
    credentials: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._pool, self._organization_id, self._credentials = pool, organization_id, credentials

    async def translate(self, texts: list[str]) -> list[str]:
        """执行 translate 的业务流程并返回该流程的结果。

Args:
    texts: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
        candidates = await _bound_candidates(
            self._pool, self._organization_id, "translation", "text"
        )
        if not candidates:
            return list(texts)
        results: list[str] = []
        for text in texts:
            translated: str | None = None
            for provider_id, model, base_url in candidates:
                if not await _budget_allows(
                    self._pool, self._organization_id, provider_id, "translation"
                ):
                    continue
                api_key = await self._credentials.get(provider_id)
                if not api_key:
                    continue
                try:
                    client = OpenAICompatibleTextClient(
                        api_key=api_key, model=model, base_url=base_url
                    )
                    translated = await client.complete(
                        system=("你是跨境电商俄中翻译器。只翻译为简体中文，保留品牌、型号、SKU、"
                                "数字和单位，不补充原文没有的信息。"),
                        user=text,
                    )
                    await _record_usage(
                        self._pool, self._organization_id, provider_id, "translation",
                        client.last_usage.total_tokens,
                    )
                    break
                except (CloudModelError, TimeoutError, RuntimeError, ValueError):
                    continue
            if translated is None:
                raise RuntimeError("翻译供应商均不可用，已安全拒绝生成不可靠译文")
            results.append(translated)
        return results


async def _bound_candidates(pool: AsyncConnectionPool, organization_id: str,
                            purpose: str, model_kind: str) -> list[tuple[str, str, str]]:
    """解析用途绑定并再次校验模型类型，防止错误用途调用错误模型。

Args:
    pool: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。
    purpose: 参数语义、输入边界和安全约束。
    model_kind: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    async with pool.connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
        await _set_scope(connection, organization_id)
        await cursor.execute(
            """SELECT primary_provider_id, fallback_provider_ids
               FROM rag_model_purpose_bindings
              WHERE organization_id=%s AND purpose=%s""", (organization_id, purpose)
        )
        binding = await cursor.fetchone()
        if binding is None:
            return []
        ids = [str(binding["primary_provider_id"]), *[
            str(item) for item in (binding["fallback_provider_ids"] or [])
        ]]
        await cursor.execute(
            """SELECT id, model, base_url FROM rag_model_providers
               WHERE organization_id=%s AND enabled=TRUE AND model_kind=%s AND id=ANY(%s)
               ORDER BY array_position(%s, id)""",
            (organization_id, model_kind, ids, ids),
        )
        rows = await cursor.fetchall()
    by_id = {
        str(row["id"]): (str(row["id"]), str(row["model"]), str(row["base_url"]))
        for row in rows
    }
    return [by_id[item] for item in ids if item in by_id]


async def _budget_allows(pool: AsyncConnectionPool, organization_id: str,
                         provider_id: str, purpose: str) -> bool:
    """执行内部步骤 _budget_allows，供同一模块的公开流程复用。

Args:
    pool: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。
    provider_id: 参数语义、输入边界和安全约束。
    purpose: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    period_start = _period_start()
    month_start = period_start.replace(day=1)
    async with pool.connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
        await _set_scope(connection, organization_id)
        await cursor.execute(
            """SELECT p.daily_token_limit, p.monthly_token_limit, p.daily_request_limit,
                      p.monthly_budget, u.daily_tokens, u.monthly_tokens,
                      u.daily_requests, u.monthly_cost
                 FROM rag_model_budget_policies p
                 LEFT JOIN (
                   SELECT organization_id, provider_id, purpose,
                          COALESCE(
                              SUM(daily_tokens) FILTER (WHERE period_start=%s), 0
                          ) AS daily_tokens,
                          COALESCE(SUM(monthly_tokens), 0) AS monthly_tokens,
                          COALESCE(
                              SUM(daily_requests) FILTER (WHERE period_start=%s), 0
                          ) AS daily_requests,
                          COALESCE(SUM(monthly_cost), 0) AS monthly_cost
                   FROM rag_model_budget_usage
                   WHERE period_start >= %s AND period_start < (%s + INTERVAL '1 month')::date
                   GROUP BY organization_id, provider_id, purpose
                 ) u ON u.organization_id=p.organization_id AND u.provider_id=p.provider_id
                   AND u.purpose=p.purpose
                WHERE p.organization_id=%s AND p.provider_id=%s AND p.purpose=%s""",
            (period_start, period_start, month_start, month_start,
             organization_id, provider_id, purpose),
        )
        row = await cursor.fetchone()
    if row is None:
        return True
    policy = ModelBudgetPolicy(
        provider_id=provider_id, daily_token_limit=int(row["daily_token_limit"]),
        monthly_token_limit=int(row["monthly_token_limit"]),
        daily_request_limit=int(row["daily_request_limit"]),
        monthly_budget=float(row["monthly_budget"]),
        purpose=cast(BudgetPurpose, purpose),
    )
    usage = ModelBudgetUsage(
        daily_tokens=int(row["daily_tokens"] or 0), monthly_tokens=int(row["monthly_tokens"] or 0),
        daily_requests=int(row["daily_requests"] or 0),
        monthly_cost=float(row["monthly_cost"] or 0),
    )
    return decide_budget(policy, usage).allowed


async def _record_usage(pool: AsyncConnectionPool, organization_id: str, provider_id: str,
                        purpose: str, total_tokens: int) -> None:
    """执行内部步骤 _record_usage，供同一模块的公开流程复用。

Args:
    pool: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。
    provider_id: 参数语义、输入边界和安全约束。
    purpose: 参数语义、输入边界和安全约束。
    total_tokens: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    period_start = _period_start()
    async with pool.connection() as connection, connection.transaction():
        await _set_scope(connection, organization_id)
        await connection.execute(
            """INSERT INTO rag_model_budget_usage
                 (organization_id, provider_id, purpose, period_start, daily_tokens,
                  monthly_tokens, daily_requests, monthly_cost)
               VALUES (%s,%s,%s,%s,%s,%s,1,0)
            ON CONFLICT (organization_id, provider_id, purpose, period_start) DO UPDATE SET
              daily_tokens=rag_model_budget_usage.daily_tokens+EXCLUDED.daily_tokens,
              monthly_tokens=rag_model_budget_usage.monthly_tokens+EXCLUDED.monthly_tokens,
              daily_requests=rag_model_budget_usage.daily_requests+1,
              updated_at=CURRENT_TIMESTAMP""",
            (organization_id, provider_id, purpose, period_start, max(total_tokens, 0),
             max(total_tokens, 0)),
        )


def _period_start() -> date:
    """执行内部步骤 _period_start，供同一模块的公开流程复用。
Returns:
    返回调用完成后的领域结果。"""
    return date.today()


class PostgresChromaKnowledgeRuntime:
    """知识治理和检索的持久化实现。

    PostgreSQL 是唯一事实来源，Chroma 只保存已发布切片的向量和引用元数据。
    撤回、删除和版本替换先提交数据库状态，再删除 Chroma 向量，避免草稿或
    已撤回内容重新进入召回结果。
    """

    persistent = True

    def __init__(self, settings: Settings) -> None:
        """初始化对象依赖和运行时状态。

Args:
    settings: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
        if settings.database_url is None:
            raise ValueError("生产 RAG 运行时需要 PostgreSQL 连接")
        if settings.chroma_url is None:
            raise ValueError("生产 RAG 运行时需要 CHROMA_URL")
        self.organization_id = settings.default_organization_id
        self._pool = AsyncConnectionPool(
            conninfo=str(settings.database_url), min_size=1, max_size=2, open=False
        )
        self._chroma_url = str(settings.chroma_url)
        self._collection: HttpChromaCollection | None = None
        self._credentials = ModelCredentialStore(settings.rag_provider_credentials_dir)
        # 未配置云端 Key 时保留确定性实现，便于本地迁移和健康检查；生产启用真实
        # Embedding 前必须显式注入 RAG_EMBEDDING_API_KEY，并为新维度重建 Chroma 索引。
        self._embedding: EmbeddingPort
        configured_embedding: EmbeddingPort
        if settings.rag_embedding_api_key:
            if settings.rag_embedding_provider not in {None, "dashscope"}:
                raise ValueError("当前生产运行时只允许使用已实现的 DashScope Embedding 适配器")
            configured_embedding = DashScopeEmbeddingClient(
                api_key=settings.rag_embedding_api_key,
                model=settings.rag_embedding_model,
                dimension=settings.rag_embedding_dimension,
                base_url=(
                    str(settings.rag_embedding_base_url)
                    if settings.rag_embedding_base_url
                    else "https://dashscope.aliyuncs.com/compatible-mode/v1"
                ),
            )
        else:
            configured_embedding = DeterministicEmbedding()
        self._embedding = _ManagedEmbeddingRouter(
            pool=self._pool,
            organization_id=self.organization_id,
            credentials=self._credentials,
            fallback=configured_embedding,
            configured_dimension=settings.rag_embedding_dimension,
        )
        self._pool_open = False
        self._evaluation_collection: HttpChromaCollection | None = None
        self._evaluation_indexed = False

    async def _ensure(self) -> None:
        """执行内部步骤 _ensure，供同一模块的公开流程复用。
Returns:
    返回调用完成后的领域结果。"""
        if not self._pool_open:
            await self._pool.open(wait=True)
            self._pool_open = True
        if self._collection is None:
            self._collection = await HttpChromaCollection.ensure(
                self._chroma_url, "ozonslj_knowledge"
            )

    async def close(self) -> None:
        """释放 API 进程持有的 PostgreSQL 连接池。
Returns:
    返回调用完成后的领域结果。"""
        if self._pool_open:
            await self._pool.close()
            self._pool_open = False

    async def create_source(self, source: KnowledgeSource) -> KnowledgeSource:
        """执行 create_source 的业务流程并返回该流程的结果。

Args:
    source: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        await self._ensure()
        async with self._pool.connection() as connection, connection.transaction():
            await _set_scope(connection, self.organization_id)
            await connection.execute(
                """
                INSERT INTO rag_knowledge_sources
                    (id, organization_id, source_type, business_domain, title,
                     authority_level, sensitivity, status, source_locator)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    source.id,
                    self.organization_id,
                    source.source_type,
                    source.business_domain,
                    source.title,
                    source.authority_level,
                    source.sensitivity,
                    source.status,
                    source.source_locator,
                ),
            )
        return replace(source, organization_id=self.organization_id)

    async def list_sources(self) -> list[KnowledgeSource]:
        """执行 list_sources 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""
        await self._ensure()
        async with self._pool.connection() as connection:
            await _set_scope(connection, self.organization_id)
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(
                    """
                    SELECT id, organization_id, source_type, business_domain,
                           title, authority_level, sensitivity, status, source_locator
                    FROM rag_knowledge_sources
                    WHERE organization_id = %s
                    ORDER BY created_at, id
                    """,
                    (self.organization_id,),
                )
                rows = await cursor.fetchall()
        return [_source(row) for row in rows]

    async def source(self, source_id: str) -> KnowledgeSource | None:
        """执行 source 的业务流程并返回该流程的结果。

Args:
    source_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return next(
            (source for source in await self.list_sources() if source.id == source_id),
            None,
        )

    async def set_source_status(self, source_id: str, status: str) -> KnowledgeSource:
        """执行 set_source_status 的业务流程并返回该流程的结果。

Args:
    source_id: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    KeyError: 业务约束或外部依赖失败时抛出。
"""
        await self._ensure()
        async with self._pool.connection() as connection, connection.transaction():
            await _set_scope(connection, self.organization_id)
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(
                    """
                    UPDATE rag_knowledge_sources
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND organization_id = %s
                    RETURNING id, organization_id, source_type, business_domain,
                              title, authority_level, sensitivity, status, source_locator
                    """,
                    (status, source_id, self.organization_id),
                )
                row = await cursor.fetchone()
        if row is None:
            raise KeyError(source_id)
        updated = _source(row)
        if status in {"active", "paused"}:
            # 暂停不删除版本事实；通过 Chroma 元数据让向量通道立即失效，
            # 恢复时重新 upsert，避免暂停来源仍被语义召回。
            chunks: list[KnowledgeChunk] = []
            for version in await self.list_versions(source_id):
                if version.status == "published":
                    chunks.extend(await self._chunks(version.id, status="published"))
            if chunks:
                adjusted = [
                    replace(
                        chunk,
                        metadata=replace(
                            chunk.metadata,
                            extra=(*chunk.metadata.extra, ("source_status", status)),
                        ),
                    )
                    for chunk in chunks
                ]
                assert self._collection is not None
                await self._collection.upsert(
                    ids=[chunk.chunk_id for chunk in adjusted],
                    documents=[chunk.content for chunk in adjusted],
                    embeddings=await self._embedding.embed(
                        [chunk.content for chunk in adjusted]
                    ),
                    metadatas=[_metadata_for_chunk(chunk) for chunk in adjusted],
                )
        return updated

    async def create_version(self, version: KnowledgeVersion) -> KnowledgeVersion:
        """执行 create_version 的业务流程并返回该流程的结果。

Args:
    version: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        await self._ensure()
        async with self._pool.connection() as connection, connection.transaction():
            await _set_scope(connection, self.organization_id)
            await connection.execute(
                """
                INSERT INTO rag_document_versions
                    (id, organization_id, source_id, version_number, content_hash,
                     parser_name, parser_version, cleaner_version, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    version.id,
                    self.organization_id,
                    version.source_id,
                    version.version_number,
                    version.content_hash,
                    version.parser_name,
                    version.parser_version,
                    version.cleaner_version,
                    version.status,
                ),
            )
        return replace(version, organization_id=self.organization_id)

    async def next_version_number(self, source_id: str) -> int:
        """执行 next_version_number 的业务流程并返回该流程的结果。

Args:
    source_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        await self._ensure()
        async with self._pool.connection() as connection:
            await _set_scope(connection, self.organization_id)
            async with connection.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT COALESCE(MAX(version_number), 0) + 1
                    FROM rag_document_versions
                    WHERE organization_id = %s AND source_id = %s
                    """,
                    (self.organization_id, source_id),
                )
                row = await cursor.fetchone()
        return int(row[0]) if row is not None else 1

    async def list_versions(self, source_id: str) -> list[KnowledgeVersion]:
        """执行 list_versions 的业务流程并返回该流程的结果。

Args:
    source_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        await self._ensure()
        async with self._pool.connection() as connection:
            await _set_scope(connection, self.organization_id)
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(
                    """
                    SELECT id, organization_id, source_id, version_number,
                           content_hash, parser_name, parser_version, cleaner_version, status
                    FROM rag_document_versions
                    WHERE organization_id = %s AND source_id = %s
                    ORDER BY version_number
                    """,
                    (self.organization_id, source_id),
                )
                rows = await cursor.fetchall()
        return [_version(row) for row in rows]

    async def version(self, version_id: str) -> KnowledgeVersion | None:
        """执行 version 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        await self._ensure()
        async with self._pool.connection() as connection:
            await _set_scope(connection, self.organization_id)
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(
                    """
                    SELECT id, organization_id, source_id, version_number,
                           content_hash, parser_name, parser_version, cleaner_version, status
                    FROM rag_document_versions
                    WHERE organization_id = %s AND id = %s
                    """,
                    (self.organization_id, version_id),
                )
                row = await cursor.fetchone()
        return _version(row) if row is not None else None

    async def set_version_status(self, version_id: str, status: str) -> KnowledgeVersion:
        """更新无切片目录版本的状态，供治理接口保持数据库为唯一事实源。

Args:
    version_id: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    KeyError: 业务约束或外部依赖失败时抛出。
"""
        await self._ensure()
        async with self._pool.connection() as connection, connection.transaction():
            await _set_scope(connection, self.organization_id)
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(
                    """
                    UPDATE rag_document_versions
                    SET status = %s
                    WHERE id = %s AND organization_id = %s
                    RETURNING id, organization_id, source_id, version_number,
                              content_hash, parser_name, parser_version,
                              cleaner_version, status
                    """,
                    (status, version_id, self.organization_id),
                )
                row = await cursor.fetchone()
        if row is None:
            raise KeyError(version_id)
        return _version(row)

    async def stage(self, version_id: str, chunks: tuple[KnowledgeChunk, ...]) -> None:
        """幂等写入草稿切片；发布前不更新 Chroma。

Args:
    version_id: 参数语义、输入边界和安全约束。
    chunks: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        await self._ensure()
        async with self._pool.connection() as connection, connection.transaction():
            await _set_scope(connection, self.organization_id)
            for chunk in chunks:
                metadata = chunk.metadata
                await connection.execute(
                    """
                    INSERT INTO rag_knowledge_chunks
                        (id, organization_id, document_version_id, ordinal, parent_chunk_id,
                         content, content_hash, source_locator, title_path, language,
                         chunk_strategy, chunk_strategy_version, page_from, page_to, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft')
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        content_hash = EXCLUDED.content_hash,
                        source_locator = EXCLUDED.source_locator,
                        title_path = EXCLUDED.title_path,
                        language = EXCLUDED.language,
                        chunk_strategy = EXCLUDED.chunk_strategy,
                        chunk_strategy_version = EXCLUDED.chunk_strategy_version,
                        page_from = EXCLUDED.page_from,
                        page_to = EXCLUDED.page_to,
                        status = 'draft',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE rag_knowledge_chunks.organization_id = EXCLUDED.organization_id
                    """,
                    (
                        chunk.chunk_id,
                        self.organization_id,
                        version_id,
                        chunk.ordinal,
                        metadata.parent_chunk_id,
                        chunk.content,
                        chunk.content_hash,
                        metadata.source_locator,
                        list(metadata.title_path),
                        metadata.language,
                        metadata.chunk_strategy,
                        metadata.chunk_strategy_version,
                        metadata.page_from,
                        metadata.page_to,
                    ),
                )

    async def has_staged(self, version_id: str) -> bool:
        """执行 has_staged 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return bool(await self._chunks(version_id, status="draft"))

    async def has_published_version(self, version_id: str) -> bool:
        """执行 has_published_version 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        version = await self.version(version_id)
        return version is not None and version.status == "published"

    async def has_published(self) -> bool:
        """执行 has_published 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""
        await self._ensure()
        async with self._pool.connection() as connection:
            await _set_scope(connection, self.organization_id)
            async with connection.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT EXISTS(
                        SELECT 1 FROM rag_document_versions
                        WHERE organization_id = %s AND status = 'published'
                    )
                    """,
                    (self.organization_id,),
                )
                row = await cursor.fetchone()
        return bool(row and row[0])

    async def _chunks(
        self, version_id: str, *, status: str | None = None
    ) -> list[KnowledgeChunk]:
        """执行内部步骤 _chunks，供同一模块的公开流程复用。

Args:
    version_id: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        await self._ensure()
        query = """
            SELECT c.id, c.content, c.content_hash, c.ordinal, c.document_version_id,
                   c.source_locator, c.title_path, c.language, c.chunk_strategy,
                   c.chunk_strategy_version, c.page_from, c.page_to, c.status,
                   s.id AS source_id, s.business_domain, s.source_type,
                   s.authority_level, s.sensitivity, s.status AS source_status
            FROM rag_knowledge_chunks AS c
            JOIN rag_document_versions AS v ON v.id = c.document_version_id
            JOIN rag_knowledge_sources AS s ON s.id = v.source_id
            WHERE c.organization_id = %s AND c.document_version_id = %s
        """
        params: list[object] = [self.organization_id, version_id]
        if status is not None:
            query += " AND c.status = %s"
            params.append(status)
        query += " ORDER BY c.ordinal, c.id"
        async with self._pool.connection() as connection:
            await _set_scope(connection, self.organization_id)
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, params)
                rows = await cursor.fetchall()
        return [_chunk(row) for row in rows]

    async def _chunks_by_status(self, status: str | None) -> list[KnowledgeChunk]:
        """读取当前组织的全部 RAG 切片，重建时只把发布事实写入 Chroma。

Args:
    status: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        query = """
            SELECT c.id, c.content, c.content_hash, c.ordinal, c.document_version_id,
                   c.source_locator, c.title_path, c.language, c.chunk_strategy,
                   c.chunk_strategy_version, c.page_from, c.page_to, c.status,
                   s.id AS source_id, s.business_domain, s.source_type,
                   s.authority_level, s.sensitivity, s.status AS source_status
            FROM rag_knowledge_chunks AS c
            JOIN rag_document_versions AS v ON v.id = c.document_version_id
            JOIN rag_knowledge_sources AS s ON s.id = v.source_id
            WHERE c.organization_id = %s
        """
        params: list[object] = [self.organization_id]
        if status is not None:
            query += " AND c.status = %s"
            params.append(status)
        query += " ORDER BY c.document_version_id, c.ordinal, c.id"
        async with self._pool.connection() as connection:
            await _set_scope(connection, self.organization_id)
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, params)
                rows = await cursor.fetchall()
        return [_chunk(row) for row in rows]

    async def publish(self, version_id: str) -> int:
        """执行 publish 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    KeyError: 业务约束或外部依赖失败时抛出。
    ValueError: 业务约束或外部依赖失败时抛出。
"""
        await self._ensure()
        version = await self.version(version_id)
        chunks = await self._chunks(version_id)
        if version is None:
            raise KeyError(version_id)
        if not chunks:
            raise ValueError("版本没有可发布切片")
        async with self._pool.connection() as connection, connection.transaction():
            await _set_scope(connection, self.organization_id)
            await connection.execute(
                """
                UPDATE rag_document_versions
                SET status = 'withdrawn', effective_to = CURRENT_TIMESTAMP
                WHERE source_id = %s AND organization_id = %s
                  AND status = 'published' AND id <> %s
                """,
                (version.source_id, self.organization_id, version_id),
            )
            await connection.execute(
                """
                UPDATE rag_knowledge_chunks
                SET status = 'withdrawn', updated_at = CURRENT_TIMESTAMP
                WHERE document_version_id IN (
                    SELECT id FROM rag_document_versions
                    WHERE source_id = %s AND organization_id = %s
                      AND id <> %s AND status = 'withdrawn'
                ) AND organization_id = %s
                """,
                (version.source_id, self.organization_id, version_id, self.organization_id),
            )
            await connection.execute(
                """
                UPDATE rag_knowledge_chunks
                SET status = 'published', updated_at = CURRENT_TIMESTAMP
                WHERE document_version_id = %s AND organization_id = %s
                """,
                (version_id, self.organization_id),
            )
            await connection.execute(
                """
                UPDATE rag_document_versions
                SET status = 'published', published_at = CURRENT_TIMESTAMP,
                    effective_from = CURRENT_TIMESTAMP, effective_to = NULL
                WHERE id = %s AND organization_id = %s
                """,
                (version_id, self.organization_id),
            )
        published = [
            replace(item, metadata=replace(item.metadata, status="published"))
            for item in chunks
        ]
        assert self._collection is not None
        await self._collection.upsert(
            ids=[item.chunk_id for item in published],
            documents=[item.content for item in published],
            embeddings=await self._embedding.embed([item.content for item in published]),
            metadatas=[_metadata_for_chunk(item) for item in published],
        )
        return len(published)

    async def withdraw(self, version_id: str) -> int:
        """执行 withdraw 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        await self._ensure()
        chunks = await self._chunks(version_id)
        async with self._pool.connection() as connection, connection.transaction():
            await _set_scope(connection, self.organization_id)
            await connection.execute(
                """
                UPDATE rag_document_versions
                SET status = 'withdrawn', effective_to = CURRENT_TIMESTAMP
                WHERE id = %s AND organization_id = %s
                """,
                (version_id, self.organization_id),
            )
            await connection.execute(
                """
                UPDATE rag_knowledge_chunks
                SET status = 'withdrawn', updated_at = CURRENT_TIMESTAMP
                WHERE document_version_id = %s AND organization_id = %s
                """,
                (version_id, self.organization_id),
            )
        assert self._collection is not None
        await self._collection.delete(ids=[chunk.chunk_id for chunk in chunks])
        return len(chunks)

    async def delete(self, version_id: str) -> int:
        """执行 delete 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        await self._ensure()
        chunks = await self._chunks(version_id)
        async with self._pool.connection() as connection, connection.transaction():
            await _set_scope(connection, self.organization_id)
            await connection.execute(
                """
                UPDATE rag_document_versions
                SET status = 'deleted', effective_to = CURRENT_TIMESTAMP
                WHERE id = %s AND organization_id = %s
                """,
                (version_id, self.organization_id),
            )
            await connection.execute(
                """
                UPDATE rag_knowledge_chunks
                SET status = 'deleted', updated_at = CURRENT_TIMESTAMP
                WHERE document_version_id = %s AND organization_id = %s
                """,
                (version_id, self.organization_id),
            )
        assert self._collection is not None
        await self._collection.delete(ids=[chunk.chunk_id for chunk in chunks])
        return len(chunks)

    async def rebuild(self) -> int:
        """按 PostgreSQL 当前发布事实重建 Chroma，避免索引成为唯一真相源。
Returns:
    返回调用完成后的领域结果。"""
        await self._ensure()
        chunks = await self._chunks_by_status("published")
        all_chunks = await self._chunks_by_status(None)
        assert self._collection is not None
        if all_chunks:
            await self._collection.delete(ids=[chunk.chunk_id for chunk in all_chunks])
        if chunks:
            await self._collection.upsert(
                ids=[chunk.chunk_id for chunk in chunks],
                documents=[chunk.content for chunk in chunks],
                embeddings=await self._embedding.embed([chunk.content for chunk in chunks]),
                metadatas=[_metadata_for_chunk(item) for item in chunks],
            )
        return len(chunks)

    async def engine(self) -> KnowledgeQueryEngine:
        """执行 engine 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""
        await self._ensure()
        assert self._collection is not None
        return KnowledgeQueryEngine(
            embedding=self._embedding,
            keyword_index=PostgresKnowledgeKeywordSearch(
                self._pool, self.organization_id
            ),
            vector_index=HttpChromaVectorIndex(self._collection, {}),
            reranker=_ManagedRerankerRouter(
                pool=self._pool,
                organization_id=self.organization_id,
                credentials=self._credentials,
            ),
            answer_generator=_ManagedAnswerGenerator(
                pool=self._pool,
                organization_id=self.organization_id,
                credentials=self._credentials,
            ),
        )

    async def evaluation_engine(self, suite: str = "full") -> KnowledgeQueryEngine:
        """构造隔离的正式评测引擎，并幂等发布固定评测语料。

        固定评测语料只进入 ``ozonslj_rag_evaluation``，与业务 collection 完全分离；
        这样质量评测能验证真实 Embedding、Chroma、Reranker 和文本模型，又不会把
        评测问题或人工标注证据污染用户的生产知识问答。collection 数量一致时不重复
        发送 Embedding，避免重复点击评测无意义地消耗供应商额度。

Args:
    suite: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        await self._ensure()
        if self._evaluation_collection is None:
            self._evaluation_collection = await HttpChromaCollection.ensure(
                self._chroma_url, "ozonslj_rag_evaluation"
            )
        # 只为当前评测套件发布证据；30 例通过后，后续 120/240 例会按 ID 补齐。
        # 这避免每次新建快速评测都提前消耗完整固定语料的 Embedding 配额。
        chunks = list(fixed_evaluation_chunks(suite=suite))
        # 每次按 ID 做断点续传。不能用运行时布尔缓存：同一个 Worker 先跑 quick，
        # 再跑 standard/full 时仍需发现并补齐新增切片；仅比较 count 也无法区分缺口。
        # 失败重试只 Embedding 缺失项，避免重复消耗额度并防止预算阻断形成死循环。
        existing_ids = await self._evaluation_collection.existing_ids(
            [item.chunk_id for item in chunks]
        )
        missing = [item for item in chunks if item.chunk_id not in existing_ids]
        # 供应商通常限制单次输入数量；按 64 条分批，单批失败会阻断本次评测，
        # 不会留下“部分索引也算成功”的假通过状态。已存在的切片直接跳过。
        for start in range(0, len(missing), 64):
            batch = missing[start:start + 64]
            await self._evaluation_collection.upsert(
                ids=[item.chunk_id for item in batch],
                documents=[item.content for item in batch],
                embeddings=await self._embedding.embed([item.content for item in batch]),
                metadatas=[_metadata_for_chunk(item) for item in batch],
            )
        self._evaluation_indexed = True
        keyword = InMemoryKeywordIndex()
        await keyword.replace(chunks)
        assert self._evaluation_collection is not None
        return KnowledgeQueryEngine(
            embedding=self._embedding,
            keyword_index=keyword,
            vector_index=HttpChromaVectorIndex(
                self._evaluation_collection,
                {item.chunk_id: item for item in chunks},
            ),
            reranker=_ManagedRerankerRouter(
                pool=self._pool,
                organization_id=self.organization_id,
                credentials=self._credentials,
            ),
            answer_generator=_ManagedAnswerGenerator(
                pool=self._pool,
                organization_id=self.organization_id,
                credentials=self._credentials,
            ),
        )

    async def translate(self, texts: list[str]) -> list[str]:
        """通过 translation 用途绑定执行翻译；该入口供 Worker/API 共用。

Args:
    texts: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        await self._ensure()
        return await _ManagedTranslationRouter(
            pool=self._pool,
            organization_id=self.organization_id,
            credentials=self._credentials,
        ).translate(texts)


async def _set_scope(connection: _ExecutableConnection, organization_id: str) -> None:
    """在每个连接事务中设置 RLS 组织上下文，防止连接池串租户。

Args:
    connection: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    await connection.execute(
        "SELECT set_config('app.organization_id', %s, true)", (organization_id,)
    )


def _source(row: dict[str, object]) -> KnowledgeSource:
    """执行内部步骤 _source，供同一模块的公开流程复用。

Args:
    row: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return KnowledgeSource(
        id=str(row["id"]),
        organization_id=str(row["organization_id"]),
        source_type=cast(Literal["markdown", "postgres_schema", "pdf"], str(row["source_type"])),
        business_domain=cast(
            Literal[
                "domain_language", "requirements", "architecture", "api", "database", "sop",
                "troubleshooting", "ozon_official", "general",
            ],
            str(row["business_domain"]),
        ),
        title=str(row["title"]),
        authority_level=cast(Literal["a", "b", "c"], str(row["authority_level"])),
        sensitivity=cast(Literal["public", "internal", "restricted"], str(row["sensitivity"])),
        status=cast(Literal["active", "paused", "withdrawn", "deleted"], str(row["status"])),
        source_locator=str(row["source_locator"]),
    )


def _version(row: dict[str, object]) -> KnowledgeVersion:
    """执行内部步骤 _version，供同一模块的公开流程复用。

Args:
    row: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return KnowledgeVersion(
        id=str(row["id"]),
        organization_id=str(row["organization_id"]),
        source_id=str(row["source_id"]),
        version_number=int(str(row["version_number"])),
        content_hash=str(row["content_hash"]),
        parser_name=str(row["parser_name"]),
        parser_version=str(row["parser_version"]),
        cleaner_version=str(row["cleaner_version"]),
        status=cast(
            Literal["draft", "processing", "published", "withdrawn", "deleted"],
            str(row["status"]),
        ),
    )


def _chunk(row: dict[str, object]) -> KnowledgeChunk:
    """执行内部步骤 _chunk，供同一模块的公开流程复用。

Args:
    row: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    title_path_value = row["title_path"]
    title_path = (
        tuple(str(item) for item in title_path_value)
        if isinstance(title_path_value, list)
        else ()
    )
    metadata = ChunkMetadata(
        document_id=str(row["source_id"]),
        document_version_id=str(row["document_version_id"]),
        business_domain=cast(
            Literal[
                "domain_language", "requirements", "architecture", "api", "database", "sop",
                "troubleshooting", "ozon_official", "general",
            ],
            str(row["business_domain"]),
        ),
        source_type=cast(Literal["markdown", "postgres_schema", "pdf"], str(row["source_type"])),
        source_level=cast(Literal["a", "b", "c"], str(row["authority_level"])),
        language=str(row["language"]),
        title_path=title_path,
        source_locator=str(row["source_locator"]),
        chunk_strategy=str(row["chunk_strategy"]),
        chunk_strategy_version=str(row["chunk_strategy_version"]),
        status=cast(Literal["draft", "published", "withdrawn", "deleted"], str(row["status"])),
        sensitivity=cast(Literal["public", "internal", "restricted"], str(row["sensitivity"])),
        extra=(("source_status", str(row["source_status"])),),
        page_from=_optional_int(row["page_from"]),
        page_to=_optional_int(row["page_to"]),
    )
    return KnowledgeChunk(
        chunk_id=str(row["id"]),
        content=str(row["content"]),
        content_hash=str(row["content_hash"]),
        ordinal=int(str(row["ordinal"])),
        metadata=metadata,
    )


def _optional_int(value: object) -> int | None:
    """执行内部步骤 _optional_int，供同一模块的公开流程复用。

Args:
    value: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return int(str(value)) if value is not None else None
