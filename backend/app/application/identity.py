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
        self._gateway = gateway
        self._password_hasher = password_hasher or PasswordHasher()
        self._session_ttl = session_ttl

    async def login(
        self,
        email: str,
        password: str,
        organization_id: str,
    ) -> LoginResult | None:
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
        if not token:
            return None
        return await self._gateway.find_user_by_session_hash(self._token_hash(token))

    async def logout(self, token: str) -> None:
        if token:
            await self._gateway.revoke_session(self._token_hash(token))

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
