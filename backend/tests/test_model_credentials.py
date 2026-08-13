from pathlib import Path

import pytest

from backend.app.infrastructure.model_credentials import ModelCredentialStore


@pytest.mark.asyncio
async def test_model_credential_store_writes_atomic_file_without_returning_secret(
    tmp_path: Path,
) -> None:
    store = ModelCredentialStore(tmp_path)
    reference = await store.put("12345678-1234-1234-1234-123456789012", "sk-test-secret")
    assert reference.startswith("file:")
    assert await store.get("12345678-1234-1234-1234-123456789012") == "sk-test-secret"
    assert await store.exists("12345678-1234-1234-1234-123456789012")
    assert "sk-test-secret" not in reference


@pytest.mark.asyncio
async def test_model_credential_store_rejects_path_traversal(tmp_path: Path) -> None:
    store = ModelCredentialStore(tmp_path)
    with pytest.raises(ValueError):
        await store.put("../escape", "sk-test-secret")
