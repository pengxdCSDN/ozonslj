from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AgentTrigger:
    trigger_type: str
    target: str
    schedule: str | None
    event_name: str | None
    enabled: bool
    read_only: bool


class AgentTriggerGateway(Protocol):
    async def save_trigger(
        self, *, workspace_id: str, trigger: AgentTrigger
    ) -> AgentTrigger: ...

    async def list_triggers(
        self, *, workspace_id: str, limit: int
    ) -> list[AgentTrigger]: ...


def create_agent_trigger(
    *, trigger_type: str, target: str, schedule: str | None,
    event_name: str | None, enabled: bool,
) -> AgentTrigger:
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
