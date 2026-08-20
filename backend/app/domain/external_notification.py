"""说明本模块的职责、边界和主要协作对象。"""

import re
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ExternalNotificationConfig:
    """说明 ExternalNotificationConfig 的职责、状态边界和对外协作关系。"""
    channel: str
    enabled: bool
    template: str
    retry_limit: int
    sensitive_data_allowed: bool
    preview_only: bool


class ExternalNotificationGateway(Protocol):
    """说明 ExternalNotificationGateway 的职责、状态边界和对外协作关系。"""
    async def save_config(
        self, *, workspace_id: str, config: ExternalNotificationConfig
    ) -> ExternalNotificationConfig:
        """执行 save_config 的业务流程并返回该流程的结果。"""

    async def list_configs(
        self, *, workspace_id: str, limit: int
    ) -> list[ExternalNotificationConfig]:
        """执行 list_configs 的业务流程并返回该流程的结果。"""


ALLOWED_CHANNELS = frozenset({"feishu", "dingtalk", "wechat_work", "email"})
ALLOWED_TEMPLATE_FIELDS = frozenset({"headline", "summary", "severity", "workspace"})


def validate_notification_config(
    *, channel: str, enabled: bool, template: str,
    retry_limit: int, sensitive_data_allowed: bool,
) -> ExternalNotificationConfig:
    """执行 validate_notification_config 的业务流程并返回该流程的结果。"""
    normalized = channel.strip().lower()
    normalized_template = template.strip()
    if normalized not in ALLOWED_CHANNELS or not template.strip():
        raise ValueError("通知渠道或消息模板无效")
    if len(normalized_template) > 5000:
        raise ValueError("通知模板不能超过 5000 个字符")
    if (
        isinstance(retry_limit, bool) or not isinstance(retry_limit, int)
        or retry_limit < 0 or retry_limit > 5
    ):
        raise ValueError("重试次数必须在 0 到 5 之间")
    if sensitive_data_allowed:
        raise ValueError("外部通知不允许发送敏感数据")
    return ExternalNotificationConfig(
        normalized, enabled, normalized_template, retry_limit, False, True
    )


def render_notification_preview(template: str, values: dict[str, object]) -> str:
    """仅渲染白名单字段，预览结果不触发任何外部发送。"""
    fields = re.findall(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", template)
    if not template.strip() or any(field not in ALLOWED_TEMPLATE_FIELDS for field in fields):
        raise ValueError("通知模板包含空内容或未允许字段")
    return re.sub(
        r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}",
        lambda match: str(values.get(match.group(1), "")),
        template,
    )
