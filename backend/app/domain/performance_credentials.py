from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PerformanceCredentialStatus:
    credential_scope: str
    client_id_present: bool
    client_secret_present: bool
    access_token_present: bool
    refresh_token_present: bool
    expires_at: str | None
    isolated_from_seller: bool
    ready: bool


class PerformanceCredentialGateway(Protocol):
    async def save_client_credentials(
        self, *, workspace_id: str, client_id: str, client_secret: str,
    ) -> PerformanceCredentialStatus: ...

    async def get_client_credentials(
        self, *, workspace_id: str,
    ) -> tuple[str, str] | None: ...

    async def get_access_token(
        self, *, workspace_id: str,
    ) -> tuple[str, str] | None: ...

    async def save_tokens(
        self, *, workspace_id: str, access_token: str, refresh_token: str | None,
        expires_at: str, client_id_present: bool,
    ) -> PerformanceCredentialStatus: ...

    async def get_status(self, *, workspace_id: str) -> PerformanceCredentialStatus | None: ...


def inspect_performance_credentials(
    *, client_id: str | None, access_token: str | None,
    refresh_token: str | None, expires_at: str | None,
    client_secret: str | None = None,
) -> PerformanceCredentialStatus:
    if any(
        value is not None and not isinstance(value, str)
        for value in (client_id, client_secret, access_token, refresh_token, expires_at)
    ):
        raise ValueError("Performance 凭据字段格式无效")
    normalized_expiry = expires_at.strip() if expires_at else None
    if normalized_expiry:
        try:
            datetime.fromisoformat(normalized_expiry.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("Performance 令牌过期时间必须是 ISO-8601 格式") from error
    client_id_present = bool(client_id and client_id.strip())
    client_secret_present = bool(client_secret and client_secret.strip())
    access_token_present = bool(access_token and access_token.strip())
    refresh_token_present = bool(refresh_token and refresh_token.strip())
    access_token_expired = False
    if normalized_expiry:
        expiry = datetime.fromisoformat(normalized_expiry.replace("Z", "+00:00"))
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        access_token_expired = expiry <= datetime.now(UTC)
    return PerformanceCredentialStatus(
        credential_scope="performance_api",
        client_id_present=client_id_present,
        client_secret_present=client_secret_present,
        access_token_present=access_token_present,
        refresh_token_present=refresh_token_present,
        expires_at=normalized_expiry,
        isolated_from_seller=True,
        ready=(
        # 过期 Access Token 仍可由 Refresh Token 恢复；没有 Refresh Token
        # 时不能误报为可用，避免后续请求必然失败。
            client_id_present
            and client_secret_present
            and ((access_token_present and not access_token_expired) or refresh_token_present)
        ),
    )
