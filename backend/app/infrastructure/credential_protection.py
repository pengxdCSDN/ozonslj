from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from backend.app.domain.store_workspace import (
    CredentialProtectionError,
    CredentialProtector,
    UnsupportedCredentialVersionError,
)


class FernetCredentialProtector(CredentialProtector):
    """使用 Compose Secret 文件保护 Ozon Api-Key，密钥和明文均不进入数据库。"""

    def __init__(self, key_file: Path, *, key_version: int) -> None:
        self._key_version = key_version
        self._fernet = Fernet(self._read_key(key_file))

    @property
    def key_version(self) -> int:
        return self._key_version

    def protect(self, plaintext: str) -> bytes:
        normalized = plaintext.strip()
        if not normalized:
            raise ValueError("Ozon Api-Key 不能为空")
        return self._fernet.encrypt(normalized.encode("utf-8"))

    def unprotect(self, ciphertext: bytes, *, credential_version: int) -> str:
        if credential_version != self._key_version:
            raise UnsupportedCredentialVersionError(
                f"不支持凭据版本 {credential_version}，当前版本为 {self._key_version}"
            )
        try:
            return self._fernet.decrypt(ciphertext).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError) as error:
            raise CredentialProtectionError("Ozon 凭据无法解密") from error

    @staticmethod
    def _read_key(key_file: Path) -> bytes:
        try:
            key = key_file.read_bytes().strip()
        except OSError as error:
            raise CredentialProtectionError("无法读取 Ozon 凭据主密钥文件") from error
        if not key:
            raise CredentialProtectionError("Ozon 凭据主密钥文件不能为空")
        return key
