from pathlib import Path

import httpx
import pytest

from backend.app.infrastructure.ocr import paddleocr_document_parser as parser


def test_parse_pdf_requires_https_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PADDLEOCR_DOC_PARSING_API_URL", "http://ocr.example/layout-parsing")
    monkeypatch.setenv("PADDLEOCR_ACCESS_TOKEN", "secret-not-printed")
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"%PDF-1.7")
    with pytest.raises(parser.OcrConfigurationError, match="HTTPS"):
        parser.parse_pdf(path)


def test_parse_pdf_maps_paddle_pages_without_leaking_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PADDLEOCR_DOC_PARSING_API_URL", "https://ocr.example/layout-parsing")
    monkeypatch.setenv("PADDLEOCR_ACCESS_TOKEN", "secret-not-printed")
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"%PDF-1.7")

    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        headers = kwargs.get("headers")
        assert isinstance(headers, dict)
        assert headers["Authorization"] == "token secret-not-printed"
        return httpx.Response(
            200,
            json={
                "errorCode": 0,
                "result": {
                    "layoutParsingResults": [
                        {"markdown": {"text": "# 标题\n\n正文"}, "prunedResult": {}}
                    ]
                },
            },
        )

    monkeypatch.setattr(parser.httpx, "post", fake_post)
    result = parser.parse_pdf(path)
    assert result.provider == "paddleocr-doc-parsing"
    assert result.text == "# 标题\n\n正文"
    assert result.pages[0].page_number == 1


def test_parse_pdf_hides_provider_error_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PADDLEOCR_DOC_PARSING_API_URL", "https://ocr.example/layout-parsing")
    monkeypatch.setenv("PADDLEOCR_ACCESS_TOKEN", "secret-not-printed")
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"%PDF-1.7")
    monkeypatch.setattr(
        parser.httpx,
        "post",
        lambda *args, **kwargs: httpx.Response(429, text="secret provider body"),
    )
    with pytest.raises(parser.OcrProviderError, match="限流") as error:
        parser.parse_pdf(path)
    assert "secret provider body" not in str(error.value)
