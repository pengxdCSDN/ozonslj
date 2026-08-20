"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class SamplingPolicyDecision:
    """说明 SamplingPolicyDecision 的职责、状态边界和对外协作关系。"""
    allowed: bool
    code: str
    message: str
    normalized_url: str | None = None


def check_sampling_policy(
    url: str,
    *,
    robots_allowed: bool,
    rate_limited: bool = False,
    stop_requested: bool = False,
) -> SamplingPolicyDecision:
    """在发送公开采样请求前执行不可绕过的合规检查。

Args:
    url: 参数语义、输入边界和安全约束。
    robots_allowed: 参数语义、输入边界和安全约束。
    rate_limited: 参数语义、输入边界和安全约束。
    stop_requested: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        return SamplingPolicyDecision(False, "https_required", "仅允许公开 HTTPS 页面")
    if parsed.username or parsed.password:
        return SamplingPolicyDecision(False, "credentials_forbidden", "URL 不得包含登录凭据")
    if stop_requested:
        return SamplingPolicyDecision(False, "sampling_stopped", "采样策略已要求停止")
    if not robots_allowed:
        return SamplingPolicyDecision(False, "robots_forbidden", "robots 策略禁止访问该页面")
    if rate_limited:
        return SamplingPolicyDecision(False, "rate_limited", "当前域名处于限流状态，禁止立即请求")
    normalized = parsed._replace(query="", fragment="").geturl()
    return SamplingPolicyDecision(True, "allowed", "允许进行受控公开采样", normalized)
