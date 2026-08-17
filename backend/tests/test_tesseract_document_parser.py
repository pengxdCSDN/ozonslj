from pathlib import Path

import pytest

from backend.app.infrastructure.ocr import tesseract_document_parser as parser


def test_parse_pdf_requires_local_binaries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(parser.shutil, "which", lambda _: None)

    with pytest.raises(parser.OcrConfigurationError, match="本地 OCR 未安装"):
        parser.parse_pdf(tmp_path / "scan.pdf")


def test_parse_pdf_runs_local_tools_and_maps_pages(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "scan.pdf"
    source.write_bytes(b"%PDF-test")
    monkeypatch.setattr(parser.shutil, "which", lambda name: name)
    commands: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> object:
        commands.append(command)
        if command[0] == "pdftoppm":
            (tmp_path / "rendered").mkdir()
            # 临时目录由实现创建，第二次通过命令输出前缀定位文件。
            prefix = Path(command[-1])
            prefix.with_name("page-1.png").write_bytes(b"png")
            class RenderResult:
                returncode = 0
                stdout = ""
            return RenderResult()
        class OcrResult:
            returncode = 0
            stdout = "库存同步说明\n第二行"
        return OcrResult()

    monkeypatch.setattr(parser.subprocess, "run", fake_run)
    result = parser.parse_pdf(source)

    assert result.provider == "tesseract-local"
    assert result.text == "库存同步说明\n第二行"
    assert result.pages[0].page_number == 1
    assert commands[1][0] == "tesseract"
    assert "chi_sim+eng" in commands[1]


def test_parse_pdf_rejects_empty_ocr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "scan.pdf"
    source.write_bytes(b"%PDF-test")
    monkeypatch.setattr(parser.shutil, "which", lambda name: name)

    def fake_run(command: list[str], **_: object) -> object:
        if command[0] == "pdftoppm":
            Path(command[-1]).with_name("page-1.png").write_bytes(b"png")
        class Result:
            returncode = 0
            stdout = ""
        return Result()

    monkeypatch.setattr(parser.subprocess, "run", fake_run)
    with pytest.raises(parser.OcrProviderError, match="未识别到可用正文"):
        parser.parse_pdf(source)
