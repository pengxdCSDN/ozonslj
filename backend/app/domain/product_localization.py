"""Ozon 商品的中俄双语内容边界。

俄文是上游事实，中文是可重新生成的派生内容。领域层只定义数据契约，
不依赖具体翻译厂商或 HTTP SDK，避免把供应商协议泄漏到业务规则中。
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Literal

TranslationStatus = Literal["pending", "succeeded", "failed", "not_required"]


@dataclass(frozen=True, slots=True)
class LocalizedProductContent:
    """商品可检索文本；原文不可被译文覆盖，译文缺失时必须明确标记。"""

    title_ru: str
    title_zh: str | None = None
    description_ru: str | None = None
    description_zh: str | None = None
    attributes_ru: tuple[tuple[str, str], ...] = ()
    attributes_zh: tuple[tuple[str, str], ...] = ()
    translation_status: TranslationStatus = "pending"
    translation_model: str | None = None
    translation_source_hash: str | None = None

    def __post_init__(self) -> None:
        if not self.title_ru.strip():
            raise ValueError("俄文商品标题不能为空；上游原文必须保留")
        if self.title_zh is not None and not self.title_zh.strip():
            raise ValueError("中文商品标题不能是空字符串")
        if self.translation_source_hash is not None and len(self.translation_source_hash) != 64:
            raise ValueError("翻译源指纹必须是 64 位 SHA-256")

    @property
    def source_hash(self) -> str:
        """计算原始俄文内容指纹，用于幂等翻译和判断是否需要重新翻译。"""

        source = "\n".join(
            (
                self.title_ru,
                self.description_ru or "",
                *[f"{key}={value}" for key, value in self.attributes_ru],
            )
        )
        return sha256(source.encode("utf-8")).hexdigest()

    def embedding_text(self) -> str:
        """构造中俄双语检索文本；数字、SKU 和品牌由调用方作为结构化字段保留。"""

        parts = [self.title_zh or "", self.title_ru]
        if self.description_zh:
            parts.append(self.description_zh)
        if self.description_ru:
            parts.append(self.description_ru)
        parts.extend(f"{key}: {value}" for key, value in self.attributes_zh)
        parts.extend(f"{key}: {value}" for key, value in self.attributes_ru)
        return "\n".join(part for part in parts if part.strip())


def translation_request_text(content: LocalizedProductContent) -> str:
    """生成发送给云端翻译服务的纯文本，不包含凭据和无关业务数据。"""

    fields = [f"标题：{content.title_ru}"]
    if content.description_ru:
        fields.append(f"描述：{content.description_ru}")
    fields.extend(f"属性 {key}：{value}" for key, value in content.attributes_ru)
    return "\n".join(fields)
