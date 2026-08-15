"""云端翻译与 Embedding 契约测试；所有请求均使用 MockTransport。"""

import json

import httpx
import pytest

from backend.app.domain.product_localization import LocalizedProductContent
from backend.app.infrastructure.cloud_models import (
    CloudModelError,
    CloudModelNotFoundError,
    CloudModelQuotaError,
    DashScopeEmbeddingClient,
    OpenAICompatibleRerankClient,
    OpenAICompatibleTranslationClient,
)


@pytest.mark.asyncio
async def test_dashscope_embedding_sends_dimension_and_preserves_order() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://example.test/v1/embeddings"
        body = json.loads(request.read().decode("utf-8"))
        assert request.headers["Authorization"] == "Bearer test-key"
        assert body["dimensions"] == 2
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.0, 1.0]},
                    {"index": 0, "embedding": [1.0, 0.0]},
                ]
            },
        )

    client = DashScopeEmbeddingClient(
        api_key="test-key", base_url="https://example.test/v1/embeddings",
        dimension=1024, transport=httpx.MockTransport(handler)
    )
    # 2 维仅用于契约测试，生产配置使用供应商支持的 1024 维。
    client.dimension = 2
    assert await client.embed(["俄文", "中文"]) == [[1.0, 0.0], [0.0, 1.0]]


@pytest.mark.asyncio
async def test_embedding_quota_error_is_classified_without_secret() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "secret should not leak"}})

    client = DashScopeEmbeddingClient(
        api_key="top-secret", dimension=1024, transport=httpx.MockTransport(handler)
    )
    with pytest.raises(CloudModelQuotaError, match="额度") as error:
        await client.embed(["商品"])
    assert "top-secret" not in str(error.value)


@pytest.mark.asyncio
async def test_embedding_can_omit_unsupported_dimensions() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read().decode("utf-8"))
        assert "dimensions" not in body
        assert body["input"] == "测试"
        return httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [0.0, 1.0]}]},
        )

    client = DashScopeEmbeddingClient(
        api_key="test-key",
        dimension=2,
        send_dimensions=False,
        transport=httpx.MockTransport(handler),
    )
    client.dimension = 2
    assert await client.embed(["测试"]) == [[0.0, 1.0]]


@pytest.mark.asyncio
async def test_embedding_error_exposes_safe_upstream_reason_without_secret() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"message": "unsupported field: dimensions", "api_key": "secret"}},
        )

    client = DashScopeEmbeddingClient(
        api_key="top-secret",
        dimension=2,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(CloudModelError, match="unsupported field: dimensions") as error:
        await client.embed(["测试"])
    assert "top-secret" not in str(error.value)


@pytest.mark.asyncio
async def test_embedding_can_auto_detect_dimension_once() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.0, 1.0]}]})

    client = DashScopeEmbeddingClient(
        api_key="test-key", auto_detect_dimension=True,
        transport=httpx.MockTransport(handler)
    )
    assert await client.embed(["测试"]) == [[0.0, 1.0]]
    assert client.dimension == 2


@pytest.mark.asyncio
async def test_text_404_is_classified_as_model_not_found() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "model not found"})

    client = OpenAICompatibleTranslationClient(
        api_key="test-key", model="missing", base_url="https://example.test/v1",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(CloudModelNotFoundError, match="model not found"):
        await client.translate(["测试"])


@pytest.mark.asyncio
async def test_embedding_retries_with_batch_input_after_provider_400() -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        body = json.loads(request.read().decode("utf-8"))
        if attempts == 1:
            assert body["input"] == "测试"
            return httpx.Response(400, json={"code": 20012, "message": "invalid input"})
        assert body["input"] == ["测试"]
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.0, 1.0]}]})

    client = DashScopeEmbeddingClient(
        api_key="test-key",
        dimension=2,
        retry_alternate_input=True,
        transport=httpx.MockTransport(handler),
    )
    assert await client.embed(["测试"]) == [[0.0, 1.0]]
    assert attempts == 2


@pytest.mark.asyncio
async def test_translation_client_returns_cloud_text() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read().decode("utf-8"))
        assert body["temperature"] == 0
        assert "只翻译" in body["messages"][0]["content"]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "男士冬季夹克"}}]},
        )

    client = OpenAICompatibleTranslationClient(
        api_key="test-key",
        model="translation-model",
        base_url="https://example.test/v1",
        transport=httpx.MockTransport(handler),
    )
    assert await client.translate(["Куртка мужская зимняя"]) == ["男士冬季夹克"]


def test_localized_content_keeps_russian_and_builds_bilingual_embedding_text() -> None:
    content = LocalizedProductContent(
        title_ru="Куртка мужская зимняя",
        title_zh="男士冬季夹克",
        attributes_ru=(("цвет", "черный"),),
        attributes_zh=(("颜色", "黑色"),),
    )
    text = content.embedding_text()
    assert "Куртка мужская зимняя" in text
    assert "男士冬季夹克" in text
    assert content.source_hash == content.source_hash


@pytest.mark.asyncio
async def test_rerank_client_sends_query_and_documents() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://example.test/v1/rerank"
        body = json.loads(request.read().decode("utf-8"))
        assert body == {
            "model": "BAAI/bge-reranker-v2-m3",
            "query": "颜色",
            "documents": ["红色", "蓝色"],
            "top_n": 2,
            "return_documents": False,
        }
        return httpx.Response(200, json={"results": [{"index": 0, "relevance_score": 0.9}]})

    client = OpenAICompatibleRerankClient(
        api_key="test-key",
        model="BAAI/bge-reranker-v2-m3",
        base_url="https://example.test/v1",
        transport=httpx.MockTransport(handler),
    )
    assert await client.rerank(query="颜色", documents=["红色", "蓝色"]) == [
        {"index": 0, "relevance_score": 0.9}
    ]


@pytest.mark.asyncio
async def test_rerank_and_text_clients_accept_complete_resource_urls() -> None:
    seen: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if request.url.path.endswith("/rerank"):
            return httpx.Response(200, json={"results": []})
        return httpx.Response(200, json={"choices": [{"message": {"content": "完成"}}]})

    rerank = OpenAICompatibleRerankClient(
        api_key="test-key", model="reranker", base_url="https://example.test/v1/rerank",
        transport=httpx.MockTransport(handler),
    )
    text = OpenAICompatibleTranslationClient(
        api_key="test-key", model="text", base_url="https://example.test/v1/chat/completions",
        transport=httpx.MockTransport(handler),
    )
    await rerank.rerank(query="q", documents=["d"])
    await text.translate(["x"])
    assert seen == [
        "https://example.test/v1/rerank",
        "https://example.test/v1/chat/completions",
    ]
