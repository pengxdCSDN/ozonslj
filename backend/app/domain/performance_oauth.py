"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True, slots=True)
class PerformanceToken:
    """说明 PerformanceToken 的职责、状态边界和对外协作关系。"""
    access_token: str
    expires_at: datetime
    refresh_token_present: bool
    credential_scope: str = "performance_api"

    @property
    def needs_refresh(self) -> bool:
        """执行 needs_refresh 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""
        return self.expires_at <= datetime.now(UTC) + timedelta(minutes=5)


class PerformanceOAuthError(ValueError):
    """Performance API 凭据或令牌状态不符合安全边界。"""


def build_performance_token(
    access_token: str, expires_at: datetime, refresh_token: str | None
) -> PerformanceToken:
    """执行 build_performance_token 的业务流程并返回该流程的结果。

Args:
    access_token: 参数语义、输入边界和安全约束。
    expires_at: 参数语义、输入边界和安全约束。
    refresh_token: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    PerformanceOAuthError: 业务约束或外部依赖失败时抛出。
"""
    if not access_token.strip():
        raise PerformanceOAuthError("访问令牌不能为空")
    if expires_at.tzinfo is None:
        raise PerformanceOAuthError("令牌过期时间必须包含时区")
    return PerformanceToken(access_token, expires_at.astimezone(UTC), bool(refresh_token))
