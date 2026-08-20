"""说明本模块的职责、边界和主要协作对象。"""

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
        """初始化对象依赖和运行时状态。

Args:
    key_file: 参数语义、输入边界和安全约束。
    key_version: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._key_version = key_version
        self._fernet = Fernet(self._read_key(key_file))

    @property
    def key_version(self) -> int:
        """执行 key_version 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""
        return self._key_version

    def protect(self, plaintext: str) -> bytes:
        """执行 protect 的业务流程并返回该流程的结果。

Args:
    plaintext: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
        normalized = plaintext.strip()
        if not normalized:
            raise ValueError("Ozon Api-Key 不能为空")
        return self._fernet.encrypt(normalized.encode("utf-8"))

    def unprotect(self, ciphertext: bytes, *, credential_version: int) -> str:
        """执行 unprotect 的业务流程并返回该流程的结果。

Args:
    ciphertext: 参数语义、输入边界和安全约束。
    credential_version: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    UnsupportedCredentialVersionError: 业务约束或外部依赖失败时抛出。
    CredentialProtectionError: 业务约束或外部依赖失败时抛出。
"""
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
        """执行内部步骤 _read_key，供同一模块的公开流程复用。

Args:
    key_file: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    CredentialProtectionError: 业务约束或外部依赖失败时抛出。
"""
        try:
            key = key_file.read_bytes().strip()
        except OSError as error:
            raise CredentialProtectionError("无法读取 Ozon 凭据主密钥文件") from error
        if not key:
            raise CredentialProtectionError("Ozon 凭据主密钥文件不能为空")
        return key
