"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AgentTrigger:
    """说明 AgentTrigger 的职责、状态边界和对外协作关系。"""
    trigger_type: str
    target: str
    schedule: str | None
    event_name: str | None
    enabled: bool
    read_only: bool


class AgentTriggerGateway(Protocol):
    """说明 AgentTriggerGateway 的职责、状态边界和对外协作关系。"""
    async def save_trigger(
        self, *, workspace_id: str, trigger: AgentTrigger
    ) -> AgentTrigger:
        """执行 save_trigger 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    trigger: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_triggers(
        self, *, workspace_id: str, limit: int
    ) -> list[AgentTrigger]:
        """执行 list_triggers 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


def create_agent_trigger(
    *, trigger_type: str, target: str, schedule: str | None,
    event_name: str | None, enabled: bool,
) -> AgentTrigger:
    """执行 create_agent_trigger 的业务流程并返回该流程的结果。

Args:
    trigger_type: 参数语义、输入边界和安全约束。
    target: 参数语义、输入边界和安全约束。
    schedule: 参数语义、输入边界和安全约束。
    event_name: 参数语义、输入边界和安全约束。
    enabled: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    normalized = trigger_type.strip().lower()
    if normalized not in {"scheduled", "event", "manual"} or not target.strip():
        raise ValueError("触发类型必须是 scheduled、event 或 manual，目标不能为空")
    normalized_schedule = schedule.strip() if schedule else None
    normalized_event = event_name.strip() if event_name else None
    if not isinstance(enabled, bool):
        raise ValueError("触发器 enabled 必须是布尔值")
    if normalized == "scheduled" and (not normalized_schedule or normalized_event):
        raise ValueError("定时触发必须配置周期")
    if normalized == "event" and (not normalized_event or normalized_schedule):
        raise ValueError("事件触发必须配置事件名称")
    if normalized == "manual" and (normalized_schedule or normalized_event):
        raise ValueError("手动触发不接受周期或事件名称")
    return AgentTrigger(
        normalized, target.strip(), normalized_schedule, normalized_event, enabled, True
    )
