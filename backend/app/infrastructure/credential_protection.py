from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class CredentialProtectionError(RuntimeError):
    """凭据密钥不可用或密文无法安全解密。"""


class UnsupportedCredentialVersionError(CredentialProtectionError):
    """数据库中的凭据版本不受当前应用支持。"""


class FernetCredentialProtector:
    """使用服务器密钥文件保护 Ozon Api-Key，密钥和明文均不进入数据库。"""

    def __init__(self, key_file: Path, *, key_version: int) -> None:
        self._key_file = key_file
        self._key_version = key_version
        self._fernet = Fernet(self._read_key())

    @property
    def key_version(self) -> int:
        return self._key_version

    def encrypt(self, api_key: str) -> bytes:
        normalized = api_key.strip()
        if not normalized:
            raise ValueError("Ozon Api-Key 不能为空")
        return self._fernet.encrypt(normalized.encode("utf-8"))

    def decrypt(self, encrypted_api_key: bytes, *, credential_version: int) -> str:
        if credential_version != self._key_version:
            raise UnsupportedCredentialVersionError(
                f"不支持凭据版本 {credential_version}，当前版本为 {self._key_version}"
            )
        try:
            return self._fernet.decrypt(encrypted_api_key).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError) as error:
            raise CredentialProtectionError("Ozon 凭据无法解密") from error

    def _read_key(self) -> bytes:
        try:
            key = self._key_file.read_bytes().strip()
        except OSError as error:
            raise CredentialProtectionError("无法读取 Ozon 凭据主密钥文件") from error
        if not key:
            raise CredentialProtectionError("Ozon 凭据主密钥文件不能为空")
        return key
