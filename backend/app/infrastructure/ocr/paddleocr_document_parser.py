"""PaddleOCR 文档解析适配器。

云端只调用 HTTPS 文档解析 API，不在 API 进程中安装或执行任意本地 OCR 命令。
这样既能复用 PaddleOCR 文档解析技能定义的请求/响应契约，也能把凭据限制在
服务端环境变量或 Secret 文件中。供应商返回的正文会先经过现有清洗、提示注入
检测和质量门禁，再允许进入知识切片；失败时不返回部分正文。
"""

from __future__ import annotations

import base64
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


class OcrConfigurationError(ValueError):
    """OCR 供应商尚未完成安全配置。"""


class OcrProviderError(RuntimeError):
    """OCR 供应商调用失败，消息不包含凭据。"""


@dataclass(frozen=True, slots=True)
class OcrPage:
    """OCR 单页结构；Markdown 用于正文，布局块用于复杂版面切片。"""

    page_number: int
    markdown: str
    layout_blocks: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OcrDocument:
    """OCR 统一输出，不暴露供应商原始响应或访问令牌。"""

    text: str
    pages: tuple[OcrPage, ...]
    provider: str


def parse_pdf(path: Path) -> OcrDocument:
    """调用 PaddleOCR 文档解析 API；普通文本 PDF 不应进入该函数。"""

    endpoint = os.environ.get("PADDLEOCR_DOC_PARSING_API_URL", "").strip()
    token = _read_secret("PADDLEOCR_ACCESS_TOKEN", "PADDLEOCR_ACCESS_TOKEN_FILE")
    if not endpoint or not token:
        raise OcrConfigurationError(
            "未配置 PaddleOCR 文档解析服务，请配置 PADDLEOCR_DOC_PARSING_API_URL 和 "
            "PADDLEOCR_ACCESS_TOKEN（或 Secret 文件）"
        )
    if not endpoint.startswith("https://") or not endpoint.rstrip("/").endswith("/layout-parsing"):
        raise OcrConfigurationError(
            "PADDLEOCR_DOC_PARSING_API_URL 必须是 HTTPS 且路径以 /layout-parsing 结尾"
        )
    try:
        content = path.read_bytes()
    except OSError as error:
        raise OcrProviderError("读取隔离 PDF 失败") from error
    timeout = _timeout_seconds()
    request = {
        "file": base64.b64encode(content).decode("ascii"),
        "fileType": 0,
        "visualize": False,
        "useDocUnwarping": False,
        "useDocOrientationClassify": False,
    }
    try:
        response = httpx.post(
            endpoint,
            json=request,
            headers={"Authorization": f"token {token}", "Client-Platform": "ozonslj"},
            timeout=timeout,
        )
    except httpx.TimeoutException as error:
        raise OcrProviderError(f"OCR 服务超时（{timeout:g} 秒）") from error
    except httpx.RequestError as error:
        raise OcrProviderError("OCR 服务网络请求失败") from error
    if response.status_code != 200:
        if response.status_code == 403:
            reason = "OCR 服务认证失败"
        elif response.status_code == 429:
            reason = "OCR 服务限流或配额不足"
        elif response.status_code >= 500:
            reason = "OCR 服务暂时不可用"
        else:
            reason = f"OCR 服务返回 HTTP {response.status_code}"
        raise OcrProviderError(reason)
    try:
        payload = response.json()
    except ValueError as error:
        raise OcrProviderError("OCR 服务返回了无效 JSON") from error
    if not isinstance(payload, dict) or payload.get("errorCode", 0) not in (0, "0", None):
        raise OcrProviderError("OCR 服务拒绝解析请求")
    pages = _pages_from_payload(payload)
    text = "\n\n".join(page.markdown.strip() for page in pages if page.markdown.strip()).strip()
    if not pages or not text:
        raise OcrProviderError("OCR 未识别到可用正文")
    return OcrDocument(text=text, pages=tuple(pages), provider="paddleocr-doc-parsing")


def _pages_from_payload(payload: dict[str, Any]) -> list[OcrPage]:
    result = payload.get("result")
    raw_pages = result.get("layoutParsingResults") if isinstance(result, dict) else None
    if not isinstance(raw_pages, list):
        raise OcrProviderError("OCR 返回缺少页面结构")
    pages: list[OcrPage] = []
    for index, raw_page in enumerate(raw_pages, start=1):
        if not isinstance(raw_page, dict):
            continue
        markdown = raw_page.get("markdown")
        markdown_text = markdown.get("text", "") if isinstance(markdown, dict) else ""
        if not isinstance(markdown_text, str):
            continue
        blocks: list[str] = []
        pruned = raw_page.get("prunedResult")
        if isinstance(pruned, dict):
            blocks.extend(_block_texts(pruned.get("parsing_res_list")))
            blocks.extend(_block_texts(pruned.get("layout_det_res")))
        pages.append(OcrPage(index, markdown_text, tuple(dict.fromkeys(blocks))))
    return pages


def _block_texts(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    texts: list[str] = []
    for item in value:
        if isinstance(item, dict):
            text = item.get("text") or item.get("content") or item.get("markdown")
            if isinstance(text, str) and text.strip():
                texts.append(text.strip())
    return texts


def _read_secret(env_name: str, file_env_name: str) -> str:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value
    file_name = os.environ.get(file_env_name, "").strip()
    if not file_name:
        return ""
    try:
        return Path(file_name).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _timeout_seconds() -> float:
    raw = os.environ.get("PADDLEOCR_DOC_PARSING_TIMEOUT", "600").strip()
    try:
        value = float(raw)
    except ValueError:
        return 600.0
    return value if math.isfinite(value) and value > 0 else 600.0
