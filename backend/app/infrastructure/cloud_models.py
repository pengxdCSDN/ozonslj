"""云端翻译和 Embedding 适配器。

适配器只负责调用 OpenAI-compatible 的 HTTPS 接口；2GB 服务器不下载、不加载
任何模型。API Key 只进入请求头，错误信息和异常文本不得包含请求头内容。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlparse

import httpx

from backend.app.domain.knowledge_retrieval import EmbeddingPort


class CloudModelError(RuntimeError):
    """云端模型调用失败，已去除凭据和完整响应正文。"""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        # 仅保留 HTTP 状态码，禁止保存或传播供应商原始响应和请求头。
        self.status_code = status_code


class CloudModelQuotaError(CloudModelError):
    """云端供应商额度、限流或余额不足，调用方应切换备用供应商。"""


class CloudTranslationPort:
    """翻译端口；实现必须返回与输入顺序一致的中文译文。"""

    async def translate(self, texts: Sequence[str]) -> list[str]:
        raise NotImplementedError


class DashScopeEmbeddingClient(EmbeddingPort):
    """阿里云百炼 Embedding 客户端，默认使用多语言 text-embedding-v4。"""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "text-embedding-v4",
        dimension: int = 1024,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        timeout_seconds: float = 30.0,
        send_dimensions: bool = True,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("Embedding API Key 不能为空")
        if dimension not in {64, 128, 256, 512, 768, 1024, 1536, 2048}:
            raise ValueError("Embedding 维度必须是供应商支持的固定值")
        _validate_cloud_base_url(base_url)
        self.model_id = model.strip()
        self.dimension = dimension
        # 不同 OpenAI 兼容供应商对可选字段的支持并不一致；调用方可关闭该字段，避免把
        # DashScope/Qwen 的参数发送给不接受它的模型（例如 SiliconFlow 的 BAAI/bge-m3）。
        self.send_dimensions = send_dimensions
        self._api_key = api_key
        self._endpoint = f"{base_url.rstrip('/')}/embeddings"
        self._timeout = httpx.Timeout(timeout_seconds)
        self._transport = transport

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not text.strip() for text in texts):
            raise ValueError("Embedding 输入不能包含空文本")
        payload = {
            "model": self.model_id,
            "input": texts,
            "encoding_format": "float",
        }
        if self.send_dimensions:
            payload["dimensions"] = self.dimension
        response = await self._post(payload)
        data = response.get("data")
        if not isinstance(data, list) or len(data) != len(texts):
            raise CloudModelError("Embedding 响应数量与输入不一致")
        ordered = sorted(data, key=lambda item: int(item.get("index", 0)))
        vectors: list[list[float]] = []
        for item in ordered:
            vector = item.get("embedding") if isinstance(item, dict) else None
            if not isinstance(vector, list) or len(vector) != self.dimension:
                raise CloudModelError("Embedding 响应维度不符合当前索引配置")
            vectors.append([float(value) for value in vector])
        return vectors

    async def _post(self, payload: dict[str, object]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                response = await client.post(
                    self._endpoint,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
        except httpx.HTTPError as error:
            raise CloudModelError("Embedding 云端网络请求失败") from error
        if response.status_code == 429:
            raise CloudModelQuotaError("Embedding 供应商额度或限流已触发", status_code=429)
        if response.is_error:
            raise CloudModelError("Embedding 云端请求失败", status_code=response.status_code)
        try:
            result = response.json()
        except json.JSONDecodeError as error:
            raise CloudModelError("Embedding 响应不是合法 JSON") from error
        if not isinstance(result, dict):
            raise CloudModelError("Embedding 响应结构无效")
        return result


class OpenAICompatibleTranslationClient(CloudTranslationPort):
    """使用云端 Chat Completions 翻译俄文，不在本机执行模型。"""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float = 45.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key.strip() or not model.strip() or not base_url.strip():
            raise ValueError("翻译供应商必须配置 API Key、模型和 HTTPS 地址")
        _validate_cloud_base_url(base_url)
        self.model_id = model.strip()
        self._api_key = api_key
        self._endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self._timeout = httpx.Timeout(timeout_seconds)
        self._transport = transport

    async def translate(self, texts: Sequence[str]) -> list[str]:
        results: list[str] = []
        for text in texts:
            if not text.strip():
                raise ValueError("翻译输入不能包含空文本")
            results.append(await self._translate_one(text))
        return results

    async def _translate_one(self, text: str) -> str:
        payload = {
            "model": self.model_id,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是跨境电商俄中本地化翻译器。只翻译输入文本为简体中文，"
                        "保留品牌、型号、SKU、数字、单位和专有名词；不要补充原文没有的信息。"
                    ),
                },
                {"role": "user", "content": text},
            ],
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                response = await client.post(
                    self._endpoint,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
        except httpx.HTTPError as error:
            raise CloudModelError("翻译云端网络请求失败") from error
        if response.status_code == 429:
            raise CloudModelQuotaError("翻译供应商额度或限流已触发", status_code=429)
        if response.is_error:
            raise CloudModelError("翻译云端请求失败", status_code=response.status_code)
        try:
            result = response.json()
            translated = result["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
            raise CloudModelError("翻译响应结构无效") from error
        if not isinstance(translated, str) or not translated.strip():
            raise CloudModelError("翻译响应为空")
        return translated.strip()


def _validate_cloud_base_url(base_url: str) -> None:
    """拒绝明文外部地址，避免模型 Key 被发送到意外的私网或环回服务。"""

    parsed = urlparse(base_url.strip())
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError("云端模型地址必须是合法 HTTP(S) URL")
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise ValueError("非本地云端模型地址必须使用 HTTPS")
