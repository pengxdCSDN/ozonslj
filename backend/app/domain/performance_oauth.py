from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True, slots=True)
class PerformanceToken:
    access_token: str
    expires_at: datetime
    refresh_token_present: bool
    credential_scope: str = "performance_api"

    @property
    def needs_refresh(self) -> bool:
        return self.expires_at <= datetime.now(UTC) + timedelta(minutes=5)


class PerformanceOAuthError(ValueError):
    """Performance API 凭据或令牌状态不符合安全边界。"""


def build_performance_token(
    access_token: str, expires_at: datetime, refresh_token: str | None
) -> PerformanceToken:
    if not access_token.strip():
        raise PerformanceOAuthError("访问令牌不能为空")
    if expires_at.tzinfo is None:
        raise PerformanceOAuthError("令牌过期时间必须包含时区")
    return PerformanceToken(access_token, expires_at.astimezone(UTC), bool(refresh_token))
