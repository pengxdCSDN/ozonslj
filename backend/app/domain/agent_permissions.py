from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AgentPermissionDecision:
    agent: str
    allowed_capabilities: list[str]
    denied_capabilities: list[str]
    sql_access: bool
    credential_access: bool
    external_write_access: bool
    read_only: bool


class AgentPermissionGateway(Protocol):
    async def save_decision(
        self, *, workspace_id: str, decision: AgentPermissionDecision
    ) -> AgentPermissionDecision: ...

    async def list_decisions(
        self, *, workspace_id: str, limit: int
    ) -> list[AgentPermissionDecision]: ...


READ_CAPABILITIES = frozenset({
    "read_sales", "read_inventory", "read_advertising", "create_report", "create_todo"
})


def evaluate_agent_permissions(
    agent: str, requested_capabilities: list[str]
) -> AgentPermissionDecision:
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
