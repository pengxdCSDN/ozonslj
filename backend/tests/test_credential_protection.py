from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from backend.app.infrastructure.credential_protection import (
    CredentialProtectionError,
    FernetCredentialProtector,
    UnsupportedCredentialVersionError,
)


def _write_key(tmp_path: Path) -> Path:
    key_file = tmp_path / "ozon_credential_key"
    key_file.write_bytes(Fernet.generate_key())
    return key_file


def test_credential_round_trip_keeps_plaintext_out_of_ciphertext(tmp_path: Path) -> None:
    protector = FernetCredentialProtector(_write_key(tmp_path), key_version=2)

    ciphertext = protector.encrypt("  secret-api-key  ")

    assert b"secret-api-key" not in ciphertext
    assert protector.decrypt(ciphertext, credential_version=2) == "secret-api-key"


def test_empty_api_key_is_rejected(tmp_path: Path) -> None:
    protector = FernetCredentialProtector(_write_key(tmp_path), key_version=1)

    with pytest.raises(ValueError, match="不能为空"):
        protector.encrypt("   ")


def test_missing_key_file_has_safe_error(tmp_path: Path) -> None:
    with pytest.raises(CredentialProtectionError, match="无法读取"):
        FernetCredentialProtector(tmp_path / "missing", key_version=1)


def test_tampered_ciphertext_is_rejected(tmp_path: Path) -> None:
    protector = FernetCredentialProtector(_write_key(tmp_path), key_version=1)

    with pytest.raises(CredentialProtectionError, match="无法解密"):
        protector.decrypt(b"not-a-valid-token", credential_version=1)


def test_unknown_credential_version_is_rejected_before_decryption(tmp_path: Path) -> None:
    protector = FernetCredentialProtector(_write_key(tmp_path), key_version=3)

    with pytest.raises(UnsupportedCredentialVersionError, match="不支持凭据版本"):
        protector.decrypt(b"unused", credential_version=2)
