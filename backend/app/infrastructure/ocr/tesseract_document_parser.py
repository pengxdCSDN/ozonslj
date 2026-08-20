"""基于本地 Tesseract 的扫描 PDF 文档解析适配器。

该适配器只处理没有文本层的扫描 PDF。pdftoppm 将页面渲染为临时 PNG，
Tesseract 按页识别中文和英文，随后返回与知识切片链路兼容的统一页面结构。
整个过程不访问网络、不读取 Secret，也不会把原始 OCR 输出写入日志。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


class OcrConfigurationError(ValueError):
    """本地 OCR 运行依赖尚未安装或配置不完整。"""


class OcrProviderError(RuntimeError):
    """本地 OCR 执行失败，消息不包含文档正文或敏感信息。"""


@dataclass(frozen=True, slots=True)
class OcrPage:
    """OCR 单页结果；页码用于引用和后续切片元数据。"""

    page_number: int
    markdown: str
    layout_blocks: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OcrDocument:
    """本地 OCR 的统一输出，不暴露命令行原始 stderr。"""

    text: str
    pages: tuple[OcrPage, ...]
    provider: str


def parse_pdf(path: Path) -> OcrDocument:
    """把扫描 PDF 按页转换为图片并使用本地 Tesseract 识别。"""

    pdftoppm = shutil.which("pdftoppm")
    tesseract = shutil.which("tesseract")
    if not pdftoppm or not tesseract:
        raise OcrConfigurationError(
            "本地 OCR 未安装，请安装 tesseract-ocr、中文语言包和 poppler-utils"
        )
    if not path.is_file():
        raise OcrProviderError("读取隔离 PDF 失败")

    max_pages = _positive_int_env("OCR_MAX_PAGES", 50)
    timeout = _positive_float_env("OCR_PAGE_TIMEOUT_SECONDS", 45.0)
    language = os.environ.get("OCR_TESSERACT_LANG", "chi_sim+eng").strip() or "chi_sim+eng"
    pages: list[OcrPage] = []
    with tempfile.TemporaryDirectory(prefix="ozonslj-ocr-") as temporary_dir:
        prefix = Path(temporary_dir) / "page"
        try:
            render = subprocess.run(
                [
                    pdftoppm,
                    "-r",
                    "200",
                    "-png",
                    "-f",
                    "1",
                    "-l",
                    str(max_pages),
                    str(path),
                    str(prefix),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=max(timeout, 60.0),
            )
        except subprocess.TimeoutExpired as error:
            raise OcrProviderError("本地 OCR 页面渲染超时") from error
        except OSError as error:
            raise OcrProviderError("本地 OCR 页面渲染失败") from error
        if render.returncode != 0:
            raise OcrProviderError("本地 OCR 页面渲染失败")

        image_paths = sorted(Path(temporary_dir).glob("page-*.png"))
        for page_number, image_path in enumerate(image_paths, start=1):
            try:
                result = subprocess.run(
                    [tesseract, str(image_path), "stdout", "-l", language, "--psm", "3"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired as error:
                raise OcrProviderError(f"本地 OCR 第 {page_number} 页超时") from error
            except OSError as error:
                raise OcrProviderError("本地 OCR 执行失败") from error
            if result.returncode != 0:
                raise OcrProviderError(f"本地 OCR 第 {page_number} 页识别失败")
            text = result.stdout.strip()
            if text:
                pages.append(OcrPage(page_number, text, (text,)))

    text = "\n\n".join(page.markdown for page in pages).strip()
    if not text:
        raise OcrProviderError("本地 OCR 未识别到可用正文")
    return OcrDocument(text=text, pages=tuple(pages), provider="tesseract-local")


def _positive_int_env(name: str, default: int) -> int:
    """执行内部步骤 _positive_int_env，供同一模块的公开流程复用。"""
    try:
        value = int(os.environ.get(name, str(default)).strip())
    except ValueError:
        return default
    return value if value > 0 else default


def _positive_float_env(name: str, default: float) -> float:
    """执行内部步骤 _positive_float_env，供同一模块的公开流程复用。"""
    try:
        value = float(os.environ.get(name, str(default)).strip())
    except ValueError:
        return default
    return value if value > 0 else default
