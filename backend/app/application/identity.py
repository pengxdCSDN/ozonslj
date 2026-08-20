"""应用层身份服务：密码哈希、登录会话创建、认证和退出。"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from backend.app.domain.identity import AuthenticatedUser, IdentityGateway, LoginResult


class PasswordHasher:
    """使用 scrypt 保存密码哈希，参数兼顾安全性与 2 核 2GB 服务器预算。"""

    _n = 2**14
    _r = 8
    _p = 1

    def hash(self, password: str) -> str:
        """校验密码长度并生成带随机盐的 scrypt 编码结果。

Args:
    password: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
        if len(password) < 12:
            raise ValueError("密码至少需要 12 个字符")
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(
            password.encode(),
            salt=salt,
            n=self._n,
            r=self._r,
            p=self._p,
        )
        return f"scrypt${self._n}${self._r}${self._p}${salt.hex()}${digest.hex()}"

    def verify(self, password: str, encoded: str) -> bool:
        """验证密码与编码哈希；格式错误或算法不匹配时返回 False。

Args:
    password: 参数语义、输入边界和安全约束。
    encoded: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        try:
            algorithm, n, r, p, salt, expected = encoded.split("$", 5)
            if algorithm != "scrypt":
                return False
            actual = hashlib.scrypt(
                password.encode(),
                salt=bytes.fromhex(salt),
                n=int(n),
                r=int(r),
                p=int(p),
            )
            return hmac.compare_digest(actual, bytes.fromhex(expected))
        except (ValueError, TypeError):
            return False


class IdentityService:
    """执行登录、会话认证和退出，不向数据库保存原始会话令牌。"""

    def __init__(
        self,
        gateway: IdentityGateway,
        *,
        password_hasher: PasswordHasher | None = None,
        session_ttl: timedelta = timedelta(hours=12),
    ) -> None:
        """初始化对象依赖和运行时状态。

Args:
    gateway: 参数语义、输入边界和安全约束。
    password_hasher: 参数语义、输入边界和安全约束。
    session_ttl: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._gateway = gateway
        self._password_hasher = password_hasher or PasswordHasher()
        self._session_ttl = session_ttl

    async def login(
        self,
        email: str,
        password: str,
        organization_id: str,
    ) -> LoginResult | None:
        """校验登录身份并创建只保存哈希的短期会话。

Args:
    email: 参数语义、输入边界和安全约束。
    password: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        identity = await self._gateway.find_login_identity(
            email.strip().lower(),
            organization_id,
        )
        if identity is None:
            return None
        user, password_hash = identity
        if not self._password_hasher.verify(password, password_hash):
            return None
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + self._session_ttl
        await self._gateway.create_session(
            user.id,
            user.organization_id,
            self._token_hash(token),
            expires_at,
        )
        return LoginResult(token=token, expires_at=expires_at, user=user)

    async def authenticate(self, token: str) -> AuthenticatedUser | None:
        """通过会话令牌哈希查找当前认证用户。

Args:
    token: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        if not token:
            return None
        return await self._gateway.find_user_by_session_hash(self._token_hash(token))

    async def logout(self, token: str) -> None:
        """撤销会话令牌；空令牌视为无需处理。

Args:
    token: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        if token:
            await self._gateway.revoke_session(self._token_hash(token))

    @staticmethod
    def _token_hash(token: str) -> str:
        """执行内部步骤 _token_hash，供同一模块的公开流程复用。

Args:
    token: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return hashlib.sha256(token.encode()).hexdigest()
