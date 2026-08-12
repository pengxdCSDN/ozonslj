from pathlib import Path


def test_chroma_manifest_is_private_and_resource_bounded() -> None:
    manifest = Path("deploy/chroma.compose.yml").read_text(encoding="utf-8")
    assert '127.0.0.1:8000:8000' in manifest
    assert "memory: 384M" in manifest
    assert "chroma_data" in manifest
    assert "healthcheck:" in manifest
    assert "ozonslj_backend" in manifest
    assert "CHROMA_IMAGE_TAG" in manifest


def test_chroma_acr_build_entrypoint_is_pinned() -> None:
    dockerfile = Path("deploy/base-images/chroma/Dockerfile").read_text(encoding="utf-8")
    assert "FROM chromadb/chroma:0.5.23" in dockerfile
