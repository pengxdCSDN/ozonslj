from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from backend.app.domain.store_workspace import (
    CredentialProtectionError,
    UnsupportedCredentialVersionError,
)
from backend.app.infrastructure.credential_protection import FernetCredentialProtector


def _write_key(tmp_path: Path) -> Path:
    key_file = tmp_path / "ozon_credential_key"
    key_file.write_bytes(Fernet.generate_key())
    return key_file


def test_credential_round_trip_keeps_plaintext_out_of_ciphertext(tmp_path: Path) -> None:
    protector = FernetCredentialProtector(_write_key(tmp_path), key_version=2)

    ciphertext = protector.protect("  secret-api-key  ")

    assert b"secret-api-key" not in ciphertext
    assert protector.unprotect(ciphertext, credential_version=2) == "secret-api-key"


def test_missing_or_invalid_key_material_fails_safely(tmp_path: Path) -> None:
    with pytest.raises(CredentialProtectionError, match="无法读取"):
        FernetCredentialProtector(tmp_path / "missing", key_version=1)


def test_tampered_or_unknown_version_ciphertext_is_rejected(tmp_path: Path) -> None:
    protector = FernetCredentialProtector(_write_key(tmp_path), key_version=3)

    with pytest.raises(CredentialProtectionError, match="无法解密"):
        protector.unprotect(b"invalid", credential_version=3)
    with pytest.raises(UnsupportedCredentialVersionError, match="不支持凭据版本"):
        protector.unprotect(b"unused", credential_version=2)
