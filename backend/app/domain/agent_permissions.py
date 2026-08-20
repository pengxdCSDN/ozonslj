"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AgentPermissionDecision:
    """说明 AgentPermissionDecision 的职责、状态边界和对外协作关系。"""
    agent: str
    allowed_capabilities: list[str]
    denied_capabilities: list[str]
    sql_access: bool
    credential_access: bool
    external_write_access: bool
    read_only: bool


class AgentPermissionGateway(Protocol):
    """说明 AgentPermissionGateway 的职责、状态边界和对外协作关系。"""
    async def save_decision(
        self, *, workspace_id: str, decision: AgentPermissionDecision
    ) -> AgentPermissionDecision:
        """执行 save_decision 的业务流程并返回该流程的结果。"""

    async def list_decisions(
        self, *, workspace_id: str, limit: int
    ) -> list[AgentPermissionDecision]:
        """执行 list_decisions 的业务流程并返回该流程的结果。"""


READ_CAPABILITIES = frozenset({
    "read_sales", "read_inventory", "read_advertising", "create_report", "create_todo"
})


def evaluate_agent_permissions(
    agent: str, requested_capabilities: list[str]
) -> AgentPermissionDecision:
    """执行 evaluate_agent_permissions 的业务流程并返回该流程的结果。"""
    normalized_agent = agent.strip()
    if not normalized_agent:
        raise ValueError("Agent 名称不能为空")
    requested: list[str] = []
    for item in requested_capabilities:
        if not isinstance(item, str):
            requested.append(str(item))
            continue
        normalized_capability = item.strip()
        if normalized_capability:
            requested.append(normalized_capability)
    requested = list(dict.fromkeys(requested))
    allowed = [item for item in requested if item in READ_CAPABILITIES]
    denied = [item for item in requested if item not in READ_CAPABILITIES]
    return AgentPermissionDecision(normalized_agent, allowed, denied, False, False, False, True)
